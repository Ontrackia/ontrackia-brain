"""AMOS integration client (placeholder).

Disabled by default. When enabled per-tenant, this client can query read-only maintenance/reliability data.
"""
from typing import Any, Dict, List, Optional
from .base_client import BaseIntegrationClient


class AmosClient(BaseIntegrationClient):
    provider_name: str = "AMOS"

    @classmethod
    def is_enabled(cls, company_id: int) -> bool:
        # TODO: read tenant-specific config from secure store
        return False

    @classmethod
    def get_credentials(cls, company_id: int) -> Optional[Dict[str, Any]]:
        # TODO: obtain credentials securely per tenant
        return None
