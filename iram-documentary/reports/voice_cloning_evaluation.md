# Voice-cloning evaluation

Date: 2026-11-20. Hardware: 4-vCPU Intel Xeon (AVX-512, AMX-BF16), 15 GiB RAM, no GPU, Linux cloud container (not a Mac; see `reports/system_hardware_audit.md`).

## Result

## Version 3 update (2026-11-20): what the film now uses

After listening, the owner reported that the version-2 English voice cracked and sometimes turned into another person's voice, and that Iram and ʿĀd were said the English way. Measurements confirmed it: 25 of 201 chunks scored below 0.90 similarity, and chunk pitch ranged from 70 to 113 Hz. A voice-stability test (`workflows/tts/eval/voice_stability_test.json`) compared four set-ups on whole paragraphs:

| Set-up | Similarity mean / min | Median pitch (Video 1: 98.3 Hz) | Pitch spread between chunks | Chunks with pitch breaks | First word |
|---|---|---|---|---|---|
| reference mode, 9.9 s clip | 0.941 / 0.910 | 95.8 Hz | 1.44 st | 1/8 | 8/8 |
| reference mode, 18 s clip | 0.956 / 0.926 | 88.1 Hz | 2.87 st | 0/8 | 8/8 |
| **ultimate mode, 9.9 s clip + 0.6 s silence** | **0.982 / 0.973** | **98.6 Hz** | **0.42 st** | 2/8 | 7/8 |
| ultimate mode, 18 s clip + 0.6 s silence | 0.976 / 0.971 | 91.9 Hz | 0.83 st | 1/8 | 7/8 |

**Version 3 English settings:** VoxCPM2, ultimate (continuation) cloning from the Video 1 clip with 0.6 s of silence added, paragraph chunks of up to 260 characters (103 chunks instead of 210), and Iram and ʿĀd written in Arabic script (إِرَم, عَاد) so that they are said the Arabic way in the same voice. Chunk QA fails and regenerates any chunk with similarity below 0.93, a pitch shift over 3 semitones or pitch breaks. The Arabic quotations are unchanged (reference mode; they passed QA).

### Version 2 selection (superseded for English by the version 3 settings above)

| Language | Selected engine | Configuration | Basis |
|---|---|---|---|
| English | **VoxCPM2** | reference-mode cloning from Video 1 (9.9 s clip), cfg 2.0, 10 steps, bf16 CPU, VoxCPM pronunciation lexicon | The only engine from the brief that could run (Audar blocked). Clear speaker margin over the other voice (0.97 vs 0.85). Reference mode removes the first-word errors of ultimate mode (A/B test below). |
| Arabic | **VoxCPM2** | reference-mode cloning from Video 2 (9.8 s clip), same settings | The only engine tested that speaks Arabic (Qwen3-TTS has no Arabic; Audar blocked). Best Arabic result of the tests: CER 0.041, similarity 0.979, steady pitch. |
| Quranic | none approved | review candidates only (`assets/narration/quranic/`) | No synthetic recitation is approved without qualified review. |

**Cloning mode.** VoxCPM2 offers "ultimate" cloning (the reference clip as a continuation prompt plus its transcript) and "reference" cloning (the clip as an isolated voice reference). In the first tests, ultimate mode garbled or dropped the first word of many sentences: Whisper heard "Banta-e-Rom was a city" for "Some said Iram was a city", and the first word of almost every Arabic sentence was missing. An A/B test on 8 sentences (`workflows/tts/eval/voxcpm_mode_ab.json`) gave: first word correct 1/8 (ultimate) vs 6/8 (reference); mean CER 0.141 vs 0.077; speaker similarity English 0.976 vs 0.947, Arabic 0.983 vs 0.981 (other speaker: 0.83–0.84). Wrong or missing words are not acceptable in a documentary, so production uses **reference mode**.

**The cost of reference mode in English.** On the full 69-second English test, reference mode is less steady in pitch than ultimate mode: chunk-to-chunk pitch spread 3.4 semitones vs 0.7, median pitch 86 Hz vs 93 Hz (Video 1: 98 Hz). In the finished narration, the chapter medians run from 86 to 97 Hz (see `reports/final_audio_quality_control.md`). In Arabic, reference mode is steadier than ultimate mode (0.5 vs 0.9 semitones).

