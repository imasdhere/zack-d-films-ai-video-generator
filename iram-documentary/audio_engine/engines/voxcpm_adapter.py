from .base import EngineAdapter


class VoxCPMAdapter(EngineAdapter):
    """VoxCPM2 (OpenBMB, Apache-2.0 code and weights). 2B parameters, 48 kHz output, 30 languages incl. Arabic."""
    key = 'voxcpm'
    languages = ('en', 'ar')
