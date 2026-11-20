"""Prose blocks for reports/voice_cloning_evaluation.md (facts checked on 2026-11-19; numbers come from the metrics file)."""

ENGINES = [
    '| | Audar-TTS-V1 (AudarAI) | VoxCPM2 (OpenBMB) | Qwen3-TTS 1.7B Base (baseline) |',
    '|---|---|---|---|',
    '| Tiers / size | Flash 0.55B (Transformers + GGUF); Turbo 1.64B (GGUF only); Pro 4B (enterprise, hosted) | 2B, one release (`voxcpm` 2.0.3) | 1.7B |',
    '| Method | Decoder-only LM over NeuCodec speech tokens (50 Hz); no phonemiser | Tokenizer-free diffusion autoregressive; AudioVAE V2 | LM over 12 Hz codec tokens |',
    '| Cloning input | 5–15 s reference (16 kHz) + transcript | Reference audio (+ transcript for "ultimate" cloning) | Reference audio + transcript |',
    '| Languages | Arabic first: MSA, Gulf/Emirati, Egyptian, Levantine, Maghrebi, Arabic–English code-switching; English | 30 languages including Arabic and English | 10 languages; **no Arabic** |',
    '| Output | 24 kHz | 48 kHz | 24 kHz |',
    '| Weights licence | Flash: AudarAI Open v1.0 (commercial use allowed). Turbo: Community v1.0 (limits for larger organisations). Pro: enterprise contract | Apache-2.0 | Apache-2.0 |',
    '| Runs on this CPU? | Flash: yes in principle (float32 Transformers, or GGUF via llama.cpp). **Not run**: the required NeuCodec codec is gated on Hugging Face and the token supplied in this session was rejected (`Invalid username or password`) | **Yes**, bf16 on AMX: 4.3× slower than real time, 11.5 GB peak RAM | Yes (version 1 engine) |',
    '| Apple Silicon Mac | GGUF + llama.cpp (Metal) is the practical path; NeuCodec still needed | Device "auto" selects MPS; not tested here (no Mac attached); plan for ≥16 GB unified memory | CPU; MPS undocumented |',
    '| Tier decision | Flash only. Turbo is GGUF-only and its licence limits larger organisations; Pro is not openly available. | — | Baseline only |',
]

LIMITS = [
    '- **No human listening yet.** Claude cannot hear audio. Every score above is an automatic proxy. The samples have to be listened to before anyone can say that the clones "sound like" Video 1 and Video 2. The listening column is left empty for that reason.',
    '- **Audar was not tested.** Its adapter, worker and environment are ready, and the Flash weights are downloaded. Only the gated NeuCodec codec is missing. With a valid Hugging Face token whose account has accepted the NeuCodec terms, run tests 1 and 3 with `python -m audio_engine.evaluate_engines generate --engine audar --lang en|ar`, then `score` and `write_reports evaluation`. The engine choice for each language can change after that.',
    '- **The Arabic reference is a chanted, reverberant supplication.** The clone inherits a slow, solemn pace and some room tone. A dry 30–60 s spoken recording of the same speaker would be a better reference.',
    '- **Names.** Whisper spells transliterated names in many ways, so the English word error rate includes some spelling noise. Recurring names were tuned with `audio_engine/pronunciation_probe.py` (results in `workflows/tts/eval/pronunciation_probe_voxcpm.json`) and still need a listening check.',
    '- **Speaker similarity** (WavLM-base-plus-sv) is a weak proxy. The cross-reference control (output vs the other speaker) shows the margin. It is not proof of identity.',
    '- **One seed per test.** CPU time allowed one run per engine and language.',
    '- **Hardware.** Linux CPU container, not a Mac. No GPU.',
]