**The version-1 engine is a strong alternative for English.** Qwen3-TTS 1.7B Base, cloning the same Video 1 clip, scored best of all English tests on the automatic measures: WER 0.043, similarity 0.986, pitch spread 0.8 semitones, PESQ estimate 3.93. It was not chosen because the brief asked for the new engines, and because no one has listened to either. Its adapter is ready: set `voice_profiles.english.preferred_engine: qwen3` in `configuration/voice_config.yaml`, then run `synthesis_manager generate --lang en --force` and the pipeline. Only the English chunks are generated again; the Arabic narration is kept.

**This choice is provisional.** It rests on automatic measurements and on two engines out of three. Listen to the English tests side by side (`voxcpm-reference`, `voxcpm-ultimate`, `qwen3`) before publishing, and re-run tests 1 and 3 when Audar can be downloaded.

## Consent

The project owner confirmed that they own these voices or have the speakers' permission to clone them for this documentary. Use the cloned voices for this documentary only. Do not use them for impersonation, deception or any other project. Confirmed by the project owner on 2026-11-19.

## References

| Profile | Source | Clip | Duration | Median F0 | Notes |
|---|---|---|---|---|---|
| english_narrator | Video1.mp4 | 3.09–12.96 s | 10.24 s | 98.3 Hz | see `voice_profiles/english_narrator/reference_quality_report.md` |
| arabic_narrator | Video2.mp4 | 37.24–47.02 s | 10.15 s | 68.7 Hz | see `voice_profiles/arabic_narrator/reference_quality_report.md` |

Speaker-embedding cosine between the two references: 0.841 (two different men; this is the 'different speaker' baseline for the scores below).

## Engines investigated

| | Audar-TTS-V1 (AudarAI) | VoxCPM2 (OpenBMB) | Qwen3-TTS 1.7B Base (baseline) |
|---|---|---|---|
| Tiers / size | Flash 0.55B (Transformers + GGUF); Turbo 1.64B (GGUF only); Pro 4B (enterprise, hosted) | 2B, one release (`voxcpm` 2.0.3) | 1.7B |
| Method | Decoder-only LM over NeuCodec speech tokens (50 Hz); no phonemiser | Tokenizer-free diffusion autoregressive; AudioVAE V2 | LM over 12 Hz codec tokens |
| Cloning input | 5–15 s reference (16 kHz) + transcript | Reference audio (+ transcript for "ultimate" cloning) | Reference audio + transcript |
| Languages | Arabic first: MSA, Gulf/Emirati, Egyptian, Levantine, Maghrebi, Arabic–English code-switching; English | 30 languages including Arabic and English | 10 languages; **no Arabic** |
| Output | 24 kHz | 48 kHz | 24 kHz |
| Weights licence | Flash: AudarAI Open v1.0 (commercial use allowed). Turbo: Community v1.0 (limits for larger organisations). Pro: enterprise contract | Apache-2.0 | Apache-2.0 |
| Runs on this CPU? | Flash: yes in principle (float32 Transformers, or GGUF via llama.cpp). **Not run**: the required NeuCodec codec is gated on Hugging Face and the token supplied in this session was rejected (`Invalid username or password`) | **Yes**, bf16 on AMX: 4.3× slower than real time, 11.5 GB peak RAM | Yes (version 1 engine) |
| Apple Silicon Mac | GGUF + llama.cpp (Metal) is the practical path; NeuCodec still needed | Device "auto" selects MPS; not tested here (no Mac attached); plan for ≥16 GB unified memory | CPU; MPS undocumented |
| Tier decision | Flash only. Turbo is GGUF-only and its licence limits larger organisations; Pro is not openly available. | — | Baseline only |

## Test design

One standard text per language (`workflows/tts/eval/clone_test_texts.yaml`), identical for every engine. English: 161 words from the approved screenplay. Arabic: 145 words of Modern Standard Arabic written for the test from claims in the claim matrix. Both texts go through the production chunker (sentence boundaries, at most 260/200 characters) and the production pronunciation lexicon, so the test reflects real production. Each engine received the same reference clip and transcript. Seeds are fixed (base 20261119 + chunk index). Chunks are joined with 0.45 s pauses.

