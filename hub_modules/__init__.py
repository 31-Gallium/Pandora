from .base import BaseHubModule
from .default import DefaultLogoHub
from .media import MediaHub
from .clock import TimeHub

MODULE_MAP = {
    "default": DefaultLogoHub,
    "media": MediaHub,
    "time": TimeHub,
}
