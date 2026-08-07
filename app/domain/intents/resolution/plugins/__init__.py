"""
HunterOS Engage V1 - Industry Resolution Plugins Package
"""

from app.domain.intents.resolution.plugins.base import IndustryResolutionPlugin
from app.domain.intents.resolution.plugins.cross_industry import CrossIndustryResolutionPlugin
from app.domain.intents.resolution.plugins.healthcare import HealthcareResolutionPlugin
from app.domain.intents.resolution.plugins.real_estate import RealEstateResolutionPlugin

__all__ = [
    "IndustryResolutionPlugin",
    "CrossIndustryResolutionPlugin",
    "RealEstateResolutionPlugin",
    "HealthcareResolutionPlugin",
]
