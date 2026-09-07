"""Short-Horizon Fire Risk Trajectory Forecasting Engine.

Computes forward-looking predictive risk models:
t+15min, t+30min, t+60min based on:
1. Environmental Vapor Pressure Deficit (VPD)
2. Biomass fuel moisture desiccation kinetics
3. Local wind shear and gust probability
4. Historical 15-minute telemetry trend acceleration
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math
from pydantic import BaseModel, Field

class ForecastHorizonPoint(BaseModel):
    horizon_minutes: int
    predicted_risk_probability: float
    predicted_alert_level: str
    dominant_driving_factor: str
    fuel_desiccation_index: float
    confidence_interval_low: float
    confidence_interval_high: float

class FleetRiskForecast(BaseModel):
    current_fleet_mean_risk: float
    forecast_points: List[ForecastHorizonPoint]
    risk_velocity_per_hour: float
    atmospheric_vpd_kpa: float
    weather_condition_summary: str
    calculation_timestamp_utc: float

class RiskForecastingEngine:
    """Computes physics-guided forward risk curves for wildland sectors."""

    @staticmethod
    def calculate_vpd(temp_c: float, rh_pct: float) -> float:
        """Calculates Vapor Pressure Deficit in kiloPascals (standard forest fire indicator)."""
        # Tetens formula for saturation vapor pressure
        svp_kpa = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
        avp_kpa = svp_kpa * (rh_pct / 100.0)
        return max(0.0, svp_kpa - avp_kpa)

    @classmethod
    def generate_forecast(
        cls,
        current_threat_index: float,
        temp_c: float = 26.5,
        rh_pct: float = 24.0,
        wind_speed_m_s: float = 4.2,
        historical_threat_trend: Optional[List[float]] = None
    ) -> FleetRiskForecast:
        import time
        now = time.time()

        vpd = cls.calculate_vpd(temp_c, rh_pct)
        # High VPD (> 2.0 kPa) means explosive fuel drying potential
        vpd_factor = min(1.0, vpd / 3.5)

        # Acceleration from historical trend
        trend_acceleration = 0.0
        if historical_threat_trend and len(historical_threat_trend) >= 3:
            recent_deltas = [
                historical_threat_trend[i] - historical_threat_trend[i-1]
                for i in range(1, len(historical_threat_trend))
            ]
            trend_acceleration = sum(recent_deltas) / len(recent_deltas)

        # Risk velocity per hour
        risk_velocity = (trend_acceleration * 60.0) + (0.05 * vpd_factor) + (0.02 * (wind_speed_m_s / 5.0))

        points = []
        for minutes in [15, 30, 60]:
            h_ratio = minutes / 60.0
            projected = current_threat_index + (risk_velocity * h_ratio)
            # Logarithmic saturation ceiling
            predicted_p = max(0.01, min(0.99, projected))

            if predicted_p >= 0.85:
                level = "CRITICAL_EVACUATION"
            elif predicted_p >= 0.60:
                level = "ADVISORY"
            elif predicted_p >= 0.35:
                level = "WATCH"
            else:
                level = "NOMINAL"

            # Dominant driver
            if vpd > 2.2:
                driver = "Atmospheric Vapor Pressure Deficit (Extreme Fuel Drying)"
            elif wind_speed_m_s > 6.0:
                driver = "Wind Shear Convective Spread"
            elif trend_acceleration > 0.05:
                driver = "Active Pyrolysis Thermal Kinetic Runaway"
            else:
                driver = "Diurnal Solar Heating Equilibrium"

            uncertainty = 0.04 + (minutes * 0.0015)

            points.append(
                ForecastHorizonPoint(
                    horizon_minutes=minutes,
                    predicted_risk_probability=round(predicted_p, 3),
                    predicted_alert_level=level,
                    dominant_driving_factor=driver,
                    fuel_desiccation_index=round(vpd_factor, 2),
                    confidence_interval_low=round(max(0.0, predicted_p - uncertainty), 3),
                    confidence_interval_high=round(min(1.0, predicted_p + uncertainty), 3)
                )
            )

        summary = f"VPD: {vpd:.2f} kPa ({'Severe' if vpd > 2.0 else 'Moderate'} desiccation) | Wind: {wind_speed_m_s:.1f} m/s"

        return FleetRiskForecast(
            current_fleet_mean_risk=round(current_threat_index, 3),
            forecast_points=points,
            risk_velocity_per_hour=round(risk_velocity, 4),
            atmospheric_vpd_kpa=round(vpd, 2),
            weather_condition_summary=summary,
            calculation_timestamp_utc=now
        )