SELECTION_V3 = [
    '## Version 3 update (2026-11-20): what the film now uses',
    '',
    'After listening, the owner reported that the version-2 English voice cracked and sometimes turned into another person\'s voice, '
    'and that Iram and ʿĀd were said the English way. Measurements confirmed it: 25 of 201 chunks scored below 0.90 similarity, '
    'and chunk pitch ranged from 70 to 113 Hz. A voice-stability test (`workflows/tts/eval/voice_stability_test.json`) compared four set-ups on whole paragraphs:',
    '',
    '| Set-up | Similarity mean / min | Median pitch (Video 1: 98.3 Hz) | Pitch spread between chunks | Chunks with pitch breaks | First word |',
    '|---|---|---|---|---|---|',
    '| reference mode, 9.9 s clip | 0.941 / 0.910 | 95.8 Hz | 1.44 st | 1/8 | 8/8 |',
    '| reference mode, 18 s clip | 0.956 / 0.926 | 88.1 Hz | 2.87 st | 0/8 | 8/8 |',
    '| **ultimate mode, 9.9 s clip + 0.6 s silence** | **0.982 / 0.973** | **98.6 Hz** | **0.42 st** | 2/8 | 7/8 |',
    '| ultimate mode, 18 s clip + 0.6 s silence | 0.976 / 0.971 | 91.9 Hz | 0.83 st | 1/8 | 7/8 |',
    '',
    '**Version 3 English settings:** VoxCPM2, ultimate (continuation) cloning from the Video 1 clip with 0.6 s of silence added, '
    'paragraph chunks of up to 260 characters (103 chunks instead of 210), and Iram and ʿĀd written in Arabic script (إِرَم, عَاد) so that '
    'they are said the Arabic way in the same voice. Chunk QA fails and regenerates any chunk with similarity below 0.93, a pitch shift over 3 semitones or pitch breaks. '
    'The Arabic quotations are unchanged (reference mode; they passed QA).',
    '',
]

SELECTION = [
    '### Version 2 selection (superseded for English by the version 3 settings above)', '',
    '| Language | Selected engine | Configuration | Basis |',
    '|---|---|---|---|',
    '| English | **VoxCPM2** | reference-mode cloning from Video 1 (9.9 s clip), cfg 2.0, 10 steps, bf16 CPU, VoxCPM pronunciation lexicon | The only engine from the brief that could run (Audar blocked). Clear speaker margin over the other voice (0.97 vs 0.85). Reference mode removes the first-word errors of ultimate mode (A/B test below). |',
    '| Arabic | **VoxCPM2** | reference-mode cloning from Video 2 (9.8 s clip), same settings | The only engine tested that speaks Arabic (Qwen3-TTS has no Arabic; Audar blocked). Best Arabic result of the tests: CER 0.041, similarity 0.979, steady pitch. |',
    '| Quranic | none approved | review candidates only (`assets/narration/quranic/`) | No synthetic recitation is approved without qualified review. |',
    '',
    '**Cloning mode.** VoxCPM2 offers "ultimate" cloning (the reference clip as a continuation prompt plus its transcript) and '
    '"reference" cloning (the clip as an isolated voice reference). In the first tests, ultimate mode garbled or dropped the first word of '
    'many sentences: Whisper heard "Banta-e-Rom was a city" for "Some said Iram was a city", and the first word of almost every Arabic sentence was missing. '
    'An A/B test on 8 sentences (`workflows/tts/eval/voxcpm_mode_ab.json`) gave: first word correct 1/8 (ultimate) vs 6/8 (reference); '
    'mean CER 0.141 vs 0.077; speaker similarity English 0.976 vs 0.947, Arabic 0.983 vs 0.981 (other speaker: 0.83–0.84). '
    'Wrong or missing words are not acceptable in a documentary, so production uses **reference mode**.',
    '',
    '**The cost of reference mode in English.** On the full 69-second English test, reference mode is less steady in pitch than ultimate mode: '
    'chunk-to-chunk pitch spread 3.4 semitones vs 0.7, median pitch 86 Hz vs 93 Hz (Video 1: 98 Hz). In the finished narration, the chapter medians '
    'run from 86 to 97 Hz (see `reports/final_audio_quality_control.md`). In Arabic, reference mode is steadier than ultimate mode (0.5 vs 0.9 semitones).',
    '',
    '**The version-1 engine is a strong alternative for English.** Qwen3-TTS 1.7B Base, cloning the same Video 1 clip, scored best of all English tests on the '
    'automatic measures: WER 0.043, similarity 0.986, pitch spread 0.8 semitones, PESQ estimate 3.93. It was not chosen because the brief asked for the new engines, and because '
    'no one has listened to either. Its adapter is ready: set `voice_profiles.english.preferred_engine: qwen3` in `configuration/voice_config.yaml`, then run '
    '`synthesis_manager generate --lang en --force` and the pipeline. Only the English chunks are generated again; the Arabic narration is kept.',
    '',
    '**This choice is provisional.** It rests on automatic measurements and on two engines out of three. Listen to the English tests side by side '
    '(`voxcpm-reference`, `voxcpm-ultimate`, `qwen3`) before publishing, and re-run tests 1 and 3 when Audar can be downloaded.',
]
