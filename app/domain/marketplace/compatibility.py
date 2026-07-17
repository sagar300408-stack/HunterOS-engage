import re
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from app.domain.marketplace.models import ConnectorDefinition


class CompatibilityService:
    PLATFORM_VERSION = "1.0.0" # This would realistically come from environment/config

    @staticmethod
    def is_compatible_with_platform(supported_versions: str) -> bool:
        """
        Check if the current platform version satisfies the connector's required version specification.
        E.g., supported_versions=">=1.0.0,<2.0.0"
        """
        try:
            spec = SpecifierSet(supported_versions)
            return spec.contains(CompatibilityService.PLATFORM_VERSION)
        except Exception:
            # Fallback if invalid specifier
            return False

    @staticmethod
    def is_upgrade_allowed(current_version: str, target_version: str) -> bool:
        """
        Ensure the target version is greater than the current version.
        """
        try:
            return Version(target_version) > Version(current_version)
        except Exception:
            return False

    @staticmethod
    def validate_installation(definition: ConnectorDefinition) -> bool:
        """
        Comprehensive compatibility check before allowing installation.
        """
        return CompatibilityService.is_compatible_with_platform(definition.supported_platform_versions)
