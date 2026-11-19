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

SELECTION = []
