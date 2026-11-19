from .base import EngineAdapter


class Qwen3Adapter(EngineAdapter):
    """Qwen3-TTS 1.7B Base clone (engine of film version 1). No Arabic support, so English only."""
    key = 'qwen3'
    languages = ('en',)
