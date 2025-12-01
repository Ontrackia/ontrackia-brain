"""Base classes for external MRO/ERP/fleet health integrations.

These connectors are pre-installed but DISABLED by default.
"""
from typing import Any, Dict, List, Optional


class BaseIntegrationClient:
    provider_name: str = "base"

    def __init__(self, company_id: int):
        self.company_id = company_id

    @classmethod
    def is_enabled(cls, company_id: int) -> bool:
        """Return True if this connector is enabled for the given tenant.

        In production this should read tenant-specific configuration from a secure store.
        """
        return False

    @classmethod
    def get_credentials(cls, company_id: int) -> Optional[Dict[str, Any]]:
        """Return credential payload for this tenant, or None if not configured."""
        return None

    def get_defect_history(self, aircraft: Optional[str] = None, ata: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent defect history (read-only)."""
        return []

    def get_reliability_trends(self, aircraft: Optional[str] = None) -> Dict[str, Any]:
        """Return simple reliability trend information (read-only)."""
        return {}
