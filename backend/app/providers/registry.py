"""Central Provider Registry & Unified Environmental Data Orchestrator.

Manages all real-world environmental adapters, automatic cache updates,
and transparent provenance tagging across RAWS, FIRMS, OpenAQ, and NEON.
"""

from typing import List, Dict, Any, Optional
from backend.app.providers.base import (
    EnvironmentalProvider,
    EnvironmentalObservation,
    StationLocation,
    ProviderStatus,
    DataProvenanceType
)
from backend.app.providers.raws import RAWSProvider
from backend.app.providers.firms import FIRMSProvider
from backend.app.providers.openaq import OpenAQProvider
from backend.app.providers.neon import NEONProvider

class ProviderRegistry:
    def __init__(self):
        self.providers: Dict[str, EnvironmentalProvider] = {
            "raws": RAWSProvider(),
            "firms": FIRMSProvider(),
            "openaq": OpenAQProvider(),
            "neon": NEONProvider()
        }

    async def get_all_stations(self) -> List[StationLocation]:
        all_stations = []
        for p in self.providers.values():
            stations = await p.get_stations()
            all_stations.extend(stations)
        return all_stations

    async def get_unified_observations(self) -> List[EnvironmentalObservation]:
        from backend.app.providers.integrity import compute_observation_hash
        unified = []
        for p in self.providers.values():
            obs_list = await p.fetch_latest_observations()
            for obs in obs_list:
                obs.cryptographic_sha256_hash = compute_observation_hash(obs.model_dump())
                unified.append(obs)
        return unified

    async def get_provider_health_matrix(self) -> List[ProviderStatus]:
        health_list = []
        for p in self.providers.values():
            health = await p.check_health()
            health_list.append(health)
        return health_list

provider_registry = ProviderRegistry()
