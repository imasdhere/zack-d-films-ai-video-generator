# TTS engine evaluation

Date: 2026-11-19. Hardware: 4-core x86-64 CPU, no GPU (see `reports/system_hardware_audit.md`).
The same text (`sample_text.md`, 145 words, about 60 s, 9 Arabic terms) was used for every engine. The audio files are in `/home/user/iram-work/tts_eval/` (kept out of git) and the chosen reference is in `assets/narration/reference/`.

## Method (objective, reproducible: `scripts/narration/evaluate_tts.py`)
- **WER**: Whisper `small.en` transcript compared with the reference text (lower is better). This measures intelligibility.
- **Arabic terms**: how many of Iram, ʿĀd, Hūd, al-Ṭabarī, Ibn Kathīr, Shisr, al-Fajr, al-Khālī and al-ʿImād Whisper recognised.
- **F0 median**: pitch depth (pYIN). A typical male baritone speaking voice is about 85–155 Hz.
- **F0 semitone SD**: pitch variation. Too low sounds monotone; too high sounds theatrical.
- **SQUIM PESQ / STOI / SI-SDR**: reference-free quality estimates (torchaudio SQUIM). Higher is cleaner and more natural.
- Listening notes were not possible in this headless session. **Listen to the samples before final sign-off.**

## Results

| Sample | Dur (s) | WER | Terms | F0 med (Hz) | F0 SD (st) | WPM | PESQ* | STOI* | SI-SDR* |
|---|---|---|---|---|---|---|---|---|---|
| kokoro_am_fenrir.wav | 59.8 | 0.115 | 8/9 | 133.9 | 4.68 | 148.5 | 3.93 | 0.994 | 22.2 |
| kokoro_am_michael.wav | 68.9 | 0.101 | 8/9 | 115.9 | 3.22 | 128.8 | 3.35 | 0.994 | 24.4 |
| kokoro_am_onyx.wav | 62.1 | 0.101 | 8/9 | 84.3 | 3.52 | 143.0 | 3.0 | 0.954 | 11.5 |
| kokoro_bm_fable.wav | 62.1 | 0.095 | 8/9 | 104.4 | 7.0 | 143.1 | 2.97 | 0.959 | 15.8 |
| kokoro_bm_george.wav | 69.2 | 0.088 | 7/9 | 141.8 | 3.82 | 128.4 | 3.55 | 0.993 | 26.5 |
| kokoro_bm_george_0_6_am_onyx_0_4.wav | 65.9 | 0.095 | 8/9 | 114.5 | 3.74 | 134.7 | 3.95 | 0.996 | 24.0 |
| kokoro_bm_lewis.wav | 68.7 | 0.088 | 8/9 | 84.3 | 3.57 | 129.2 | 3.78 | 0.994 | 19.6 |
| qwen3_voicedesign.wav | 69.6 | 0.088 | 8/9 | 119.3 | 3.78 | 127.6 | 4.17 | 1.0 | 31.9 |
| qwen3_clone_split.wav | 65.9 | 0.095 | 8/9 | 90.9 | 2.76 | 134.7 | 4.33 | 0.998 | 30.2 |

\* SQUIM estimates computed on the first 30 s.

## Candidates not run, and why

| Candidate | Status (checked 2026-11-19) | Reason not run |
|---|---|---|
| Fish Speech (fishaudio) | Active. Code and weights under the Fish Audio Community License. S2-Pro weights are under the Fish Audio Research License. | The weight licences restrict commercial use, and the main models need a GPU. Excluded on licence and hardware grounds. |
| CosyVoice (Fun-CosyVoice3-0.5B) | Active, Apache-2.0 weights | Zero-shot cloning needs a reference speaker clip, and the install is heavy (Python 3.10, Matcha-TTS submodule, NVIDIA-oriented Docker). Qwen3-TTS already provides design plus clone under Apache-2.0. Kept as an alternative. |
| Microsoft VibeVoice | TTS-1.5B code was removed from the repo on 2025-09-05 after misuse. Realtime-0.5B was released 2025-12-03 (MIT), marked "research and development purposes only". | Research-only positioning and removed long-form code. Not suitable for a production deliverable. |
| F5-TTS | Code MIT; pretrained weights CC-BY-NC-4.0 (Emilia data) | Non-commercial weights. Excluded. |

## Decision

- **Primary: Qwen3-TTS 1.7B**, voice designed once from a text persona (VoiceDesign model), then **cloned** with the Base model for every sentence. Cloning keeps the voice consistent across all chapters. It had the best estimated quality (PESQ 4.33, STOI 0.998) and good intelligibility (WER 0.095). Its median pitch of about 91 Hz is a deep baritone, its pitch variation is calm, and its pace is natural (about 135 wpm). The model is Apache-2.0. It runs at about 4.3× slower than real time on this CPU (about 90 min for the whole film), which is acceptable.
- **Backup: Kokoro-82M, voice `bm_lewis`**. Apache-2.0, about 5× faster than real time on CPU. It was deep and intelligible but scored lower on quality (PESQ 3.78).
- Pronunciation is controlled with `configuration/pronunciation_lexicon.yaml` (display transliteration → TTS respelling). On-screen text and subtitles keep the scholarly transliteration.
