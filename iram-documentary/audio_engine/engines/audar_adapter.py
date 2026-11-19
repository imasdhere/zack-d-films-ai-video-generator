from .base import EngineAdapter


class AudarAdapter(EngineAdapter):
    """Audar-TTS-V1-Flash (AudarAI Open License v1.0 weights; Apache-2.0 reference code). 0.55B, 24 kHz.
    Needs the NeuCodec codec (neuphonic/neucodec), which is gated on Hugging Face."""
    key = 'audar'
    languages = ('en', 'ar')
