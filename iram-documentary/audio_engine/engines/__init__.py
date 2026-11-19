from .base import EngineAdapter
from .voxcpm_adapter import VoxCPMAdapter
from .audar_adapter import AudarAdapter
from .qwen3_adapter import Qwen3Adapter

ADAPTERS = {'voxcpm': VoxCPMAdapter, 'audar': AudarAdapter, 'qwen3': Qwen3Adapter}


def get(key):
    return ADAPTERS[key]()