## Test matrix

| Test | Reference | Engine | Language | Status | Output |
|---|---|---|---|---|---|
| 1 | Video 1 | Audar-TTS-V1-Flash | English | not run: NeuCodec codec is gated on Hugging Face and the access token was not accepted | — |
| 2 | Video 1 | VoxCPM2, reference mode (production) | English | done | `voice_profiles/english_narrator/test_samples/voxcpm-reference_en_test.wav` (local only) |
| 2b | Video 1 | VoxCPM2, ultimate mode | English | done | `voice_profiles/english_narrator/test_samples/voxcpm-ultimate_en_test.wav` (local only) |
| 3 | Video 2 | Audar-TTS-V1-Flash | Arabic | not run: NeuCodec codec is gated on Hugging Face and the access token was not accepted | — |
| 4 | Video 2 | VoxCPM2, reference mode (production) | Arabic | done | `voice_profiles/arabic_narrator/test_samples/voxcpm-reference_ar_test.wav` (local only) |
| 4b | Video 2 | VoxCPM2, ultimate mode | Arabic | done | `voice_profiles/arabic_narrator/test_samples/voxcpm-ultimate_ar_test.wav` (local only) |
| baseline | Video 1 | Qwen3-TTS 1.7B Base (version 1 engine) | English | done | `voice_profiles/english_narrator/test_samples/qwen3_en_test.wav` (local only) |

## Measurements

| Metric | Qwen3-TTS 1.7B Base (version 1 engine) EN | VoxCPM2, reference mode (production) EN | VoxCPM2, ultimate mode EN | VoxCPM2, reference mode (production) AR | VoxCPM2, ultimate mode AR |
|---|---|---|---|---|---|
| Audio length (s) | 61.47 | 68.97 | 63.4 | 86.09 | 105.11 |
| Generation wall time (s, incl. model load) | 349.4 | 276.4 | 292.4 | 322.9 | 448.6 |
| Real-time factor (compute ÷ audio) | 4.73 | 3.77 | 4.33 | 3.55 | 4.11 |
| Peak memory (GB RSS) | 6.87 | 11.32 | 11.48 | 10.72 | 11.19 |
| Mean CPU use (% of one core; 400 = all 4) | 244 | 370 | 367 | 373 | 368 |
| Retries | 0 | 0 | 0 | 0 | 0 |
| ASR word error rate (Whisper large-v3-turbo) | 0.043 | 0.06 | 0.074 | 0.048 | 0.11 |
| ASR character error rate | 0.012 | 0.02 | 0.037 | 0.041 | 0.084 |
| Speaker similarity to own reference (WavLM-SV cosine) | 0.986 | 0.97 | 0.989 | 0.979 | 0.99 |
| Similarity to the other reference (control) | 0.829 | 0.845 | 0.843 | 0.811 | 0.829 |
| Chunk similarity, mean ± sd | 0.977 ± 0.007 | 0.947 ± 0.017 | 0.973 ± 0.01 | 0.973 ± 0.008 | 0.957 ± 0.075 |
| Median F0 (Hz) / shift vs reference (semitones) | 93.3 / -0.9 | 86.1 / -2.29 | 93.3 / -0.9 | 65.6 / -0.39 | 66.7 / -0.1 |
| Pitch spread (semitones) | 3.08 | 5.05 | 3.22 | 1.95 | 2.24 |
| Chunk-to-chunk F0 spread (semitones) | 0.84 | 3.41 | 0.69 | 0.49 | 0.86 |
| Speaking rate (words/min, ASR count) | 155.2 | 137.4 | 147.6 | 99.0 | 78.2 |
| SQUIM estimates: STOI / PESQ / SI-SDR | 0.998 / 3.93 / 27.8 dB | 0.987 / 3.09 / 17.5 dB | 0.99 / 3.25 / 23.6 dB | 0.993 / 3.27 / 20.0 dB | 0.984 / 2.75 / 19.2 dB |
| Internal silences > 1 s / clipped samples | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Reference values: English reference median F0 98.3 Hz, spread 3.51 st; Arabic reference median F0 67.1 Hz, spread 1.68 st.

