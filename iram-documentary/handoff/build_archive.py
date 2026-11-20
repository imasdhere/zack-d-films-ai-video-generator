"""Build the handoff archives (three ZIPs that unpack into one folder, iram_lost_city_handoff/).

  python handoff/build_archive.py [--out DIR]

part 1  project:  every git-tracked file, AI images (PNG) + depth maps, Blender renders, photographs, map cache
part 2  audio:    narration segments (24-bit WAV), final mix (FLAC), subtitles
part 3  extras:   narration chunks (current), Quranic review candidates, voice references + listening copies, review copy, thumbnails
Narration WAVs are stored as 24-bit PCM (the working copies are 32-bit float; the difference is inaudible).
FILE_MANIFEST.csv lists every file with its size and SHA-256.
"""
import argparse, csv, datetime, hashlib, json, os, pathlib, shutil, subprocess, sys, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = pathlib.Path(os.environ.get('IRAM_WORK', '/home/user/iram-work'))
TOP = 'iram_lost_city_handoff'
STORE = {'.png', '.jpg', '.jpeg', '.mp4', '.flac', '.mp3', '.tif', '.webp', '.zip', '.npy'}


def git(*a): return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def current_chunk_files():
    sys.path.insert(0, str(ROOT))
    from audio_engine.synthesis_manager import plan
    out = []
    for i in plan():
        w = pathlib.Path(i['wav'])
        if w.exists(): out += [w, pathlib.Path(str(w) + '.json')]
    return out


def to_pcm24(src, dst):
    import soundfile as sf
    x, sr = sf.read(src, dtype='float32'); dst.parent.mkdir(parents=True, exist_ok=True)
    sf.write(dst, x, sr, subtype='PCM_24')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=str(ROOT / 'handoff_out')); a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    stage = WORK / 'handoff_stage' / TOP; shutil.rmtree(stage.parent, ignore_errors=True); P = stage / 'iram-documentary'
    parts = {1: [], 2: [], 3: []}

    def add(src, rel, part, convert=None):
        dst = P / rel; dst.parent.mkdir(parents=True, exist_ok=True)
        if convert: convert(src, dst)
        else:
            try: os.link(src, dst)
            except OSError: shutil.copy2(src, dst)
        parts[part].append(dst)

    # part 1: project files and picture inputs
    for f in git('ls-files').splitlines():
        p = ROOT / f
        if p.is_file(): add(p, f, 1)
    for pat in ('assets/images/*.png', 'assets/images/depth/*', 'assets/3d_models/**/*.png', 'assets/archaeological_photographs/*'):
        for p in ROOT.glob(pat):
            rel = p.relative_to(ROOT)
            if p.is_file() and not (P / rel).exists(): add(p, rel, 1)
    for p in list((WORK / 'cache/maps').glob('*.png')) + list((WORK / 'data/ne').glob('*.geojson')):
        add(p, pathlib.Path('handoff_work') / p.relative_to(WORK), 1)
    # part 2: audio needed to export
    for p in sorted((ROOT / 'assets/narration/segments').glob('*.wav')):
        add(p, p.relative_to(ROOT), 2, to_pcm24)
    flac = WORK / 'handoff_stage/mix.flac'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ROOT / 'renders/final/mix.wav'), '-c:a', 'flac', '-compression_level', '8', str(flac)], check=True)
    add(flac, 'renders/final/mix.flac', 2)
    # part 3: extras
    for p in current_chunk_files():
        rel = p.relative_to(ROOT); add(p, rel, 3, to_pcm24 if p.suffix == '.wav' else None)
    for p in (ROOT / 'assets/narration/quranic').glob('*'):
        if p.is_file() and not (P / p.relative_to(ROOT)).exists(): add(p, p.relative_to(ROOT), 3)
    vp = ROOT / 'voice_profiles'
    for pat in ('*/cleaned_reference*.wav', '*/original_video/*', '*/extracted_audio/reference_*.wav', '*/extracted_audio/reference_*.txt',
                '*/test_samples/*.mp3', '*/test_samples/v3/*.mp3'):
        for p in vp.glob(pat):
            if p.is_file() and not (P / p.relative_to(ROOT)).exists(): add(p, p.relative_to(ROOT), 3)
    for n in ('iram_lost_city_documentary_1440p_review_540p.mp4', 'thumbnail.jpg', 'thumbnail_1280x720.jpg'):
        p = ROOT / 'renders/final' / n
        if p.exists(): add(p, p.relative_to(ROOT), 3)

    # info and manifest (in every part, so any part tells what the set contains)
    info = (f"THE LOST CITY OF IRAM - handoff archive\nbuilt: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC\n"
            f"git: imasdhere/zack-d-films-ai-video-generator, branch {git('rev-parse', '--abbrev-ref', 'HEAD')}, commit {git('rev-parse', 'HEAD')}\n"
            f"film version: 3 (2560x1440, 20:12.6)\nparts: 1 project+images, 2 audio, 3 extras; unzip all three into the same folder\n"
            f"start with: iram-documentary/handoff/README.md\n")
    (P / 'handoff').mkdir(parents=True, exist_ok=True); (P / 'handoff/ARCHIVE_INFO.txt').write_text(info, encoding='utf-8')
    rows = []
    for k, files in parts.items():
        for f in files:
            h = hashlib.sha256(open(f, 'rb').read()).hexdigest()
            rows.append({'part': k, 'path': str(f.relative_to(stage.parent)), 'bytes': f.stat().st_size, 'sha256': h})
    with open(P / 'handoff/FILE_MANIFEST.csv', 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['part', 'path', 'bytes', 'sha256']); w.writeheader(); w.writerows(rows)
    shared = [P / 'handoff/ARCHIVE_INFO.txt', P / 'handoff/FILE_MANIFEST.csv', P / 'handoff/README.md', P / 'handoff/NOT_INCLUDED.md']
    stamp = datetime.date.today().isoformat(); names = {1: 'part1_project_and_images', 2: 'part2_audio', 3: 'part3_extras'}; result = []
    for k, files in parts.items():
        z = out / f'iram_lost_city_handoff_{stamp}_{names[k]}.zip'
        with zipfile.ZipFile(z, 'w', allowZip64=True) as zf:
            for f in sorted(set(files + shared)):
                ct = zipfile.ZIP_STORED if f.suffix.lower() in STORE or f.suffix == '.wav' else zipfile.ZIP_DEFLATED
                zf.write(f, str(f.relative_to(stage.parent)), compress_type=ct)
        result.append({'zip': str(z), 'files': len(files), 'mb': round(z.stat().st_size / 1e6, 1)})
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
