import hashlib
import json
from typing import Dict, Any

def compute_observation_hash(obs_dict: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 integrity hash for an environmental observation."""
    core_fields = {
        "station_id": obs_dict.get("station_id"),
        "timestamp_utc": obs_dict.get("timestamp_utc"),
        "temperature_c": obs_dict.get("temperature_c"),
        "relative_humidity_pct": obs_dict.get("relative_humidity_pct"),
        "pm2_5_ug_m3": obs_dict.get("pm2_5_ug_m3"),
        "satellite_brightness_kelvin": obs_dict.get("satellite_brightness_kelvin"),
        "provenance": str(obs_dict.get("provenance"))
    }
    encoded = json.dumps(core_fields, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