## Scores (1–10)

These scores are **provisional and metric-derived**. A dash means that no valid automatic proxy exists: the criterion needs a human listening test. Mapping: similarity from the WavLM cosine (0.80 → 5, 0.97 → 10); pronunciation from WER (English) or CER (Arabic) (10 − 40 × error); rhythm from the speaking-rate ratio to the reference (English only, because the Arabic reference is chanted); prosody from the pitch-spread ratio and pitch shift; consistency from chunk-to-chunk similarity and pitch spread; artefacts from the SQUIM PESQ estimate, long silences and clipping.

| Criterion | Qwen3-TTS 1.7B Base (version 1 engine) EN | VoxCPM2, reference mode (production) EN | VoxCPM2, ultimate mode EN | VoxCPM2, reference mode (production) AR | VoxCPM2, ultimate mode AR | Listening score (fill in) |
|---|---|---|---|---|---|---|
| Similarity to the reference speaker | 10 | 10 | 10 | 10 | 10 |  |
| Naturalness | — | — | — | — | — |  |
| Pronunciation accuracy | 8 | 8 | 7 | 8 | 7 |  |
| Accent preservation | — | — | — | — | — |  |
| Rhythm and pacing | 9 | 7 | 9 | — | — |  |
| Prosody | 8 | 5 | 9 | 8 | 7 |  |
| Emotional suitability | — | — | — | — | — |  |
| Consistency between generated segments | 8 | 4 | 8 | 9 | 4 |  |
| Absence of robotic artefacts | 9 | 7 | 8 | 8 | 7 |  |
| Overall (mean of scored rows) | 8.7 | 6.8 | 8.5 | 8.6 | 7.0 |  |

## ASR transcripts of the test outputs

**Qwen3-TTS 1.7B Base (version 1 engine), English:** Tabari gathered the opinions of the generations before him. Some said Iram was a city, Alexandria, according to one early authority, Damascus, according to another. But the view at Tabari preferred was simpler. The Imad, he argued, were the poles of tents. A-Aid-Eid were people of poles, travelers moving with the rains and the pasture. And he added a sentence that cuts to the heart of this mystery. No building of theirs with columns, he wrote, is known through any authentic report. The search later led to Shisr, a small oasis in Dofar, about 170 kilometers inland, with a Bedouin well and a ruined fort that earlier travelers had dismissed as only a few centuries old. Perhaps that is the real lesson of Irem. A people can survive in memory long after their stones are gone, or even if they never built in stone at all. A few words in a sacred text have outlived empires, maps, and explorers.

**VoxCPM2, reference mode (production), English:** Al-Tabari gathered the opinions of the generations before him. Some said Eram was a city, Alexandria according to one early authority, Damascus according to another. But the view Al-Tabari preferred was simpler. The Imad, he argued, were the poles of tents. Dey-hadi were people of poles, travelers moving with the rains and the pasture. And he added a sentence that cuts to the heart of this mystery. No building of theirs with columns, he wrote, is known through any authentic report. The search later led to Shishr, a small oasis in Dofar, about 170 kilometers inland, with a Bedouin well and a ruined fort that earlier travelers had dismissed as only a few centuries old. Perhaps that is the real lesson of Iram, a people can survive in memory long after their stones are gone, or even if they never built in stone at all. A few words in a sacred text have outlived empires, maps, and explorers.

**VoxCPM2, ultimate mode, English:** But Tabari gathered the opinions of the generations before him. Banta-e-Rom was a city, Alexandria according to one early authority, Damascus according to another. But the view at Tabari preferred was simpler. The Imad, he argued, were the poles of tents. It were people of poles, travelers, moving with the rains and the pasture. He added a sentence that cuts to the heart of this mystery. no building of theirs with columns, he wrote, is known through any authentic report. The search later led to Shishir, a small oasis in Dofar, about 170 kilometers inland, with a Bedouin well and a ruined fort that earlier travelers had dismissed as only a few centuries old. Perhaps that is the real lesson of Iram. People can survive in memory long after their stones are gone, or even if they never built in stone at all. In few words in the sacred text have outlived empires, maps, and explorers.

