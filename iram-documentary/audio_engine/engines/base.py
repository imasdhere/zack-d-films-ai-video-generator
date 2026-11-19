"""Engine adapters. An adapter turns chunk jobs into a JSONL file and runs the engine's worker in the
engine's own virtual environment, so the dependencies of the engines never conflict."""
import json, pathlib, subprocess, time, tempfile
from ..common import ROOT, WORK, config


class EngineAdapter:
    key = None
    languages = ('en', 'ar')

    def __init__(self):
        self.cfg = config()['engines'][self.key]

    def worker_cmd(self, jobs_path, force=False):
        c = self.cfg
        cmd = [f"{c['venv']}/bin/python", '-I', str(ROOT / c['worker']), '--jobs', str(jobs_path), '--model', c['model_dir']]
        if c.get('codec_dir'): cmd += ['--codec', c['codec_dir']]
        if force: cmd += ['--force']
        return cmd

    def check(self):
        """Return a list of problems that stop this engine from running (empty list = ready)."""
        c = self.cfg; probs = []
        if not pathlib.Path(c['venv'], 'bin/python').exists(): probs.append(f"venv missing: {c['venv']}")
        if not pathlib.Path(c['model_dir']).exists(): probs.append(f"weights missing: {c['model_dir']}")
        if c.get('codec_dir') and not pathlib.Path(c['codec_dir']).exists(): probs.append(f"codec missing: {c['codec_dir']}")
        return probs

    def run(self, jobs, log_path=None, force=False):
        """jobs: list of dicts (id, text, lang, out, ref_wav, ref_text, seed, params). Returns per-job results."""
        for j in jobs:
            if j['lang'] not in self.languages: raise ValueError(f"{self.key} does not support language {j['lang']}")
            j.setdefault('params', {}); j['params'] = {**self.cfg.get('params', {}), **j['params']}
        tmp = tempfile.NamedTemporaryFile('w', suffix='.jsonl', dir=WORK / 'scratch', delete=False, encoding='utf-8')
        for j in jobs: tmp.write(json.dumps(j, ensure_ascii=False) + '\n')
        tmp.close()
        log = open(log_path or WORK / 'logs' / f'{self.key}_{int(time.time())}.log', 'a', encoding='utf-8')
        t0 = time.time(); results = []
        p = subprocess.Popen(self.worker_cmd(tmp.name, force), stdout=subprocess.PIPE, stderr=log, text=True)
        for line in p.stdout:
            log.write(line); log.flush()
            try: results.append(json.loads(line))
            except json.JSONDecodeError: pass
        rc = p.wait(); log.close()
        if rc != 0: raise RuntimeError(f'{self.key} worker exited with {rc}; see {log.name}')
        return {'results': results, 'wall_s': round(time.time() - t0, 1)}
