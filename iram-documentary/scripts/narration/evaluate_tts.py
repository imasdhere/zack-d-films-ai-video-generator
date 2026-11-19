"""Objective TTS comparison: intelligibility (Whisper WER), Arabic-term recognition, pitch depth,
pitch variation, speaking rate, pause structure, clipping, and an automatic MOS estimate (torchaudio SQUIM)."""
import sys, json, re, glob, pathlib
import numpy as np, soundfile as sf, librosa, torch, whisper, jiwer
ref_text = open(sys.argv[1], encoding='utf-8').read()
wavs = sorted(glob.glob(sys.argv[2]))
out_json = sys.argv[3]
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower().replace('-', ' ')).split()
TERMS = {'Iram': r'\bi[r]+[ae]m', 'Aad': r'\b(aad|ad|aahd|odd)\b', 'Hud': r'\b(hud|hood|hude)\b', 'Tabari': r'tabar', 'Kathir': r'kath', 'Shisr': r'shis|shiz', 'Fajr': r'fajr|fajir|fudger|fadger', 'Khali': r'khali|kali|kahli', 'Imad': r'imad|ima?d|emad'}
model = whisper.load_model('small.en', download_root='/home/user/iram-work/models/whisper')
try:
    from torchaudio.pipelines import SQUIM_OBJECTIVE
    squim = SQUIM_OBJECTIVE.get_model(); have_squim = True
except Exception as e:
    print('SQUIM unavailable:', e); have_squim = False
res = []
for w in wavs:
    y, sr = sf.read(w); y = y.astype(np.float32)
    if y.ndim > 1: y = y.mean(1)
    dur = len(y) / sr
    hyp = model.transcribe(w, language='en', fp16=False, temperature=0)['text']
    wer = jiwer.wer(' '.join(norm(ref_text)), ' '.join(norm(hyp)))
    terms = {k: bool(re.search(v, hyp.lower())) for k, v in TERMS.items()}
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
    f0, vf, _ = librosa.pyin(y16, fmin=55, fmax=300, sr=16000, frame_length=1024)
    f0v = f0[~np.isnan(f0)]
    rms = librosa.feature.rms(y=y16, frame_length=800, hop_length=160)[0]
    silent = rms < (0.02 * rms.max()); 
    # pauses = runs of silence > 250 ms
    runs = []; c = 0
    for s in silent:
        if s: c += 1
        else:
            if c >= 25: runs.append(c * 0.01)
            c = 0
    words = len(norm(ref_text))
    speech_time = dur - sum(runs)
    r = {'file': pathlib.Path(w).name, 'duration_s': round(dur, 1), 'wer': round(wer, 3), 'terms_recognised': sum(terms.values()), 'terms': terms,
         'f0_median_hz': round(float(np.median(f0v)), 1), 'f0_semitone_sd': round(float(np.std(12*np.log2(f0v/np.median(f0v)))), 2),
         'wpm_overall': round(words / dur * 60, 1), 'wpm_articulation': round(words / speech_time * 60, 1), 'n_pauses': len(runs),
         'mean_pause_s': round(float(np.mean(runs)) if runs else 0, 2), 'peak_dbfs': round(float(20*np.log10(np.abs(y).max()+1e-9)), 1), 'transcript': hyp.strip()}
    if have_squim:
        with torch.no_grad():
            seg = torch.from_numpy(y16[:16000*30]).unsqueeze(0)
            stoi, pesq, sisdr = squim(seg)
        r.update({'squim_stoi': round(float(stoi), 3), 'squim_pesq': round(float(pesq), 2), 'squim_sisdr': round(float(sisdr), 1)})
    res.append(r); print(json.dumps({k: v for k, v in r.items() if k not in ('transcript', 'terms')}))
json.dump(res, open(out_json, 'w'), indent=1, ensure_ascii=False)
