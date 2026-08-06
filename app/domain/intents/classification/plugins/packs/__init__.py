"""
HunterOS Engage V1 - Built-in Industry Plugin Packs
"""

from app.domain.intents.classification.plugins.packs.cross_industry import (
    create_cross_industry_plugin,
)
from app.domain.intents.classification.plugins.packs.healthcare import (
    create_healthcare_plugin,
)
from app.domain.intents.classification.plugins.packs.manufacturing import (
    create_manufacturing_plugin,
)
from app.domain.intents.classification.plugins.packs.real_estate import (
    create_real_estate_plugin,
)

__all__ = [
    "create_cross_industry_plugin",
    "create_real_estate_plugin",
    "create_healthcare_plugin",
    "create_manufacturing_plugin",
]
