"""Automated quality control of the final master. Writes reports/qc_metrics.json (the report is written from it)."""
import json, re, subprocess, sys, pathlib, numpy as np, soundfile as sf
ROOT = pathlib.Path(__file__).resolve().parents[2]
F = ROOT / 'renders/final/iram_lost_city_documentary.mp4'
res = {}
def run(cmd): return subprocess.run(cmd, capture_output=True, text=True)
# 1. container / streams
pr = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(F)]).stdout)
v = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]; a = [s for s in pr['streams'] if s['codec_type'] == 'audio'][0]
res['container'] = {'duration_s': float(pr['format']['duration']), 'size_mb': round(int(pr['format']['size']) / 1e6, 1), 'video_codec': v['codec_name'], 'profile': v.get('profile'),
    'width': v['width'], 'height': v['height'], 'fps': v['r_frame_rate'], 'pix_fmt': v['pix_fmt'], 'dar': v.get('display_aspect_ratio'),
    'audio_codec': a['codec_name'], 'audio_channels': a['channels'], 'audio_rate': a['sample_rate'], 'streams': [s['codec_type'] for s in pr['streams']]}
# 2. full decode (corruption)
dec = run(['ffmpeg', '-v', 'error', '-i', str(F), '-f', 'null', '-'])
res['decode_errors'] = dec.stderr.strip().splitlines()[:20]
# 3. black frames (true black only) and frozen frames
bd = run(['ffmpeg', '-i', str(F), '-vf', 'blackdetect=d=0.5:pix_th=0.03', '-an', '-f', 'null', '-']).stderr
res['black_segments'] = [tuple(float(x) for x in m) for m in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', bd)]
fz = run(['ffmpeg', '-i', str(F), '-vf', 'freezedetect=n=0.0008:d=6', '-an', '-f', 'null', '-']).stderr
res['frozen_segments'] = re.findall(r'freeze_start: ([\d.]+)', fz)
# 4. loudness / peaks / silence
eb = run(['ffmpeg', '-i', str(F), '-filter_complex', 'ebur128=peak=true', '-vn', '-f', 'null', '-']).stderr
summ = eb[eb.rfind('Summary:'):]
g = lambda k: float(re.search(k + r':\s+([-\d.]+)', summ).group(1))
res['loudness'] = {'integrated_lufs': g('I'), 'lra_lu': g('LRA'), 'true_peak_dbfs': g('Peak')}
sd = run(['ffmpeg', '-i', str(F), '-af', 'silencedetect=n=-55dB:d=2', '-vn', '-f', 'null', '-']).stderr
res['silences_over_2s_below_-55dB'] = re.findall(r'silence_start: ([\d.]+)', sd)
# 5. music-absence analysis on the ambience stem (everything except narration)
import librosa
from scipy.ndimage import median_filter, label as cc_label
amb, sr = sf.read(ROOT / 'assets/sound_effects/ambience_stem.wav', dtype='float32'); amb = amb.mean(1)
y = librosa.resample(amb, orig_sr=sr, target_sr=16000)
S = np.abs(librosa.stft(y, n_fft=4096, hop_length=512)); D = 20 * np.log10(S + 1e-9)
freqs = librosa.fft_frequencies(sr=16000, n_fft=4096); band = (freqs > 100) & (freqs < 4000)
prom = D - median_filter(D, size=(31, 1))                      # prominence over the local spectral floor
tonal = (prom > 15) & band[:, None] & (D > D.max() - 70)
min_frames = int(0.5 * 16000 / 512)                            # a "note" must persist >= 0.5 s on one bin (+-1)
tonal_d = np.maximum(tonal, np.roll(tonal, 1, 0)) | np.roll(tonal, -1, 0)
lab, n = cc_label(tonal_d)
sustained = 0
for i in range(1, n + 1):
    ys, xs = np.where(lab == i)
    if xs.max() - xs.min() + 1 >= min_frames and (ys.max() - ys.min()) <= 3: sustained += 1
chroma = librosa.feature.chroma_stft(S=S ** 2, sr=16000); cmax = float(np.median(chroma.max(0) / (chroma.sum(0) + 1e-9)))
onset = librosa.onset.onset_strength(y=y, sr=16000); ac = librosa.autocorrelate(onset - onset.mean()); ac = ac / (ac[0] + 1e-9)
res['music_check'] = {'sustained_tonal_components_>=0.5s': int(sustained), 'chroma_peak_ratio_median': round(cmax, 3),
                      'max_rhythmic_autocorrelation_lag_0.6-12s': round(float(ac[20:400].max()), 3),
                      'stem_duration_min': round(len(y) / 16000 / 60, 1),
                      'reference_values': 'tonal music typically shows many sustained tonal components, chroma peak ratio > 0.3, rhythmic autocorrelation > 0.3'}
# 6. narration intelligibility and subtitle sync (Whisper on the final mix, sampled windows)
import whisper, jiwer
m = whisper.load_model('small.en', download_root='/home/user/iram-work/models/whisper')
mix, msr = sf.read(ROOT / 'renders/final/mix.wav', dtype='float32')
tl = json.load(open(ROOT / 'renders/timeline.json')); import yaml
script = yaml.safe_load(open(ROOT / 'screenplay/script.yaml', encoding='utf-8'))
disp = {seg['id']: ' '.join(seg['text'].split()) for ch in script['chapters'] for seg in ch['segments']}
norm = lambda s: re.sub(r"[^a-z0-9 ]", " ", s.lower()).split()
checks = []
for seg in tl['segments'][::6]:
    s0 = int(seg['start'] * msr); s1 = int((seg['start'] + seg['dur']) * msr)
    clip = librosa.resample(mix[s0:s1].mean(1), orig_sr=msr, target_sr=16000)
    hyp = m.transcribe(clip, language='en', fp16=False, temperature=0)['text']
    checks.append({'seg': seg['id'], 'wer': round(jiwer.wer(' '.join(norm(disp[seg['id']])), ' '.join(norm(hyp))), 3)})
res['narration_wer_sampled'] = checks; res['narration_wer_mean'] = round(float(np.mean([c['wer'] for c in checks])), 3)
# 7. editorial checks from the timeline
import collections
uses = collections.Counter(s['asset'] for s in tl['shots'])
res['shots'] = {'count': len(tl['shots']), 'unique_assets': len(uses), 'max_reuse': uses.most_common(5),
                'mean_shot_s': round(float(np.mean([s['end'] - s['start'] for s in tl['shots']])), 2)}
json.dump(res, open(ROOT / 'reports/qc_metrics.json', 'w'), indent=1)
print(json.dumps(res, indent=1)[:4000])
