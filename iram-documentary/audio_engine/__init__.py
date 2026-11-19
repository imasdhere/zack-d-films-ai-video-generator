"""Dual-language narration engine for THE LOST CITY OF IRAM.

Modules:
  reference_processing   extract, analyse, select and clean the narrator reference clips
  engines/               TTS adapters (VoxCPM2, Audar-TTS, Qwen3-TTS legacy); each runs in its own venv
  language_router        segment -> parts (language, voice profile, content category)
  quranic_validator      Quranic text registry and exact-text checks (Tanzil)
  narration_chunker      sentence-safe chunking
  synthesis_manager      generate, retry, resume; writes the narration manifest
  audio_postprocessor    trim, high-pass, loudness, fades, joins
  audio_quality_control  ASR, speaker similarity, pitch drift, clipping, missing or repeated text
  audio_assembler        segment index for the editor, then the mix
"""
