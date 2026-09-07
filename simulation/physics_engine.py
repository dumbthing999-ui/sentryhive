"""Forest Canopy Atmospheric & Pyrolysis Kinetics Cyber-Physical Simulation Engine.

Simulates:
- Canopy atmospheric conditions (temperature, relative humidity, VPD, barometric pressure, wind vectors)
- Biomass pyrolysis combustion kinetics (Arrhenius thermal degradation, moisture desiccation, CO/VOC/PM curves)
- 3D Gaussian plume dispersion from point combustion sources to distributed sensor nodes
- Melexis MLX90640 32x24 thermal far-IR radiance array with 2D Sobel spatial gradients and centroid velocity
- Knowles INMP441 acoustic cavitation cellular wall rupture signatures and spectral energy distribution
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
import math
import numpy as np
from scipy.signal import convolve2d


@dataclass
class AtmosphericState:
    """Instantaneous canopy atmospheric conditions."""
    timestamp_s: float
    temperature_c: float
    relative_humidity_pct: float
    barometric_pressure_hpa: float
    vapor_pressure_deficit_kpa: float
    wind_speed_m_s: float
    wind_direction_deg: float  # 0 = North, 90 = East, 180 = South, 270 = West
    wind_u: float  # Eastward velocity component (m/s)
    wind_v: float  # Northward velocity component (m/s)
    solar_irradiance_w_m2: float


@dataclass
class CombustionState:
    """Biomass pyrolysis and combustion source state."""
    timestamp_s: float
    source_id: str
    position_xyz: Tuple[float, float, float]  # (x, y, z) in meters
    fuel_temperature_c: float
    fuel_moisture_content_pct: float
    heat_flux_kw_m2: float
    pyrolysis_rate_kg_s: float
    co_emission_rate_mg_s: float
    voc_emission_rate_mg_s: float
    pm1_0_emission_rate_mg_s: float
    pm2_5_emission_rate_mg_s: float
    pm4_0_emission_rate_mg_s: float
    pm10_0_emission_rate_mg_s: float
    acoustic_crackle_rate_hz: float
    active: bool = True


@dataclass
class ThermalMatrixResult:
    """MLX90640 32x24 thermal far-IR spatial evaluation."""
    raw_matrix: np.ndarray  # Shape (24, 32) in degrees Celsius
    ambient_median_c: float
    max_temperature_c: float
    min_temperature_c: float
    delta_max_c: float
    sobel_gradient_max: float  # deg C / pixel
    hotspot_pixels: int
    centroid_xy: Optional[Tuple[float, float]]  # (x, y) pixel coordinates
    plume_velocity_mm_s: float  # Estimated centroid drift velocity


@dataclass
class AcousticSignatureResult:
    """INMP441 acoustic sensor evaluation."""
    crackle_event_rate_hz: float
    spectral_energy_ratio: float  # Energy in 800Hz-4500Hz vs total
    peak_frequency_hz: float
    pyrolysis_confidence: float  # 0.0 to 1.0


class CanopyMicroclimateModel:
    """Forest canopy microclimate with diurnal cycle, Tetens VPD, and canopy turbulence."""

    def __init__(
        self,
        base_temperature_c: float = 21.0,
        diurnal_amplitude_c: float = 8.0,
        base_humidity_pct: float = 60.0,
        base_pressure_hpa: float = 1013.25,
        elevation_m: float = 450.0,
        base_wind_speed_m_s: float = 2.0,
        base_wind_dir_deg: float = 45.0,  # North-East
        seed: int = 42,
    ):
        self.base_temp = base_temperature_c
        self.diurnal_amp = diurnal_amplitude_c
        self.base_humidity = base_humidity_pct
        self.base_pressure = base_pressure_hpa
        self.elevation_m = elevation_m
        self.base_wind_speed = base_wind_speed_m_s
        self.base_wind_dir = base_wind_dir_deg
        self.rng = np.random.RandomState(seed)

        # Wind turbulence state (Ornstein-Uhlenbeck process)
        self.wind_u_turb = 0.0
        self.wind_v_turb = 0.0

    def compute_state(self, timestamp_s: float, z_height_m: float = 2.5) -> AtmosphericState:
        """Compute microclimate parameters for current time and sensor height."""
        # Diurnal phase: cycle period = 86400s (24 hours), peak temp around 14:00 (50400s)
        time_in_day = timestamp_s % 86400.0
        solar_phase = 2.0 * math.pi * (time_in_day - 50400.0) / 86400.0

        # Temperature variation: warmest at 14:00, coolest before sunrise
        elevation_temp_lapse = -0.0065 * self.elevation_m
        diurnal_temp = self.diurnal_amp * math.cos(solar_phase)
        ambient_temp = self.base_temp + elevation_temp_lapse + diurnal_temp

        # Solar irradiance (W/m2): positive during daylight hours (06:00 to 18:00)
        daylight_phase = 2.0 * math.pi * (time_in_day - 43200.0) / 86400.0
        solar_insolation = max(0.0, 950.0 * math.cos(daylight_phase))

        # Relative humidity anti-correlates with temperature
        # Tetens equation for saturation vapor pressure e_s(T) in kPa
        e_sat = 0.61078 * math.exp((17.27 * ambient_temp) / (ambient_temp + 237.3))
        humidity_fluctuation = - (diurnal_temp / self.diurnal_amp) * 22.0
        rh_pct = float(np.clip(self.base_humidity + humidity_fluctuation, 12.0, 98.0))

        # Actual vapor pressure and VPD
        e_act = e_sat * (rh_pct / 100.0)
        vpd_kpa = max(0.0, e_sat - e_act)

        # Barometric pressure with hypsometric altitude compensation
        pressure_hpa = self.base_pressure * ((1.0 - 0.0065 * self.elevation_m / 288.15) ** 5.255)

        # Wind dynamics: Canopy logarithmic wind profile & stochastic gust turbulence
        # u(z) = u_ref * ln(z / z0) / ln(z_ref / z0)
        z0 = 0.35  # Canopy roughness length (meters)
        height_factor = max(0.2, math.log(max(z_height_m, z0 + 0.1) / z0) / math.log(10.0 / z0))

        # Update turbulence with Ornstein-Uhlenbeck (damping=0.92, noise=0.15)
        self.wind_u_turb = 0.92 * self.wind_u_turb + 0.15 * float(self.rng.normal())
        self.wind_v_turb = 0.92 * self.wind_v_turb + 0.15 * float(self.rng.normal())

        dir_rad = math.radians(self.base_wind_dir)
        mean_u = self.base_wind_speed * math.sin(dir_rad) * height_factor
        mean_v = self.base_wind_speed * math.cos(dir_rad) * height_factor

        u = mean_u + self.wind_u_turb
        v = mean_v + self.wind_v_turb
        actual_speed = math.sqrt(u * u + v * v)
        actual_dir = (math.degrees(math.atan2(u, v)) + 360.0) % 360.0

        return AtmosphericState(
            timestamp_s=timestamp_s,
            temperature_c=float(ambient_temp),
            relative_humidity_pct=float(rh_pct),
            barometric_pressure_hpa=float(pressure_hpa),
            vapor_pressure_deficit_kpa=float(vpd_kpa),
            wind_speed_m_s=float(max(0.1, actual_speed)),
            wind_direction_deg=float(actual_dir),
            wind_u=float(u),
            wind_v=float(v),
            solar_irradiance_w_m2=float(solar_insolation),
        )


class PyrolysisKineticsModel:
    """Biomass pyrolysis degradation kinetics based on Arrhenius equations and fuel moisture."""

    # Universal Gas Constant J/(mol*K)
    R_GAS = 8.314462

    # Kinetic parameters: Frequency factor A (1/s) and Activation Energy Ea (J/mol)
    # Hemicellulose: 200°C - 260°C (emits CO, acetic acid, furfural)
    A_HEMI = 1.2e7
    EA_HEMI = 1.05e5

    # Cellulose: 240°C - 350°C (emits levoglucosan, formaldehyde, CO, fine aerosols)
    A_CELL = 4.8e9
    EA_CELL = 1.45e5

    # Lignin: 280°C - 500°C (char formation, heavy aromatics, persistent smolder)
    A_LIGNIN = 1.5e4
    EA_LIGNIN = 7.8e4

    def __init__(
        self,
        source_id: str = "src_01",
        position_xyz: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        initial_fuel_temp_c: float = 20.0,
        initial_fuel_moisture_pct: float = 14.0,
        fuel_mass_kg: float = 12.0,
    ):
        self.source_id = source_id
        self.pos = position_xyz
        self.fuel_temp_c = initial_fuel_temp_c
        self.fmc_pct = initial_fuel_moisture_pct
        self.fuel_mass_kg = fuel_mass_kg

        # Compositional dry mass fractions
        self.mass_hemi = 0.25 * fuel_mass_kg
        self.mass_cell = 0.50 * fuel_mass_kg
        self.mass_lignin = 0.25 * fuel_mass_kg

    def step(
        self,
        dt_s: float,
        heat_flux_kw_m2: float,
        ambient_temp_c: float,
        timestamp_s: float,
    ) -> CombustionState:
        """Advance pyrolysis thermal kinetics by dt_s seconds."""
        if heat_flux_kw_m2 <= 0.0 and self.fuel_temp_c <= ambient_temp_c + 2.0:
            # Cold / inactive source
            return CombustionState(
                timestamp_s=timestamp_s,
                source_id=self.source_id,
                position_xyz=self.pos,
                fuel_temperature_c=ambient_temp_c,
                fuel_moisture_content_pct=self.fmc_pct,
                heat_flux_kw_m2=0.0,
                pyrolysis_rate_kg_s=0.0,
                co_emission_rate_mg_s=0.0,
                voc_emission_rate_mg_s=0.0,
                pm1_0_emission_rate_mg_s=0.0,
                pm2_5_emission_rate_mg_s=0.0,
                pm4_0_emission_rate_mg_s=0.0,
                pm10_0_emission_rate_mg_s=0.0,
                acoustic_crackle_rate_hz=0.0,
                active=False,
            )

        # Thermal heat balance:
        # Wood specific heat Cp ~ 1.7 kJ/(kg*K), Water Lv = 2260 kJ/kg
        cp_wood = 1.70  # kJ/(kg*K)
        fuel_area = 0.6  # m2 effective surface area

        # Absorbed heat rate (kW)
        q_in_kw = heat_flux_kw_m2 * fuel_area

        # Heat losses: convective cooling + radiative emission
        h_conv = 0.015  # kW/(m2*K)
        q_conv_loss = h_conv * fuel_area * (self.fuel_temp_c - ambient_temp_c)
        sigma_sb = 5.67037e-11  # kW/(m2*K4)
        t_fuel_k = self.fuel_temp_c + 273.15
        t_amb_k = ambient_temp_c + 273.15
        q_rad_loss = 0.88 * sigma_sb * fuel_area * (t_fuel_k ** 4 - t_amb_k ** 4)

        net_q_kw = q_in_kw - q_conv_loss - q_rad_loss

        # Phase 1: Water evaporation buffer when FMC > 1% and T >= 95°C
        if self.fmc_pct > 1.0 and self.fuel_temp_c >= 95.0:
            # Latent heat of vaporization absorbs incoming energy
            latent_heat_lv = 2260.0  # kJ/kg
            evap_rate_kg_s = max(0.0, min(net_q_kw / latent_heat_lv, 0.02 * self.fuel_mass_kg))
            water_loss_pct = (evap_rate_kg_s * dt_s / self.fuel_mass_kg) * 100.0
            self.fmc_pct = max(0.5, self.fmc_pct - water_loss_pct)

            # Temperature climbs slowly while boiling water
            dt_temp = (net_q_kw * 0.25) / (self.fuel_mass_kg * cp_wood) * dt_s
            self.fuel_temp_c += dt_temp
        else:
            # Dry thermal climb
            dt_temp = net_q_kw / (self.fuel_mass_kg * cp_wood) * dt_s
            self.fuel_temp_c = max(ambient_temp_c, self.fuel_temp_c + dt_temp)

        # Arrhenius chemical reaction rate constants k = A * exp(-Ea / (R * T))
        k_hemi = self.A_HEMI * math.exp(-self.EA_HEMI / (self.R_GAS * t_fuel_k)) if t_fuel_k > 350.0 else 0.0
        k_cell = self.A_CELL * math.exp(-self.EA_CELL / (self.R_GAS * t_fuel_k)) if t_fuel_k > 400.0 else 0.0
        k_lig = self.A_LIGNIN * math.exp(-self.EA_LIGNIN / (self.R_GAS * t_fuel_k)) if t_fuel_k > 450.0 else 0.0

        # Pyrolysis degradation rates (kg/s)
        rate_hemi = min(self.mass_hemi, k_hemi * self.mass_hemi)
        rate_cell = min(self.mass_cell, k_cell * self.mass_cell)
        rate_lig = min(self.mass_lignin, k_lig * self.mass_lignin)
        total_pyrolysis_kg_s = rate_hemi + rate_cell + rate_lig

        # Update remaining masses
        self.mass_hemi = max(0.001, self.mass_hemi - rate_hemi * dt_s)
        self.mass_cell = max(0.001, self.mass_cell - rate_cell * dt_s)
        self.mass_lignin = max(0.001, self.mass_lignin - rate_lig * dt_s)

        # Gas and Particulate Emission Curves
        # Smoldering produces abundant CO and VOCs relative to flaming
        # Units: mg/s
        co_mg_s = (rate_hemi * 0.18 + rate_cell * 0.12 + rate_lig * 0.08) * 1e6
        voc_mg_s = (rate_hemi * 0.32 + rate_cell * 0.25 + rate_lig * 0.14) * 1e6

        # Particulate emissions:
        # In smoldering pyrolysis, condensed tar droplets form ultra-fine aerosols.
        # High moisture amplifies white smoke aerosol generation.
        moisture_multiplier = 1.0 + 0.04 * self.fmc_pct
        base_pm2_5_mg_s = (rate_cell * 0.045 + rate_hemi * 0.035) * 1e6 * moisture_multiplier

        pm2_5_mg_s = max(0.0, base_pm2_5_mg_s)
        pm1_0_mg_s = 0.72 * pm2_5_mg_s
        pm4_0_mg_s = 1.06 * pm2_5_mg_s
        pm10_0_mg_s = 1.14 * pm2_5_mg_s  # Smoldering ratio PM2.5/PM10 ~ 0.88

        # Acoustic crackle rate: steam cavitation micro-bursts in tracheids
        # Occurs primarily when fuel temp is 160°C - 380°C and residual moisture > 2%
        crackle_hz = 0.0
        if 150.0 <= self.fuel_temp_c <= 420.0 and self.fmc_pct >= 2.0:
            temp_window = math.exp(-((self.fuel_temp_c - 270.0) ** 2) / (2.0 * (55.0 ** 2)))
            moisture_factor = min(1.5, self.fmc_pct / 10.0)
            crackle_hz = 14.5 * temp_window * moisture_factor * (q_in_kw / 5.0)

        return CombustionState(
            timestamp_s=timestamp_s,
            source_id=self.source_id,
            position_xyz=self.pos,
            fuel_temperature_c=float(self.fuel_temp_c),
            fuel_moisture_content_pct=float(self.fmc_pct),
            heat_flux_kw_m2=float(heat_flux_kw_m2),
            pyrolysis_rate_kg_s=float(total_pyrolysis_kg_s),
            co_emission_rate_mg_s=float(co_mg_s),
            voc_emission_rate_mg_s=float(voc_mg_s),
            pm1_0_emission_rate_mg_s=float(pm1_0_mg_s),
            pm2_5_emission_rate_mg_s=float(pm2_5_mg_s),
            pm4_0_emission_rate_mg_s=float(pm4_0_mg_s),
            pm10_0_emission_rate_mg_s=float(pm10_0_mg_s),
            acoustic_crackle_rate_hz=float(crackle_hz),
            active=True,
        )


class GaussianPlumeDispersionModel:
    """3D Gaussian advection-diffusion atmospheric dispersion for gas and particulate transport."""

    @staticmethod
    def calculate_concentration_at_node(
        node_pos_xyz: Tuple[float, float, float],
        combustion: CombustionState,
        atmosphere: AtmosphericState,
    ) -> Dict[str, float]:
        """Compute local gas and aerosol concentrations at node coordinate."""
        if not combustion.active:
            return {
                "co_ppm": 0.0,
                "voc_ppm": 0.0,
                "pm1_0_ug_m3": 0.0,
                "pm2_5_ug_m3": 0.0,
                "pm4_0_ug_m3": 0.0,
                "pm10_0_ug_m3": 0.0,
            }

        # Vector from source to sensor node
        dx = node_pos_xyz[0] - combustion.position_xyz[0]
        dy = node_pos_xyz[1] - combustion.position_xyz[1]
        dz = node_pos_xyz[2] - combustion.position_xyz[2]

        wind_speed = max(0.2, atmosphere.wind_speed_m_s)
        wind_u = atmosphere.wind_u
        wind_v = atmosphere.wind_v

        # Along-wind unit vector and cross-wind unit vector
        norm_u = math.sqrt(wind_u * wind_u + wind_v * wind_v)
        u_hat_x = wind_u / norm_u
        u_hat_y = wind_v / norm_u

        # Rotate to along-wind coordinate x_down and cross-wind coordinate y_cross
        x_down = dx * u_hat_x + dy * u_hat_y
        y_cross = -dx * u_hat_y + dy * u_hat_x

        # Plume only propagates downwind (with small upwind back-diffusion for close distances < 2m)
        if x_down < -1.5:
            return {
                "co_ppm": 0.0,
                "voc_ppm": 0.0,
                "pm1_0_ug_m3": 0.0,
                "pm2_5_ug_m3": 0.0,
                "pm4_0_ug_m3": 0.0,
                "pm10_0_ug_m3": 0.0,
            }

        eff_x = max(1.0, x_down + 1.5)

        # Pasquill-Gifford dispersion parameters for forested canopy (Class C/D)
        sigma_y = 0.28 * eff_x * ((1.0 + 0.00015 * eff_x) ** -0.5)
        sigma_z = 0.22 * eff_x

        # Ground reflection term
        z_source = combustion.position_xyz[2]
        z_node = node_pos_xyz[2]
        z_term = math.exp(-((z_node - z_source) ** 2) / (2.0 * sigma_z * sigma_z)) + \
                 math.exp(-((z_node + z_source) ** 2) / (2.0 * sigma_z * sigma_z))

        # Crosswind Gaussian distribution
        y_term = math.exp(-(y_cross ** 2) / (2.0 * sigma_y * sigma_y))

        # Dilution factor Chi / Q (s/m3)
        dilution = (1.0 / (2.0 * math.pi * wind_speed * sigma_y * sigma_z)) * y_term * z_term

        # Convert mg/s emission rates to mg/m3 at sensor node
        # 1 mg/m3 = 1000 ug/m3
        co_mg_m3 = combustion.co_emission_rate_mg_s * dilution
        voc_mg_m3 = combustion.voc_emission_rate_mg_s * dilution
        pm1_ug_m3 = (combustion.pm1_0_emission_rate_mg_s * dilution) * 1000.0
        pm25_ug_m3 = (combustion.pm2_5_emission_rate_mg_s * dilution) * 1000.0
        pm4_ug_m3 = (combustion.pm4_0_emission_rate_mg_s * dilution) * 1000.0
        pm10_ug_m3 = (combustion.pm10_0_emission_rate_mg_s * dilution) * 1000.0

        # Molecular weight conversion: CO (28.01 g/mol) at standard temp/pressure
        # ppm = (mg/m3 * 24.45) / MW
        co_ppm = (co_mg_m3 * 24.45) / 28.01
        # VOC surrogate: Furfural/Levoglucosan average MW ~ 96.0 g/mol
        voc_ppm = (voc_mg_m3 * 24.45) / 96.0

        return {
            "co_ppm": float(co_ppm),
            "voc_ppm": float(voc_ppm),
            "pm1_0_ug_m3": float(pm1_ug_m3),
            "pm2_5_ug_m3": float(pm25_ug_m3),
            "pm4_0_ug_m3": float(pm4_ug_m3),
            "pm10_0_ug_m3": float(pm10_ug_m3),
        }


class ThermalRadianceMatrixModel:
    """Melexis MLX90640 32x24 uncooled far-IR thermopile matrix synthesis and spatial gradient tracker."""

    def __init__(
        self,
        fov_horizontal_deg: float = 55.0,
        fov_vertical_deg: float = 35.0,
        netd_noise_k: float = 0.10,
        seed: int = 101,
    ):
        self.cols = 32
        self.rows = 24
        self.fov_h_rad = math.radians(fov_horizontal_deg)
        self.fov_v_rad = math.radians(fov_vertical_deg)
        self.netd = netd_noise_k
        self.rng = np.random.RandomState(seed)

        # 2D Sobel Kernels for spatial differential tracking
        self.sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
        self.sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32) / 8.0

        # History tracking for centroid velocity calculation
        self.prev_centroid: Optional[Tuple[float, float]] = None
        self.prev_timestamp: Optional[float] = None

    def render_matrix(
        self,
        node_pos_xyz: Tuple[float, float, float],
        combustion: CombustionState,
        atmosphere: AtmosphericState,
    ) -> ThermalMatrixResult:
        """Render 32x24 thermal image and compute spatial Sobel gradients and centroid motion."""
        z_height = max(1.0, node_pos_xyz[2])
        footprint_w = 2.0 * z_height * math.tan(self.fov_h_rad / 2.0)
        footprint_h = 2.0 * z_height * math.tan(self.fov_v_rad / 2.0)

        # Baseline ground ambient temperature + NETD sensor noise
        base_temp = atmosphere.temperature_c
        matrix = np.full((self.rows, self.cols), base_temp, dtype=np.float32)

        # Add NETD white noise (NETD = 0.1K)
        noise = self.rng.normal(0.0, self.netd, (self.rows, self.cols)).astype(np.float32)
        matrix += noise

        # If combustion is active, project thermal hotspot onto pixel grid
        if combustion.active and combustion.fuel_temperature_c > base_temp + 5.0:
            # Source coordinates relative to node ground nadir
            rel_x = combustion.position_xyz[0] - node_pos_xyz[0]
            rel_y = combustion.position_xyz[1] - node_pos_xyz[1]

            # Thermal convection drift in wind direction: plume shift
            plume_shift_x = 0.6 * atmosphere.wind_u
            plume_shift_y = 0.6 * atmosphere.wind_v

            combustion_delta_t = combustion.fuel_temperature_c - base_temp

            for r in range(self.rows):
                # Normalized pixel coordinate (-0.5 to +0.5)
                py = (r - 11.5) / 24.0
                ground_y = py * footprint_h

                for c in range(self.cols):
                    px = (c - 15.5) / 32.0
                    ground_x = px * footprint_w

                    # Distance from pixel ground footprint to fire core
                    d_core_sq = (ground_x - rel_x) ** 2 + (ground_y - rel_y) ** 2
                    # Distance to convective warm plume
                    d_plume_sq = (ground_x - (rel_x + plume_shift_x)) ** 2 + (ground_y - (rel_y + plume_shift_y)) ** 2

                    # Radiative spot (radius ~ 0.8m)
                    core_rad = combustion_delta_t * math.exp(-d_core_sq / (2.0 * (0.8 ** 2)))
                    # Convective warm air smear (radius ~ 2.0m)
                    plume_rad = (combustion_delta_t * 0.35) * math.exp(-d_plume_sq / (2.0 * (2.2 ** 2)))

                    matrix[r, c] += float(max(core_rad, plume_rad))

        # Spatial Statistics
        median_amb = float(np.median(matrix))
        max_temp = float(np.max(matrix))
        min_temp = float(np.min(matrix))
        delta_max = max_temp - median_amb

        # 2D Sobel spatial gradient computation
        grad_x = convolve2d(matrix, self.sobel_x, mode="same", boundary="symm")
        grad_y = convolve2d(matrix, self.sobel_y, mode="same", boundary="symm")
        grad_mag = np.sqrt(grad_x * grad_x + grad_y * grad_y)
        max_gradient = float(np.max(grad_mag))

        # Hotspot extraction: delta > 12.5°C and grad > 4.0°C/px (per Section 3 spec)
        hotspot_mask = (matrix - median_amb > 12.5) & (grad_mag > 4.0)
        hotspot_count = int(np.sum(hotspot_mask))

        centroid_xy: Optional[Tuple[float, float]] = None
        plume_vel_mm_s = 0.0

        if hotspot_count > 0:
            # Center of mass of thermal anomaly
            weights = np.maximum(0.0, matrix - median_amb) * hotspot_mask
            sum_w = np.sum(weights)
            if sum_w > 1e-4:
                y_indices, x_indices = np.indices((self.rows, self.cols))
                cx = float(np.sum(x_indices * weights) / sum_w)
                cy = float(np.sum(y_indices * weights) / sum_w)
                centroid_xy = (cx, cy)

                # Centroid velocity calculation
                if self.prev_centroid is not None and self.prev_timestamp is not None:
                    dt = max(0.1, atmosphere.timestamp_s - self.prev_timestamp)
                    dcx = cx - self.prev_centroid[0]
                    dcy = cy - self.prev_centroid[1]
                    pixel_dist = math.sqrt(dcx * dcx + dcy * dcy)
                    # Convert pixel distance to millimeters on ground
                    mm_per_pixel = (footprint_w / 32.0) * 1000.0
                    plume_vel_mm_s = float((pixel_dist * mm_per_pixel) / dt)

                self.prev_centroid = centroid_xy
                self.prev_timestamp = atmosphere.timestamp_s

        return ThermalMatrixResult(
            raw_matrix=matrix,
            ambient_median_c=median_amb,
            max_temperature_c=max_temp,
            min_temperature_c=min_temp,
            delta_max_c=delta_max,
            sobel_gradient_max=max_gradient,
            hotspot_pixels=hotspot_count,
            centroid_xy=centroid_xy,
            plume_velocity_mm_s=plume_vel_mm_s,
        )


class AcousticCavitationModel:
    """Knowles INMP441 MEMS microphone acoustic cellular wall rupture crackle generator."""

    def __init__(self, sample_rate_hz: int = 16000, buffer_samples: int = 512, seed: int = 202):
        self.sample_rate = sample_rate_hz
        self.buffer_samples = buffer_samples
        self.rng = np.random.RandomState(seed)

    def evaluate(
        self,
        combustion: CombustionState,
        atmosphere: AtmosphericState,
        distance_to_source_m: float,
    ) -> AcousticSignatureResult:
        """Evaluate acoustic crackle event rate, spectral energy ratio, and confidence."""
        eff_dist = max(1.0, distance_to_source_m)

        # Sound attenuation in air: geometric 1/r plus absorption in forest ~ 0.05 dB/m
        geometric_atten = 1.0 / eff_dist
        absorption = math.exp(-0.02 * eff_dist)
        attenuation = geometric_atten * absorption

        # Source crackle rate attenuated by distance
        received_crackle_rate = combustion.acoustic_crackle_rate_hz * attenuation if combustion.active else 0.0

        # Background acoustic environment:
        # Wind noise concentrates in low frequencies (< 500Hz)
        wind_noise_power = 0.1 + 0.05 * (atmosphere.wind_speed_m_s ** 2)

        # Pyrolysis crackle power concentrates in 800Hz - 4500Hz band
        crackle_power = received_crackle_rate * 0.85

        total_power = wind_noise_power + crackle_power + 0.05  # noise floor
        spectral_ratio = crackle_power / total_power

        # Pyrolysis confidence score based on crackle rate and spectral ratio
        conf = 1.0 / (1.0 + math.exp(-1.5 * (received_crackle_rate - 3.5))) if received_crackle_rate > 0.5 else 0.02

        peak_freq = 2850.0 if received_crackle_rate > 2.0 else 180.0

        return AcousticSignatureResult(
            crackle_event_rate_hz=float(received_crackle_rate),
            spectral_energy_ratio=float(np.clip(spectral_ratio, 0.01, 0.99)),
            peak_frequency_hz=float(peak_freq),
            pyrolysis_confidence=float(np.clip(conf, 0.0, 1.0)),
        )


class ForestPhysicsEngine:
    """Unified cyber-physical simulation engine coordinating atmosphere, kinetics, plume dispersion, IR, and acoustics."""

    def __init__(
        self,
        base_temperature_c: float = 22.0,
        base_humidity_pct: float = 58.0,
        base_wind_speed_m_s: float = 2.5,
        base_wind_dir_deg: float = 45.0,
        elevation_m: float = 500.0,
        seed: int = 42,
    ):
        self.atmosphere_model = CanopyMicroclimateModel(
            base_temperature_c=base_temperature_c,
            base_humidity_pct=base_humidity_pct,
            base_wind_speed_m_s=base_wind_speed_m_s,
            base_wind_dir_deg=base_wind_dir_deg,
            elevation_m=elevation_m,
            seed=seed,
        )
        self.thermal_model = ThermalRadianceMatrixModel(seed=seed + 1)
        self.acoustic_model = AcousticCavitationModel(seed=seed + 2)
        self.combustion_sources: Dict[str, PyrolysisKineticsModel] = {}
        self.latest_combustion_states: Dict[str, CombustionState] = {}
        self.current_time_s = 0.0

    def add_combustion_source(
        self,
        source_id: str,
        position_xyz: Tuple[float, float, float],
        initial_fuel_temp_c: float = 22.0,
        initial_fuel_moisture_pct: float = 12.0,
        fuel_mass_kg: float = 15.0,
    ) -> PyrolysisKineticsModel:
        """Register a physical combustion/pyrolysis source."""
        source = PyrolysisKineticsModel(
            source_id=source_id,
            position_xyz=position_xyz,
            initial_fuel_temp_c=initial_fuel_temp_c,
            initial_fuel_moisture_pct=initial_fuel_moisture_pct,
            fuel_mass_kg=fuel_mass_kg,
        )
        self.combustion_sources[source_id] = source
        return source

    def step(
        self,
        dt_s: float,
        heat_fluxes: Optional[Dict[str, float]] = None,
    ) -> Tuple[AtmosphericState, Dict[str, CombustionState]]:
        """Advance the physics simulation forward by dt_s seconds."""
        self.current_time_s += dt_s
        heat_fluxes = heat_fluxes or {}

        # 1. Update canopy atmospheric conditions
        atm = self.atmosphere_model.compute_state(self.current_time_s)

        # 2. Step all active combustion kinetics
        states = {}
        for s_id, source in self.combustion_sources.items():
            flux = heat_fluxes.get(s_id, 0.0)
            state = source.step(
                dt_s=dt_s,
                heat_flux_kw_m2=flux,
                ambient_temp_c=atm.temperature_c,
                timestamp_s=self.current_time_s,
            )
            states[s_id] = state

        self.latest_combustion_states = states
        return atm, states

    def sample_environment_at_node(
        self,
        node_pos_xyz: Tuple[float, float, float],
        active_source_id: Optional[str] = None,
    ) -> Tuple[AtmosphericState, Dict[str, float], ThermalMatrixResult, AcousticSignatureResult]:
        """Compute the combined physical environment as sensed by a hardware node at node_pos_xyz."""
        atm = self.atmosphere_model.compute_state(self.current_time_s, z_height_m=node_pos_xyz[2])

        # Aggregate gas and PM dispersion across all sources (or the specified active source)
        total_dispersion = {
            "co_ppm": 0.0,
            "voc_ppm": 0.0,
            "pm1_0_ug_m3": 0.0,
            "pm2_5_ug_m3": 0.0,
            "pm4_0_ug_m3": 0.0,
            "pm10_0_ug_m3": 0.0,
        }

        # Baseline clean canopy background air
        clean_pm2_5 = 5.5 + 1.5 * math.sin(self.current_time_s / 3600.0)
        clean_pm10 = 9.8 + 2.0 * math.sin(self.current_time_s / 3600.0)
        total_dispersion["pm1_0_ug_m3"] += clean_pm2_5 * 0.70
        total_dispersion["pm2_5_ug_m3"] += clean_pm2_5
        total_dispersion["pm4_0_ug_m3"] += clean_pm2_5 * 1.05
        total_dispersion["pm10_0_ug_m3"] += clean_pm10

        target_sources = (
            [self.latest_combustion_states[active_source_id]]
            if active_source_id and active_source_id in self.latest_combustion_states
            else list(self.latest_combustion_states.values())
        )

        dominant_combustion = None
        min_distance = float("inf")

        for c_state in target_sources:
            if not c_state.active:
                continue

            disp = GaussianPlumeDispersionModel.calculate_concentration_at_node(
                node_pos_xyz=node_pos_xyz,
                combustion=c_state,
                atmosphere=atm,
            )
            for k in total_dispersion:
                total_dispersion[k] += disp[k]

            dx = node_pos_xyz[0] - c_state.position_xyz[0]
            dy = node_pos_xyz[1] - c_state.position_xyz[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < min_distance:
                min_distance = dist
                dominant_combustion = c_state

        # If no active combustion source, synthesize inert baseline source
        if dominant_combustion is None:
            dominant_combustion = CombustionState(
                timestamp_s=self.current_time_s,
                source_id="inert",
                position_xyz=(0.0, 0.0, 0.0),
                fuel_temperature_c=atm.temperature_c,
                fuel_moisture_content_pct=15.0,
                heat_flux_kw_m2=0.0,
                pyrolysis_rate_kg_s=0.0,
                co_emission_rate_mg_s=0.0,
                voc_emission_rate_mg_s=0.0,
                pm1_0_emission_rate_mg_s=0.0,
                pm2_5_emission_rate_mg_s=0.0,
                pm4_0_emission_rate_mg_s=0.0,
                pm10_0_emission_rate_mg_s=0.0,
                acoustic_crackle_rate_hz=0.0,
                active=False,
            )
            min_distance = 100.0

        # Thermal IR matrix evaluation
        thermal_res = self.thermal_model.render_matrix(
            node_pos_xyz=node_pos_xyz,
            combustion=dominant_combustion,
            atmosphere=atm,
        )

        # Acoustic INMP441 evaluation
        acoustic_res = self.acoustic_model.evaluate(
            combustion=dominant_combustion,
            atmosphere=atm,
            distance_to_source_m=min_distance,
        )

        return atm, total_dispersion, thermal_res, acoustic_res


class PhysicsEngine:
    """Convenience and backward-compatible simulation interface.

    Provides thermal matrix generation, 2D Sobel gradient computation,
    and Rothermel wildfire spread behavior modeling.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
        self.sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
        self.sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32) / 8.0

    def generate_thermal_matrix(
        self,
        hotspot_center: Tuple[int, int] = (16, 12),
        max_temp: float = 25.0,
        ambient_temp: float = 21.0,
        radius: float = 1.0,
        plume_drift: Tuple[float, float] = (0.0, 0.0),
        noise_std: float = 0.2,
    ) -> np.ndarray:
        """Generate MLX90640 32x24 thermal image with hotspot, convective plume, and noise."""
        rows, cols = 24, 32
        matrix = np.full((rows, cols), ambient_temp, dtype=np.float32)

        # Add sensor NETD noise
        noise = self.rng.normal(0.0, noise_std, (rows, cols)).astype(np.float32)
        matrix += noise

        delta_t = max_temp - ambient_temp
        if delta_t > 0.5:
            cx, cy = hotspot_center
            drift_x, drift_y = plume_drift

            for r in range(rows):
                for c in range(cols):
                    # Core distance
                    d_core_sq = (c - cx) ** 2 + (r - cy) ** 2
                    # Plume distance
                    d_plume_sq = (c - (cx + drift_x)) ** 2 + (r - (cy + drift_y)) ** 2

                    rad_core = delta_t * math.exp(-d_core_sq / (2.0 * max(0.5, radius) ** 2))
                    rad_plume = (delta_t * 0.4) * math.exp(-d_plume_sq / (2.0 * max(1.0, radius * 2.2) ** 2))
                    matrix[r, c] += float(max(rad_core, rad_plume))

        return matrix

    def compute_spatial_gradient(
        self,
        thermal_matrix: np.ndarray,
    ) -> Tuple[float, Tuple[float, float]]:
        """Compute maximum Sobel gradient magnitude and normalized vector."""
        grad_x = convolve2d(thermal_matrix, self.sobel_x, mode="same", boundary="symm")
        grad_y = convolve2d(thermal_matrix, self.sobel_y, mode="same", boundary="symm")
        grad_mag = np.sqrt(grad_x * grad_x + grad_y * grad_y)

        max_mag = float(np.max(grad_mag))
        max_idx = np.unravel_index(np.argmax(grad_mag), grad_mag.shape)

        gx_at_max = float(grad_x[max_idx])
        gy_at_max = float(grad_y[max_idx])
        norm = math.sqrt(gx_at_max * gx_at_max + gy_at_max * gy_at_max) + 1e-6
        vec = (gx_at_max / norm, gy_at_max / norm)

        return max_mag, vec

    def calculate_rothermel_spread(
        self,
        fti_score: float,
        wind_speed_ms: float,
        wind_dir_deg: float,
        slope_deg: float = 14.0,
    ) -> Dict[str, Any]:
        """Calculate Rothermel surface fire spread rate, reaction intensity, and evacuation vector."""
        if fti_score < 0.60:
            # Below advisory threshold: minimal or zero spread
            spread_m_s = 0.0
            spread_m_min = 0.0
            reaction_intensity = 0.0
            flame_length_m = 0.0
            bearing = 0.0
        else:
            # Active combustion / wildfire condition
            # Rothermel parameters:
            # Reaction intensity IR (kW/m2) scales with threat index
            reaction_intensity = 450.0 + (fti_score - 0.60) * 2200.0

            # Wind multiplier Phi_w = C * (3.281 * u)^B
            u_fps = wind_speed_ms * 3.28084
            phi_w = 0.08 * (u_fps ** 1.35)

            # Slope multiplier Phi_s = 5.275 * tan(slope)^2
            tan_slope = math.tan(math.radians(slope_deg))
            phi_s = 5.275 * (tan_slope ** 2)

            # Propagating flux ratio xi ~ 0.04
            # Heat sink: rho_b * epsilon * Q_ig ~ 4500 kJ/m3
            xi = 0.042
            heat_sink = 4200.0  # kJ/m3

            # Rate of spread (m/s)
            spread_m_s = (reaction_intensity * xi * (1.0 + phi_w + phi_s)) / heat_sink
            spread_m_min = spread_m_s * 60.0

            # Flame length Byram formula: L = 0.0775 * (IB)^0.46 (meters)
            byram_intensity = reaction_intensity * spread_m_s  # kW/m
            flame_length_m = 0.0775 * (byram_intensity ** 0.46) if byram_intensity > 0 else 0.0

            # Fire propagation heading is downwind + upslope vector
            bearing = (wind_dir_deg + 180.0) % 360.0  # Towards downwind

        # Evacuation bearing is perpendicular or opposite to fire spread
        evacuation_bearing = (bearing + 180.0) % 360.0

        return {
            "spread_rate_m_s": round(spread_m_s, 4),
            "spread_rate_m_min": round(spread_m_min, 2),
            "reaction_intensity_kw_m2": round(reaction_intensity, 1),
            "flame_length_m": round(flame_length_m, 2),
            "propagation_bearing_deg": round(bearing, 1),
            "evacuation_bearing_deg": round(evacuation_bearing, 1),
            "active": fti_score >= 0.60,
        }