**VoxCPM2, reference mode (production), Arabic:** في جنوب الجزيرة العربية حيث تمتد رمال الربع الخالي بلا نهاية يتردد منذ قرون اسم قديم إرام ذات العماد ذكرها القرآن الكريم مرة واحدة مقرونة بقوم عاد الذين أرسل إليهم النبي هود فما أرم أهي مدينة ذات أعمدة شاهقة أم قبيلة من الرحل تتنقل بخيرها وراء المطر والمرعى جمع الإمام الطبري أقوال من سبقه ورجح أن العمادة هي أعمدة الخيام وقال إنه لا يعلم لهم بناء بالعماد بخبر صحيح وبعد أربعة قرون وافقه ابن كثير وعد حكايات المدينة الذهبية من خرافات الإسرائيليات وفي عام 1992 كشفت بعثة أثرية في شصر بمحافظة ظفار في سلطنة عمان عن حصن قديم على طرق تجارة اللبان أعلنت الصحف أن مدينة أوبار قد وجدت غير أن المنقبين أنفسهم رأوا أن أوبار اسم إقليم وقوم لا مدينة واحدة ربما لا تكون إرم مدينة ضائعة تنتظر من يكتشفها ربما كانت درسا محفوظا في الذاكرة أطول عمرا من الحجارة والأعمدة

**VoxCPM2, ultimate mode, Arabic:** جنوب الجزيرة العربية حيث تمتد رمال الربع الخالي بلا نهاية يتردد منذ قرون اسم قديم إرم ذات العماد القرآن الكريم مرة واحدة مقرونة بقوم عاد الذين أرسل إليهم النبي هود أرم أهي مدينة ذات أعمدة شاهقة أم قبيلة من الرحل تتنقل بخيامها وراء المطر والمرعى الإمام الطبري أقوى لمن سبقه ورجح أن العمادة هي أعمدة الخيام وقال إنه لا يعلم لهم بناء بالعماد بخبر صحيح أربعة قرون وافقه ابن كثير وعد حكامه حكايات المدينة الذهبية من خرافات الإسرائيليات في عام 1992 كشفت بعثة أثرية في شصر بمحافظة ظفار في سلطنة عمان عن حصن قديم على طرق تجارة اللبان أعلنت الصحف أن مدينة أوبار قد وجدت غير أن المنقبين أنفسهم رأوا أن أوبار اسم إقليم وقوم لا مدينة واحدة لا تكون إرم مدينة ضائعة تنتظر من يكتشفها يما كانت درسا محفوظا في الذاكرة أطول عمرا من الحجارة والأعمدة

## Limitations

- **No human listening yet.** Claude cannot hear audio. Every score above is an automatic proxy. The samples have to be listened to before anyone can say that the clones "sound like" Video 1 and Video 2. The listening column is left empty for that reason.
- **Audar was not tested.** Its adapter, worker and environment are ready, and the Flash weights are downloaded. Only the gated NeuCodec codec is missing. With a valid Hugging Face token whose account has accepted the NeuCodec terms, run tests 1 and 3 with `python -m audio_engine.evaluate_engines generate --engine audar --lang en|ar`, then `score` and `write_reports evaluation`. The engine choice for each language can change after that.
- **The Arabic reference is a chanted, reverberant supplication.** The clone inherits a slow, solemn pace and some room tone. A dry 30–60 s spoken recording of the same speaker would be a better reference.
- **Names.** Whisper spells transliterated names in many ways, so the English word error rate includes some spelling noise. Recurring names were tuned with `audio_engine/pronunciation_probe.py` (results in `workflows/tts/eval/pronunciation_probe_voxcpm.json`) and still need a listening check.
- **Speaker similarity** (WavLM-base-plus-sv) is a weak proxy. The cross-reference control (output vs the other speaker) shows the margin. It is not proof of identity.
- **One seed per test.** CPU time allowed one run per engine and language.
- **Hardware.** Linux CPU container, not a Mac. No GPU.
