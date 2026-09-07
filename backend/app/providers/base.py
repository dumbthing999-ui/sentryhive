"""Base Environmental Provider Interface & Data Provenance Schemas.

Enforces strict data reality classification:
- LIVE (fresh real-world API stream)
- SATELLITE (NASA FIRMS / NOAA orbital observations)
- ECOLOGICAL (NEON ecosystem research tower)
- AIR_QUALITY (OpenAQ sensor networks)
- CACHED (recent offline store)
- SIMULATED (virtual edge sensor or deterministic test fixture)
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field, field_validator
import math

class DataProvenanceType(str, Enum):
    LIVE = "LIVE"
    SATELLITE = "SATELLITE"
    ECOLOGICAL = "ECOLOGICAL"
    AIR_QUALITY = "AIR_QUALITY"
    CACHED = "CACHED"
    SIMULATED = "SIMULATED"

class ProviderHealthStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    OFFLINE_USING_CACHE = "OFFLINE_USING_CACHE"
    OFFLINE_USING_FIXTURE = "OFFLINE_USING_FIXTURE"

class StationLocation(BaseModel):
    station_id: str
    name: str
    network: str
    latitude: float
    longitude: float
    elevation_m: float
    vegetation_zone: str

    @field_validator("latitude")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v) or not (-90.0 <= v <= 90.0):
            raise ValueError(f"Invalid latitude: {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v) or not (-180.0 <= v <= 180.0):
            raise ValueError(f"Invalid longitude: {v}")
        return v

class EnvironmentalObservation(BaseModel):
    observation_id: str
    station_id: str
    station_name: str
    provider_name: str
    provenance: DataProvenanceType
    timestamp_utc: float
    age_seconds: float
    
    # Atmospheric metrics
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    wind_speed_m_s: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_gust_m_s: Optional[float] = None
    barometric_pressure_hpa: Optional[float] = None
    
    # Particulate & chemical indicators
    pm2_5_ug_m3: Optional[float] = None
    pm10_ug_m3: Optional[float] = None
    co_ppm: Optional[float] = None
    voc_ppb: Optional[float] = None
    
    # Ecological & satellite indicators
    fuel_moisture_10hr_pct: Optional[float] = None
    solar_radiation_w_m2: Optional[float] = None
    satellite_brightness_kelvin: Optional[float] = None
    satellite_confidence_pct: Optional[float] = None
    satellite_frp_mw: Optional[float] = None # Fire Radiative Power in MegaWatts
    
    # Data quality metadata
    data_quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    validation_status: str = "VALID"
    cryptographic_sha256_hash: Optional[str] = None

class ProviderStatus(BaseModel):
    provider_name: str
    status: ProviderHealthStatus
    endpoint_url: str
    last_successful_fetch_utc: Optional[float] = None
    active_stations_count: int = 0
    is_live_network_enabled: bool = True
    error_message: Optional[str] = None

class EnvironmentalProvider(ABC):
    """Abstract Base Class for public environmental data providers."""

    def __init__(self, name: str, endpoint: str):
        self.name = name
        self.endpoint = endpoint
        self.last_fetch: Optional[float] = None
        self.status = ProviderHealthStatus.CONNECTED
        self.last_error: Optional[str] = None

    @abstractmethod
    async def get_stations(self) -> List[StationLocation]:
        """Returns station metadata within the target Tahoe National Forest sector."""
        pass

    @abstractmethod
    async def fetch_latest_observations(self) -> List[EnvironmentalObservation]:
        """Fetches and normalizes observations into the canonical schema."""
        pass

    @abstractmethod
    async def check_health(self) -> ProviderStatus:
        """Evaluates connectivity or fallback status."""
        pass
