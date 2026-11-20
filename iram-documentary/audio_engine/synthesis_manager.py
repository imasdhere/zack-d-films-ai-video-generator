"""Long-form narration: plan -> generate -> QA (regenerate failures only) -> assemble -> manifest.

  python -m audio_engine.synthesis_manager plan
  python -m audio_engine.synthesis_manager generate [--lang en|ar] [--only 3.06 3.07] [--force]
  python -m audio_engine.synthesis_manager qa [--only ...] [--regenerate]
  python -m audio_engine.synthesis_manager assemble
  python -m audio_engine.synthesis_manager quranic          # review candidates only; never mixed until approved
Run with venvs/ml/bin/python from the project root. Engines run in their own venvs through audio_engine/engines.
"""
import argparse, csv, json, hashlib, pathlib, time
from .common import ROOT, WORK, config, load_yaml, write_wav
from .language_router import route_segment, tts_text_en
from .narration_chunker import chunk
from . import engines

NARR = ROOT / 'assets/narration'
MANIFEST = NARR / 'narration_manifest.csv'
SEGDIR = NARR / 'segments'
LANGDIR = {'english': 'english', 'arabic': 'arabic', 'quranic': 'quranic'}
FIELDS = ['segment_id', 'chapter', 'part', 'chunk', 'language', 'voice_profile', 'category', 'tts_engine', 'input_text', 'display_text',
          'output_audio', 'generation_settings', 'seed', 'duration_s', 'include_in_mix', 'qa_status', 'qa_notes', 'approval_status']


def engine_for(profile, cfg):
    p = cfg['voice_profiles']['arabic' if profile == 'quranic' else profile]['preferred_engine']
    if p in (None, '', 'pending_evaluation'): raise SystemExit(f'no engine selected for {profile}: run the evaluation first')
    return p


def seed_for(cid, base=20261119):
    return base + int(hashlib.sha1(cid.encode()).hexdigest()[:6], 16) % 100000


def plan():
    """Chunk plan. English: consecutive sentences of a segment are grouped into one chunk of at most
    chunking.en_group_chars characters (more context keeps the cloned voice steady); a sentence that is longer than
    en_max_chars is split at clauses. Arabic quotations are separate chunks. Every chunk lists its sentences."""
    cfg = config(); script = load_yaml('screenplay/script.yaml'); items = []; ck = cfg['chunking']
    group = ck.get('en_group_chars', 0)
    for ch in script['chapters']:
        for seg in ch['segments']:
            parts = route_segment(seg, ch['id'])
            units = []                       # (part indices, lang, profile) in order
            for pi, p in enumerate(parts):
                tts = tts_text_en(p['display'], engine_for(p['profile'], cfg)) if p['lang'] == 'en' else p['tts']
                p['_tts'] = tts
                if (group and p['lang'] == 'en' and units and units[-1][1] == 'en' and len(tts) <= ck['en_max_chars']
                        and sum(len(parts[i]['_tts']) + 1 for i in units[-1][0]) + len(tts) <= group):
                    units[-1][0].append(pi)
                else: units.append(([pi], p['lang'], p['profile']))
            for gi, (pis, lang, prof) in enumerate(units):
                p0 = parts[pis[0]]; eng = engine_for(prof, cfg)
                if len(pis) > 1:
                    cs = [{'text': ' '.join(parts[i]['_tts'] for i in pis), 'pause_after': 'sentence'}]
                else:
                    cs = chunk(p0['_tts'], lang, ck[f'{lang}_max_chars'], merge_short=ck.get(f'merge_short_{lang}', False))
                for ci, c in enumerate(cs):
                    cid = f"{seg['id']}_g{gi:02d}_c{ci:02d}"
                    items.append({'id': cid, 'segment_id': seg['id'], 'chapter': ch['id'], 'part': pis[0], 'chunk': ci, 'lang': lang,
                                  'profile': prof, 'category': p0['category'], 'engine': eng, 'text': c['text'], 'pause_after': c['pause_after'],
                                  'display': ' '.join(parts[i]['display'] for i in pis), 'sentence_tts': p0['_tts'],
                                  'sentence_key': f"{seg['id']}:{pis[0]}",
                                  'sentences': [{'key': f"{seg['id']}:{i}", 'display': parts[i]['display'], 'tts': parts[i]['_tts']} for i in pis],
                                  'include_in_mix': p0['include_in_mix'], 'approval': p0['approval'], 'flags': sum((parts[i]['flags'] for i in pis), []),
                                  'wav': str(NARR / LANGDIR[prof] / 'chunks' / f'{cid}.wav'), 'seed': seed_for(cid)})
    return items


def _ref(profile, cfg):
    p = cfg['voice_profiles']['arabic' if profile == 'quranic' else profile]
    return str(ROOT / p.get('synthesis_reference', p['reference'])), (ROOT / p['transcript']).read_text(encoding='utf-8').strip()


def _params(profile, cfg):
    return dict(cfg['voice_profiles']['arabic' if profile == 'quranic' else profile].get('engine_params', {}))


def generate(only=None, lang=None, force=False, seed_offset=0, ids=None):
    cfg = config(); items = [i for i in plan() if i['include_in_mix']]
    if only: items = [i for i in items if i['segment_id'] in only]
    if lang: items = [i for i in items if i['lang'] == lang]
    if ids: items = [i for i in items if i['id'] in ids]
    by = {}
    for i in items: by.setdefault((i['engine'], i['profile']), []).append(i)
    for (eng, prof), its in by.items():
        rw, rt = _ref(prof, cfg)
        jobs = [{'id': i['id'], 'text': i['text'], 'lang': i['lang'], 'out': i['wav'], 'ref_wav': rw, 'ref_text': rt,
                 'seed': i['seed'] + seed_offset, 'params': _params(prof, cfg)} for i in its]
        todo = [j for j in jobs if force or not pathlib.Path(j['out']).exists()]
        print(json.dumps({'engine': eng, 'profile': prof, 'chunks': len(jobs), 'to_generate': len(todo)}), flush=True)
        if todo: engines.get(eng).run(todo, log_path=WORK / 'logs' / f'narr_{eng}_{prof}.log', force=force)
    write_manifest()


def qa(only=None):
    """Per-chunk ASR and speaker check (results cached by file time in assets/narration/chunk_qa.json)."""
    from .audio_quality_control import chunk_qa
    cfg = config(); store = NARR / 'chunk_qa.json'
    res = json.load(open(store)) if store.exists() else {}
    items = [i for i in plan() if i['include_in_mix'] and pathlib.Path(i['wav']).exists()]
    if only: items = [i for i in items if i['segment_id'] in only]
    todo = [i for i in items if i['id'] not in res or res[i['id']].get('mtime') != pathlib.Path(i['wav']).stat().st_mtime]
    for i in todo:
        r = chunk_qa(i, cfg); r['mtime'] = pathlib.Path(i['wav']).stat().st_mtime; res[i['id']] = r
        print(json.dumps({'id': i['id'], **{k: r[k] for k in ('status', 'err', 'similarity')}}), flush=True)
        json.dump(res, open(store, 'w'), indent=1)
    failed = [i['id'] for i in items if res[i['id']]['status'] != 'pass']
    print(json.dumps({'checked': len(todo), 'failed': failed}), flush=True)
    write_manifest()
    return failed


def regenerate_failed(rnd):
    """Generate the chunks that failed QA again with a new seed. Runs in its own process (no QA models loaded),
    so that VoxCPM2 (about 11 GB) and the QA models (about 4 GB) are never in memory together."""
    store = NARR / 'chunk_qa.json'; res = json.load(open(store)) if store.exists() else {}
    items = {i['id']: i for i in plan() if i['include_in_mix']}
    failed = [k for k, v in res.items() if v['status'] == 'fail' and k in items]   # 'review' = best take kept for listening
    print(json.dumps({'round': rnd, 'regenerate': failed}), flush=True)
    if not failed: return
    for k in failed:
        w = pathlib.Path(items[k]['wav']); keep = w.with_suffix(f'.round{rnd - 1}.wav')
        if w.exists(): w.replace(keep)          # keep the previous take for comparison
        mj = pathlib.Path(str(w) + '.json')
        if mj.exists(): mj.replace(pathlib.Path(str(keep) + '.json'))
    generate(ids=set(failed), seed_offset=7919 * rnd)


def best_of(cid, n=6):
    """Generate n takes of one chunk (one model load), score each with the chunk QA, keep the best.
    The engine runs first; the QA models load only after the engine process has exited (memory)."""
    import shutil
    cfg = config(); it = next(i for i in plan() if i['id'] == cid); rw, rt = _ref(it['profile'], cfg)
    w = pathlib.Path(it['wav']); jobs = []
    for k in range(n):
        jobs.append({'id': f'{cid}_take{k}', 'text': it['text'], 'lang': it['lang'], 'out': str(w.with_suffix(f'.take{k}.wav')),
                     'ref_wav': rw, 'ref_text': rt, 'seed': it['seed'] + 104729 * (k + 1), 'params': _params(it['profile'], cfg)})
    engines.get(it['engine']).run(jobs, log_path=WORK / 'logs' / f'bestof_{cid}.log', force=True)
    from .audio_quality_control import chunk_qa
    scored = []
    for j in jobs:
        if not pathlib.Path(j['out']).exists(): continue
        r = chunk_qa({**it, 'wav': j['out']}, cfg); scored.append((r['err'], -(r['similarity'] or 0), j, r))
        print(json.dumps({'take': j['id'], 'err': r['err'], 'similarity': r['similarity'], 'asr': r['asr']}, ensure_ascii=False), flush=True)
    err, nsim, j, r = min(scored, key=lambda x: (x[0], x[1]))
    shutil.copy2(j['out'], w); shutil.copy2(j['out'] + '.json', str(w) + '.json')
    store = NARR / 'chunk_qa.json'; res = json.load(open(store))
    r['mtime'] = w.stat().st_mtime; r['notes'] = r['notes'] + [f'best of {len(scored)} takes ({j["id"]})']
    if r['status'] == 'fail': r['status'] = 'review'   # keep the best take; a listener decides
    res[cid] = r
    json.dump(res, open(store, 'w'), indent=1); write_manifest()
    print(json.dumps({'chosen': j['id'], 'err': err, 'status': r['status']}), flush=True)


def assemble():
    from .audio_postprocessor import assemble_segment
    cfg = config(); SEGDIR.mkdir(parents=True, exist_ok=True); segs = {}
    for i in plan():
        if i['include_in_mix']: segs.setdefault(i['segment_id'], []).append(i)
    missing = [i['id'] for s in segs.values() for i in s if not pathlib.Path(i['wav']).exists()]
    if missing: raise SystemExit(f'{len(missing)} chunks missing, e.g. {missing[:5]}')
    for sid, its in segs.items():
        y, tm = assemble_segment(its)
        sr = cfg['postprocess']['sample_rate']
        write_wav(SEGDIR / f'{sid}.wav', y, sr, subtype='FLOAT')
        json.dump({'id': sid, 'sr': sr, 'duration': round(len(y) / sr, 3), 'sentences': tm}, open(SEGDIR / f'{sid}.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print(json.dumps({'segments': len(segs), 'minutes': round(sum(json.load(open(SEGDIR / f'{s}.json'))['duration'] for s in segs) / 60, 2)}))
    write_manifest()


def write_manifest():
    cfg = config(); store = NARR / 'chunk_qa.json'; q = json.load(open(store)) if store.exists() else {}
    rows = []
    for i in plan():
        meta_p = pathlib.Path(i['wav'] + '.json'); meta = json.load(open(meta_p, encoding='utf-8')) if meta_p.exists() else {}
        r = q.get(i['id'], {})
        rows.append({'segment_id': i['segment_id'], 'chapter': i['chapter'], 'part': i['part'], 'chunk': i['chunk'], 'language': i['lang'],
                     'voice_profile': cfg['voice_profiles']['arabic' if i['profile'] == 'quranic' else i['profile']]['id'] + (' (quranic workflow)' if i['profile'] == 'quranic' else ''),
                     'category': i['category'], 'tts_engine': i['engine'], 'input_text': i['text'], 'display_text': i['display'],
                     'output_audio': str(pathlib.Path(i['wav']).relative_to(ROOT)) if i['include_in_mix'] else 'see research/quranic_verse_registry.csv',
                     'generation_settings': json.dumps(meta.get('params', cfg['engines'][i['engine']].get('params', {})), ensure_ascii=False),
                     'seed': meta.get('seed', i['seed']), 'duration_s': meta.get('duration', ''), 'include_in_mix': i['include_in_mix'],
                     'qa_status': r.get('status', 'not run' if i['include_in_mix'] else 'excluded: Quranic wording'),
                     'qa_notes': '; '.join(r.get('notes', []) + i['flags']), 'approval_status': i['approval']})
    with open(MANIFEST, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    return rows


def quranic():
    """Synthetic renderings for review only: verses whose Arabic is on screen, plus routed Quranic parts.
    Text is the exact Tanzil Uthmani text; a second rendering uses the exact Tanzil Simple (diacritised) text."""
    from . import quranic_validator as QV
    from .audio_quality_control import transcribe, load16, error_rates
    cfg = config(); eng = engine_for('quranic', cfg); rw, rt = _ref('quranic', cfg); out = NARR / 'quranic'; out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(QV.REGISTRY, encoding='utf-8')))
    keys = [r['verse_key'] for r in rows if 'arabic_on_screen' in r['use_in_film']]
    jobs = []
    for k in keys:
        s, a = map(int, k.split(':'))
        for script in ('uthmani', 'simple'):
            jobs.append({'id': f'q{s}_{a}_{script}', 'text': QV.verse(s, a, script), 'lang': 'ar', 'out': str(out / f'quran_{s:03d}_{a:03d}_{script}.wav'),
                         'ref_wav': rw, 'ref_text': rt, 'seed': 4600 + s * 1000 + a})
    for i in plan():
        if i['profile'] == 'quranic':
            jobs.append({'id': i['id'], 'text': i['text'], 'lang': 'ar', 'out': str(out / f"{i['id']}.wav"), 'ref_wav': rw, 'ref_text': rt, 'seed': i['seed']})
    engines.get(eng).run(jobs, log_path=WORK / 'logs' / f'quranic_{eng}.log')
    report = []
    for j in jobs:
        if not pathlib.Path(j['out']).exists(): report.append({'id': j['id'], 'status': 'generation failed'}); continue
        hyp = transcribe(load16(j['out']), 'ar'); wer, cer = error_rates(j['text'], hyp, 'ar')
        report.append({'id': j['id'], 'text': j['text'], 'asr': hyp, 'cer_letters': cer, 'wer': wer, 'file': str(pathlib.Path(j['out']).relative_to(ROOT)),
                       'engine': eng, 'approved_for_publication': 'no', 'review': 'requires a qualified reciter or tajwid teacher'})
    by_key = {}
    for r in report:
        if r['id'].startswith('q') and 'cer_letters' in r:
            k = r['id'][1:].rsplit('_', 1)[0].replace('_', ':')
            by_key.setdefault(k, []).append(r)
    for k, rs in by_key.items():
        best = min(rs, key=lambda r: r['cer_letters'])
        QV.update_audio(k, best['file'], eng, f"{best['cer_letters']} ({'uthmani' if 'uthmani' in best['id'] else 'simple'} text)")
    json.dump(report, open(out / 'quranic_review_candidates.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps([{k: r.get(k) for k in ('id', 'cer_letters', 'wer')} for r in report]))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--only', nargs='*'); ap.add_argument('--lang')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--round', type=int, default=1)
    ap.add_argument('--id'); ap.add_argument('--n', type=int, default=6)
    a = ap.parse_args()
    if a.cmd == 'plan':
        its = plan(); print(json.dumps({'chunks': len(its), 'in_mix': sum(i['include_in_mix'] for i in its),
                                        'by_lang': {l: sum(1 for i in its if i['lang'] == l) for l in ('en', 'ar')},
                                        'excluded': [i['id'] for i in its if not i['include_in_mix']]}))
        write_manifest()
    elif a.cmd == 'generate': generate(a.only, a.lang, a.force)
    elif a.cmd == 'qa': qa(a.only)
    elif a.cmd == 'regenerate-failed': regenerate_failed(a.round)
    elif a.cmd == 'best-of': best_of(a.id, a.n)
    elif a.cmd == 'assemble': assemble()
    elif a.cmd == 'quranic': quranic()
