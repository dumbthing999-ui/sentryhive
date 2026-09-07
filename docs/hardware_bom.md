# SentryHive: Edge Wildfire & Microclimate Multi-Modal Early Warning Network
## Hardware Bill of Materials (BOM), Pinout & Electrical Specification

---

## 1. Executive Hardware Overview

The SentryHive Edge Sensor Node is an ultra-reliable, solar-harvesting cyber-physical appliance engineered for long-term deployment (>5 years maintenance-free) in harsh wildland and wildland-urban interface (WUI) environments. The hardware integrates multi-modal atmospheric, optical, acoustic, and radiative transducers with edge machine learning compute and sub-GHz wireless telemetry, protected by an IP67-rated UV-stabilized enclosure.

### Primary Hardware Key Performance Indicators (KPIs)
* **Nominal System Rail:** $3.30\text{ V DC} \pm 1\%$ via ultra-low-quiescent buck regulator ($I_Q = 60\text{ nA}$).
* **Battery Chemistry:** Lithium Iron Phosphate ($\text{LiFePO}_4$), $3.2\text{ V}$ nominal, $3400\text{ mAh}$ capacity ($10.88\text{ Wh}$), non-combustible up to $+150^\circ\text{C}$.
* **Solar Harvesting:** $5.0\text{ W}$ Monocrystalline ETFE panel with integrated Maximum Power Point Tracking (MPPT) buck-boost charger ($96.5\%$ peak efficiency).
* **Average Power Consumption (Nominal Monitoring Tier 0):** $18.4\text{ mW}$ ($5.58\text{ mA}$ average current @ $3.3\text{ V}$).
* **Battery Autonomy (Zero Solar Insolation / Smoke Eclipse):** $> 25.4\text{ days}$ continuous operation under Tier 0 monitoring; $> 90\text{ days}$ under Tier 2 low-power triage.
* **Operating Temperature Range:** $-20^\circ\text{C}$ to $+70^\circ\text{C}$.
* **RF Link Budget:** $+159\text{ dB}$ ($+22\text{ dBm}$ TX power, $-137\text{ dBm}$ sensitivity @ SF10, $125\text{ kHz}$).

```
+--------------------------------------------------------------------------------------------------+
|                                    ELECTRICAL SYSTEM BUS ARCHITECTURE                            |
|                                                                                                  |
|   [ 5W Solar Panel ] ---> [ TI BQ25798 MPPT Charger ] <---> [ 3400mAh LiFePO4 Battery + BQ2970 ]  |
|                                     |                                                            |
|                                     v (System Battery Rail: 2.8V - 3.65V)                        |
|                         [ TI TPS62840 Low-Iq Buck ]                                              |
|                                     |                                                            |
|                                     +-----------------+-------------------+                      |
|                                     | 3.3V Digital    | 3.3V Analog       | 5.0V Boost (SPS30)   |
|                                     v                 v                   v                      |
|                           +-------------------+ +---------------+ +------------------+           |
|                           | ESP32-S3 MCU      | | INMP441 MEMS  | | Sensirion SPS30  |           |
|                           | SX1262 LoRa Radio | | BME688 MOX    | | Fan & Laser Rail |           |
|                           | MLX90640 Array    | | Transducers   | |                  |           |
|                           +-------------------+ +---------------+ +------------------+           |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Complete Engineering Bill of Materials (BOM)

The following component schedule provides exact manufacturer part numbers (MPNs), vendor reference numbers, package footprints, and unit costs at 1x prototype, 100x pilot, and 1,000x production scales.

### 2.1 Core Compute, Processing & Clocks
| Item | RefDes | Description | Mfr | MPN | Package | Supplier / SKU | Qty | Unit (1x) | Ext (1x) | 100x | 1000x |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1.01 | U1 | MCU Dual-Core Xtensa LX7 240MHz, 16MB Flash, 8MB PSRAM | Espressif | ESP32-S3-WROOM-1-N16R8 | SMD Module 41-pin | DigiKey / 1965-ESP32-S3-WROOM-1-N16R8CT-ND | 1 | $4.20 | $4.20 | $3.45 | $2.95 |
| 1.02 | Y1 | Crystal Oscillator 32.768 kHz $\pm 20\text{ ppm}$ 9pF | Abracon | ABS07-32.768KHZ-T | SMD 3.2x1.5mm | Mouser / 815-ABS07-32.768KHZT | 1 | $0.65 | $0.65 | $0.42 | $0.28 |
| 1.03 | C1, C2 | Ceramic Cap 9pF 50V C0G 1% | Murata | GRM1555C1H9R0BA01D | 0402 | DigiKey / 490-GRM1555C1H9R0BA01DCT-ND | 2 | $0.10 | $0.20 | $0.03 | $0.015 |
| 1.04 | C3, C4 | Decoupling Cap 10µF 10V X7R 10% | TDK | C1608X7R1A106K080AC | 0603 | DigiKey / 445-7524-1-ND | 2 | $0.18 | $0.36 | $0.08 | $0.045 |
| 1.05 | C5..C9 | Bypass Cap 0.1µF 25V X7R 10% | Murata | GRM155R71E104KE14D | 0402 | Mouser / 81-GRM155R71E104KE14D | 5 | $0.08 | $0.40 | $0.02 | $0.009 |
| 1.06 | R1 | Pullup Resistor 10k$\Omega$ 1/16W 1% | Yageo | RC0402FR-0710KL | 0402 | DigiKey / 311-10.0KLRCT-ND | 1 | $0.05 | $0.05 | $0.01 | $0.004 |
| 1.07 | SW1, SW2| Tactile Switch SPST-NO 50mA 12V (Boot / Reset) | C&K | KXT331LHS | SMD 3.0x2.0mm | DigiKey / CKN10793CT-ND | 2 | $0.45 | $0.90 | $0.28 | $0.18 |

### 2.2 Multi-Modal Sensor Array
| Item | RefDes | Description | Mfr | MPN | Package | Supplier / SKU | Qty | Unit (1x) | Ext (1x) | 100x | 1000x |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2.01 | U2 | Gas, Pressure, Temp & Humidity Matrix MOX Sensor | Bosch Sensortec | BME688 | 8-pin LGA 3.0x3.0x0.93mm | Mouser / 262-BME688 | 1 | $9.80 | $9.80 | $7.85 | $6.20 |
| 2.02 | M1 | Optical Laser Scattering Particulate Matter Sensor (PM1.0/2.5/4/10) | Sensirion | SPS30 | Module 41x41x12mm | DigiKey / 1649-1087-ND | 1 | $36.50 | $36.50 | $29.80 | $24.50 |
| 2.03 | U3 | $32 \times 24$ Far-Infrared Thermopile Focal Plane Array (55°x35° FOV) | Melexis | MLX90640ESF-BAB-000-TU | TO-39 4-lead | DigiKey / MLX90640ESF-BAB-000-TU-ND | 1 | $48.20 | $48.20 | $39.50 | $33.80 |
| 2.04 | U4 | High-SNR Omnidirectional I2S Digital MEMS Microphone | Knowles / TDK | INMP441ACEZ-R7 | 14-pin LGA 4.72x3.76mm | DigiKey / 1864-INMP441ACEZ-R7CT-ND | 1 | $2.40 | $2.40 | $1.75 | $1.25 |
| 2.05 | R2, R3 | Pullup Resistor 4.7k$\Omega$ 1/16W 1% (I2C Bus 0) | Yageo | RC0402FR-074K7L | 0402 | DigiKey / 311-4.70KLRCT-ND | 2 | $0.05 | $0.10 | $0.01 | $0.004 |
| 2.06 | R4, R5 | Pullup Resistor 2.2k$\Omega$ 1/16W 1% (I2C Bus 1 Fast+) | Yageo | RC0402FR-072K2L | 0402 | DigiKey / 311-2.20KLRCT-ND | 2 | $0.05 | $0.10 | $0.01 | $0.004 |
| 2.07 | U5 | Synchronous Boost Converter 3.3V to 5.0V (SPS30 Fan Rail) | Texas Instruments | TPS61099YFFR | 6-ball DSBGA 1.2x0.8mm | DigiKey / 296-46985-1-ND | 1 | $0.92 | $0.92 | $0.62 | $0.44 |
| 2.08 | L1 | Inductor 2.2µH 1.8A Shielded | Murata | DFE201610E-2R2M=P2 | 0806 (2016 Metric) | Mouser / 81-DFE201610E-2R2MP2 | 1 | $0.48 | $0.48 | $0.31 | $0.21 |

### 2.3 Sub-GHz Long-Range Wireless & RF
| Item | RefDes | Description | Mfr | MPN | Package | Supplier / SKU | Qty | Unit (1x) | Ext (1x) | 100x | 1000x |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 3.01 | U6 | LoRa Sub-GHz +22dBm Transceiver Module (SX1262 TCXO) | Semtech / Ebyte | E22-900M22S | SMD 14x20mm (Castellated) | LCSC / C962770 | 1 | $6.80 | $6.80 | $5.10 | $4.20 |
| 3.02 | J1 | RF Coaxial Connector U.FL / IPEX1 Receptacle 50$\Omega$ | Hirose | U.FL-R-SMT-1(10) | SMD 3.0x3.0mm | DigiKey / H9161CT-ND | 1 | $0.62 | $0.62 | $0.41 | $0.27 |
| 3.03 | ANT1 | 915MHz External IP67 Omnidirectional Whip Antenna + SMA Pigtail | Linx / TE | ANT-916-CW-HWR-SMA | Waterproof Dipole 1/2 Wave | DigiKey / ANT-916-CW-HWR-SMA-ND | 1 | $9.10 | $9.10 | $7.20 | $5.80 |
| 3.04 | W1 | Coaxial Pigtail U.FL to Female SMA Bulkhead with O-Ring (150mm RG-178) | Taoglas | CAB.011 | Cable Assembly | Mouser / 960-CAB.011 | 1 | $3.25 | $3.25 | $2.45 | $1.90 |
| 3.05 | FL1 | SAW Bandpass Filter 915 MHz (80MHz BW) 50$\Omega$ | Tai-Saw | B39921B4301F210 | SMD 1.4x1.1mm | Mouser / 962-B39921B4301F210 | 1 | $1.15 | $1.15 | $0.82 | $0.58 |

### 2.4 Power Management, MPPT & Battery Storage
| Item | RefDes | Description | Mfr | MPN | Package | Supplier / SKU | Qty | Unit (1x) | Ext (1x) | 100x | 1000x |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 4.01 | U7 | Synchronous Buck-Boost MPPT Battery Charger NVDC | Texas Instruments | BQ25798RQMR | 29-pin QFN 4.0x4.0mm | DigiKey / 296-BQ25798RQMRCT-ND | 1 | $4.75 | $4.75 | $3.65 | $2.85 |
| 4.02 | U8 | Synchronous Step-Down Buck Converter 3.3V $I_Q=60\text{nA}$ | Texas Instruments | TPS62840DLYR | 6-pin WSON 1.5x1.5mm | DigiKey / 296-TPS62840DLYRCT-ND | 1 | $1.35 | $1.35 | $0.98 | $0.72 |
| 4.03 | U9 | Single-Cell LiFePO4 Precision Battery Protection IC | Texas Instruments | BQ29704DSER | 6-pin WSON 1.5x1.5mm | DigiKey / 296-48412-1-ND | 1 | $0.55 | $0.55 | $0.38 | $0.26 |
| 4.04 | Q1, Q2 | Dual N-Channel Power MOSFET 20V 6A (Battery Protection) | Alpha & Omega | AON2802 | 6-pin DFN 2.0x2.0mm | Mouser / 426-AON2802 | 1 | $0.42 | $0.42 | $0.26 | $0.16 |
| 4.05 | L2 | Inductor 1.5µH 4.5A Shielded Power Choke (BQ25798) | Coilcraft | XFL4020-152MEC | SMD 4.0x4.0mm | Mouser / 994-XFL4020-152MEC | 1 | $1.20 | $1.20 | $0.85 | $0.62 |
| 4.06 | L3 | Inductor 1.0µH 1.8A Low DCR (TPS62840) | Murata | DFE201610E-1R0M=P2 | 0806 (2016 Metric) | Mouser / 81-DFE201610E-1R0MP2 | 1 | $0.46 | $0.46 | $0.30 | $0.20 |
| 4.07 | BT1 | 18650 LiFePO4 Battery Cell 3.2V 3400mAh High-Cycle | Power Sonic / Melasta | IFR18650-3400 | Cylindrical 18650 | Melasta / IFR18650-3400 | 1 | $6.50 | $6.50 | $4.80 | $3.90 |
| 4.08 | BH1 | Keystone 18650 Battery Holder Gold-Plated SMT Clips | Keystone | 1042 | SMT Bracket | DigiKey / 36-1042-ND | 1 | $1.85 | $1.85 | $1.32 | $0.98 |
| 4.09 | PV1 | 5W 6V Monocrystalline ETFE Solar Panel IP67 with JST-PH | Voltaic Systems / Customized | P105-5W-6V | Encapsulated 180x150mm | Direct / P105-5W | 1 | $14.50 | $14.50 | $10.50 | $8.20 |
| 4.10 | D1 | TVS Diode Bidirectional 6.0V 600W (Solar Surge Clamp) | Littelfuse | SMBJ6.0CA | DO-214AA (SMB) | DigiKey / SMBJ6.0CALFCT-ND | 1 | $0.42 | $0.42 | $0.24 | $0.15 |

### 2.5 Autonomous Actuation & Life-Safety Alarms
| Item | RefDes | Description | Mfr | MPN | Package | Supplier / SKU | Qty | Unit (1x) | Ext (1x) | 100x | 1000x |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 5.01 | BZ1 | High-Output 110dB Continuous/Pulse Piezo Siren Transducer | Mallory Sonalert | SC628P | Panel Mount 30mm | DigiKey / 458-1002-ND | 1 | $8.80 | $8.80 | $6.90 | $5.40 |
| 5.02 | LED1 | High-Flux Amber Power Strobe LED (590nm, 120 lm @ 350mA) | Cree LED | XPEBAM-L1-0000-00A01 | SMD 3.45x3.45mm | Mouser / 941-XPEBAML100A01 | 1 | $1.65 | $1.65 | $1.15 | $0.85 |
| 5.03 | Q3 | N-Channel Power MOSFET 30V 5.7A $R_{DS(on)}=28\text{m}\Omega$ | Alpha & Omega | AO3400A | SOT-23-3 | DigiKey / 785-1001-1-ND | 1 | $0.22 | $0.22 | $0.09 | $0.045 |
| 5.04 | Q4 | N-Channel Power MOSFET 30V 5.7A (LED Strobe Driver) | Alpha & Omega | AO3400A | SOT-23-3 | DigiKey / 785-1001-1-ND | 1 | $0.22 | $0.22 | $0.09 | $0.045 |
| 5.05 | D2 | Fast Recovery Rectifier Diode 40V 1A Schottky (Flyback) | ON Semi | MBR140T3G | SOD-123 | DigiKey / MBR140T3GOSCT-ND | 1 | $0.28 | $0.28 | $0.12 | $0.065 |
| 5.06 | R6, R7 | Gate Pull-Down Resistor 100k$\Omega$ 1/16W 1% | Yageo | RC0402FR-07100KL | 0402 | DigiKey / 311-100KLRCT-ND | 2 | $0.05 | $0.10 | $0.01 | $0.004 |

### 2.6 Mechanical Enclosure, Optics & Interconnect
| Item | RefDes | Description | Mfr | MPN | Package | Supplier / SKU | Qty | Unit (1x) | Ext (1x) | 100x | 1000x |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 6.01 | ENC1 | Rugged Polycarbonate Enclosure IP67 UV-Resistant Gray | Polycase | ML-47F | Box 160x110x60mm | Polycase / ML-47F | 1 | $16.20 | $16.20 | $12.40 | $9.80 |
| 6.02 | VNT1 | Protective Vent Hydrophobic/Oleophobic PTFE M12 Membrane | W. L. Gore | PMF100318 | M12x1.5 Threaded | Gore Direct / PMF100318 | 1 | $4.50 | $4.50 | $3.20 | $2.40 |
| 6.03 | PCB1 | 4-Layer Rigid FR4 TG170 ENIG Immersion Gold 1.6mm | JLCPCB / PCBWay | SENTRY-REV-B | Custom PCB 100x80mm | Custom Fabrication | 1 | $8.00 | $8.00 | $2.50 | $1.40 |
| 6.04 | LENS1| Germanium / Silicon AR-Coated Window for Thermal FIR (8-14µm)| Edmund Optics | 68-646 | Optical Window 15mm Dia | Edmund Optics / 68-646 | 1 | $18.50 | $18.50 | $14.20 | $11.50 |
| 6.05 | GLD1 | Cable Gland M12 Brass Nickel-Plated IP68 | Phoenix Contact | 1411124 | M12 Fitting | DigiKey / 277-1411124-ND | 2 | $2.40 | $4.80 | $1.70 | $1.20 |
| 6.06 | CC1 | Silicone Conformal Coating Aerosol 422B (Prorated per PCB)| MG Chemicals | 422B-340G | Aerosol Can 340g | DigiKey / 473-1011-ND | 1 | $1.50 | $1.50 | $0.85 | $0.50 |

---

## 3. Cost Summary & Economics

```
+-----------------------------------------------------------------------------------------------+
|                                  BILL OF MATERIALS COST ROLLUP                                |
|                                                                                               |
|  Category                               1x Prototype (USD)   100x Pilot (USD)   1000x Prodn (USD) |
|  -------------------------------------------------------------------------------------------  |
|  1.0 Core Compute & Clocks                     $6.76              $4.57               $3.66   |
|  2.0 Multi-Modal Sensor Array                 $97.82             $79.83              $66.41   |
|  3.0 Sub-GHz Long-Range RF                    $20.92             $15.98              $12.75   |
|  4.0 Power, MPPT & LiFePO4                    $31.46             $23.70              $18.67   |
|  5.0 Autonomous Actuation & Alarms            $11.27              $8.46               $6.45   |
|  6.0 Enclosure, Optics & Interconnect         $53.50             $34.85              $26.80   |
|  -------------------------------------------------------------------------------------------  |
|  TOTAL HARDWARE BOM COST                     $221.73            $167.39             $134.74   |
+-----------------------------------------------------------------------------------------------+
```

### Commercial Viability Analysis
* **Wildfire Suppression Cost Context:** Standard aerial suppression operations (airtanker drops) exceed **$65,000 per flight-hour**, and structural losses per hectare in the wildland-urban interface average **$240,000**.
* **Deployment Density:** Monitored at a recommended grid resolution of 1 node per $2.5\text{ hectares}$ ($160\text{ meters}$ spacing across high-risk corridors), full coverage cost is **$53.90 per hectare** at production scale, delivering an ROI of $> 4,000\times$ on avoided structural and ecological catastrophe.

---

## 4. Complete Hardware Pinout & Interconnect Matrix

Every single GPIO pin and physical bus interface on the ESP32-S3-WROOM-1-N16R8 is allocated deterministically without pin overlap or multiplexing conflicts.

```
                  +----------------------------------------------+
                  |         ESP32-S3-WROOM-1-N16R8 (Top View)    |
                  |                                              |
      GND    [ 1] |                                              | [41] GND
     3V3     [ 2] |                                              | [40] GPIO44 (U0RXD - Debug Console)
   EN (RST)  [ 3] |                                              | [39] GPIO43 (U0TXD - Debug Console)
    GPIO4    [ 4] | DIO1 (SX1262 LoRa Interrupt)                 | [38] GPIO42 (NC / Reserved)
    GPIO5    [ 5] | STROBE_EN (AO3400A Siren/LED Gate)           | [37] GPIO41 (NC / Reserved)
    GPIO6    [ 6] | BQ_INT (TI BQ25798 Charger Interrupt)        | [36] GPIO40 (NC / Reserved)
    GPIO7    [ 7] | SPS30_RST (Sensirion Reset Pin)              | [35] GPIO39 (NC / Reserved)
    GPIO8    [ 8] | SDA0 (BME688 I2C0 Bus Data)                  | [34] GPIO38 (NC / Reserved)
    GPIO9    [ 9] | SCL0 (BME688 I2C0 Bus Clock)                 | [33] GPIO37 (NC / Reserved)
    GPIO10   [10] | LORA_NSS (SX1262 SPI Chip Select)            | [32] GPIO36 (NC / Reserved)
    GPIO11   [11] | LORA_MOSI (SX1262 SPI Master Out)            | [31] GPIO35 (NC / Reserved)
    GPIO12   [12] | LORA_SCK (SX1262 SPI Clock)                  | [30] GPIO0  (Boot Strapping / Button)
    GPIO13   [13] | LORA_MISO (SX1262 SPI Master In)             | [29] GPIO45 (NC / Reserved)
    GPIO14   [14] | I2S_BCLK (INMP441 Bit Clock)                 | [28] GPIO48 (RGB WS2812 Status LED)
    GPIO15   [15] | I2S_WS (INMP441 Word Select / LRCLK)         | [27] GPIO47 (NC / Reserved)
    GPIO16   [16] | I2S_SD (INMP441 Serial Audio Data)           | [26] GPIO21 (LORA_BUSY - SX1262 Status)
    GPIO17   [17] | SPS30_TX (UART1 RX from Particulate Sensor)  | [25] GPIO20 (USB D+)
    GPIO18   [18] | SPS30_RX (UART1 TX to Particulate Sensor)    | [24] GPIO19 (USB D-)
    GPIO1    [19] | SDA1 (MLX90640 I2C1 Bus Data)                | [23] GPIO3  (ULP_ADC - Battery Voltage)
    GPIO2    [20] | SCL1 (MLX90640 I2C1 Bus Clock)               | [22] GND
                  +----------------------------------------------+
```

### Detailed Functional Pin Assignment
| ESP32-S3 Pin | GPIO | Bus / Protocol | Target IC / Peripheral | Signal Function | Electrical Characteristics & Pullups |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 19 | **GPIO1** | $\text{I}^2\text{C}1$ | MLX90640 FIR Array | `SDA1` Data | 3.3V Logic, $2.2\text{ k}\Omega$ pullup to 3.3V, Fast-Mode+ ($1.0\text{ MHz}$) |
| 20 | **GPIO2** | $\text{I}^2\text{C}1$ | MLX90640 FIR Array | `SCL1` Clock | 3.3V Logic, $2.2\text{ k}\Omega$ pullup to 3.3V, Fast-Mode+ ($1.0\text{ MHz}$) |
| 23 | **GPIO3** | ADC1_CH2 | Battery Voltage Divider | `VBAT_SENSE` | Analog input $0-3.1\text{ V}$ via $2\times 100\text{ k}\Omega$ $0.1\%$ divider with $10\text{ nF}$ filter |
| 4 | **GPIO4** | Direct Digital | SX1262 LoRa Radio | `DIO1` | External interrupt on LoRa packet received / TX done; active HIGH |
| 5 | **GPIO5** | Direct Output | AO3400A Gate Driver | `ALARM_TRIG` | Logic level gate drive for 110dB Siren & Amber Strobe; $100\text{ k}\Omega$ pull-down |
| 6 | **GPIO6** | Direct Digital | TI BQ25798 MPPT | `CHG_INT` | Active LOW open-drain interrupt on charge status / fault; internal pullup |
| 7 | **GPIO7** | Direct Output | Sensirion SPS30 | `SPS_RESET` | Active LOW hardware reset line to cycle optical particle sensor |
| 8 | **GPIO8** | $\text{I}^2\text{C}0$ | BME688 Gas Matrix | `SDA0` Data | 3.3V Logic, $4.7\text{ k}\Omega$ pullup to 3.3V, Standard Fast-Mode ($400\text{ kHz}$) |
| 9 | **GPIO9** | $\text{I}^2\text{C}0$ | BME688 Gas Matrix | `SCL0` Clock | 3.3V Logic, $4.7\text{ k}\Omega$ pullup to 3.3V, Standard Fast-Mode ($400\text{ kHz}$) |
| 10 | **GPIO10**| SPI | SX1262 LoRa Radio | `LORA_NSS` | Active LOW Chip Select; $16\text{ MHz}$ SPI Mode 0 |
| 11 | **GPIO11**| SPI | SX1262 LoRa Radio | `LORA_MOSI` | Master Out Slave In; $16\text{ MHz}$ SPI Mode 0 |
| 12 | **GPIO12**| SPI | SX1262 LoRa Radio | `LORA_SCK` | SPI Serial Clock; up to $16\text{ MHz}$ |
| 13 | **GPIO13**| SPI | SX1262 LoRa Radio | `LORA_MISO` | Master In Slave Out; $16\text{ MHz}$ SPI Mode 0 |
| 14 | **GPIO14**| $\text{I}^2\text{S}0$ | INMP441 MEMS Mic | `I2S_BCLK` | Audio Bit Clock ($16\text{ kHz} \times 32\text{ bits} \times 2\text{ ch} = 1.024\text{ MHz}$) |
| 15 | **GPIO15**| $\text{I}^2\text{S}0$ | INMP441 MEMS Mic | `I2S_WS` | Audio Word Select / LRCLK ($16.0\text{ kHz}$ frame strobe) |
| 16 | **GPIO16**| $\text{I}^2\text{S}0$ | INMP441 MEMS Mic | `I2S_SD` | Serial Audio Data input (24-bit resolution over DMA) |
| 17 | **GPIO17**| UART1 | Sensirion SPS30 | `SPS_TXD` | ESP32 UART1 RX input from SPS30 TX ($115200\text{ baud}$, 8N1) |
| 18 | **GPIO18**| UART1 | Sensirion SPS30 | `SPS_RXD` | ESP32 UART1 TX output to SPS30 RX ($115200\text{ baud}$, 8N1) |
| 26 | **GPIO21**| Direct Digital | SX1262 LoRa Radio | `LORA_BUSY` | Radio busy line; MCU waits for LOW before initiating next SPI command |
| 28 | **GPIO48**| RMT / Direct | Onboard Diagnostic | `NEOPIXEL` | Single WS2812B-2020 RGB status LED for local deployment testing |
| 30 | **GPIO0** | Strapping | Boot Button | `BOOT_SW` | Low at reset initiates ROM serial bootloader; internal pullup |
| 39 | **GPIO43**| UART0 | Debug Console | `TXD0` | Serial debug telemetry output at $115200\text{ baud}$ |
| 40 | **GPIO44**| UART0 | Debug Console | `RXD0` | Serial programming input at $115200\text{ baud}$ |

---

## 5. Comprehensive Electrical Power Budgets

### 5.1 Operating State Breakdown
The SentryHive node transitions across discrete operational states managed by the FreeRTOS power-triage task.

```
+-----------------------------------------------------------------------------------------------+
|                             CURRENT CONSUMPTION BY SUBSYSTEM & STATE                          |
|                                                                                               |
|  Subsystem / Component     State 1: Full    State 2: Light   State 3: Standby State 4: Deep   |
|                           Inference (mA)   Sensing (mA)     Sleep (mA)       Sleep ULP (µA)   |
|  -------------------------------------------------------------------------------------------  |
|  ESP32-S3 (240MHz/80MHz)      82.00            28.50            0.80             12.0 µA      |
|  Sensirion SPS30 (5V boost)   55.00             0.05 (sleep)    0.05              0.05 µA     |
|  Bosch BME688 (10-step)       12.50            12.50            0.003             0.003 µA    |
|  Melexis MLX90640 (4Hz)       18.00             0.00 (sleep)    0.00              0.00 µA     |
|  Knowles INMP441 (Audio)       1.40             0.00 (sleep)    0.00              0.00 µA     |
|  Semtech SX1262 (RX mode)      5.80             0.00 (sleep)    0.001             0.001 µA    |
|  Power Rails & Regulators      0.08             0.06            0.0006            0.00006 µA  |
|  -------------------------------------------------------------------------------------------  |
|  TOTAL CURRENT DRAW          174.78 mA         41.11 mA         0.854 mA         12.054 µA    |
|  POWER @ 3.3V                576.77 mW        135.66 mW         2.82 mW           0.040 mW    |
+-----------------------------------------------------------------------------------------------+
```

### 5.2 LoRa Wireless Transmission Current Spikes
* **SX1262 TX @ +22 dBm (US915 band):** $118.0\text{ mA}$ @ $3.3\text{ V}$ ($389.4\text{ mW}$).
* **Packet Airtime Calculation (52 bytes, SF7, BW 125 kHz, CR 4/5):**
  $$T_{packet} = T_{preamble} + T_{payload} = (8 + 4.25) \cdot \frac{2^7}{125000} + \left(8 + \max\left(\lceil \frac{8 \cdot 52 - 4 \cdot 7 + 28}{4 \cdot 7}\rceil \cdot 5, 0\right)\right) \cdot \frac{2^7}{125000} = 61.7\text{ ms}$$
* **Energy per Uplink Burst:**
  $$E_{TX} = 3.3\text{ V} \times 118\text{ mA} \times 0.0617\text{ s} = 24.03\text{ mJ} = 0.00668\text{ mWh}$$

### 5.3 Active Strobe & Siren Alarm Actuation Draw
* **110dB Piezo Siren (SC628P):** $28.0\text{ mA}$ continuous @ $3.3\text{ V}$ ($92.4\text{ mW}$).
* **Amber Strobe LED (Cree XP-E2):** Pulsed at $2.0\text{ Hz}$ with $10\%$ duty cycle ($350\text{ mA} \times 0.10 = 35.0\text{ mA}$ average, $115.5\text{ mW}$).
* **Total Peak Critical Alarm Current:** $63.0\text{ mA}$ combined actuation draw.

---

## 6. Daily Energy Harvest Balance & Autonomy Calculations

### 6.1 Baseline Nominal Cycle (Tier 0 Profile)
Under standard environmental monitoring conditions (Tier 0), the node executes a 60-second recurring operational cycle:
1. **Multi-Modal Active Window (1.0 second duration):**
   * ESP32-S3 runs at $240\text{ MHz}$ executing ESP-NN vector INT8 inference across acoustic, thermal, and gas vectors.
   * All sensors active: SPS30 optical chamber, BME688 heating cycle, MLX90640 4Hz DMA frame acquisition, INMP441 audio FFT.
   * Current draw: $174.78\text{ mA}$ for $1.0\text{ s}$.
2. **LoRa Uplink Burst (0.062 seconds duration):**
   * Current draw: $118.0\text{ mA}$ for $0.062\text{ s}$.
3. **Standby Sleep Window (58.938 seconds duration):**
   * Sensors powered down / placed in deep standby; ESP32-S3 in light sleep with RTC timer active.
   * Current draw: $0.854\text{ mA}$ for $58.938\text{ s}$.

#### Average Current & Energy Computation
$$\bar{I}_{cycle} = \frac{(174.78\text{ mA} \times 1.0\text{ s}) + (118.0\text{ mA} \times 0.062\text{ s}) + (0.854\text{ mA} \times 58.938\text{ s})}{60.0\text{ s}}$$
$$\bar{I}_{cycle} = \frac{174.78 + 7.316 + 50.333}{60.0} = \frac{232.429}{60.0} = 3.874\text{ mA}$$

* **Average Continuous Power:** $P_{avg} = 3.3\text{ V} \times 3.874\text{ mA} = 12.78\text{ mW}$
* **Daily Energy Consumption:**
  $$E_{daily} = 3.874\text{ mA} \times 24\text{ h} = 92.98\text{ mAh/day} = 0.3068\text{ Wh/day} \quad (306.8\text{ mWh/day})$$

### 6.2 Solar Energy Harvest Modeling (Worst-Case Winter Scenario)
To validate true perpetual operation, the energy balance is evaluated under worst-case high-latitude winter conditions in a dense conifer canopy:
* **Solar Panel Nominal Rating:** $5.0\text{ W}$ ($V_{mp} = 6.0\text{ V}, I_{mp} = 0.833\text{ A}$).
* **Canopy Shading & Dirt Derating Factor ($\eta_{canopy}$):** $0.35$ ($65\%$ solar attenuation due to needle canopy, sap, and dust deposition).
* **Peak Sun Hours (PSH) in Winter:** $2.5\text{ hours/day}$.
* **MPPT Buck-Boost Charging Efficiency ($\eta_{MPPT}$):** $94.0\%$.
* **$\text{LiFePO}_4$ Coulombic Charging Efficiency ($\eta_{battery}$):** $95.0\%$.

#### Daily Harvested Energy Calculation
$$E_{harvest} = P_{panel} \times \text{PSH} \times \eta_{canopy} \times \eta_{MPPT} \times \eta_{battery}$$
$$E_{harvest} = 5.0\text{ W} \times 2.5\text{ h} \times 0.35 \times 0.94 \times 0.95 = 3.908\text{ Wh/day} = 3908\text{ mWh/day}$$

* **Harvest-to-Consumption Surplus Ratio:**
  $$\text{Energy Margin} = \frac{E_{harvest}}{E_{daily}} = \frac{3908\text{ mWh}}{306.8\text{ mWh}} = 12.74\times$$

Even under extreme winter cloud cover and heavy canopy shading, **the solar subsystem generates over $12\times$ the daily required energy**, continuously replenishing the storage reserve.

### 6.3 Blackout Autonomy Analysis (Zero Insolation / Catastrophic Smoke Plume)
In the event of continuous atmospheric smoke obscuration where solar irradiance falls to $0\text{ W/m}^2$:
* **Nominal Usable Battery Capacity:** $3400\text{ mAh} \times 80\%\text{ DoD (Depth of Discharge)} = 2720\text{ mAh}$.
* **Autonomy under Tier 0 Nominal Monitoring:**
  $$T_{autonomy, Tier 0} = \frac{2720\text{ mAh}}{92.98\text{ mAh/day}} = 29.25\text{ days}$$
* **Autonomy under Tier 2 Low-Power Triage Mode ($\bar{I} = 0.92\text{ mA}$):**
  $$T_{autonomy, Tier 2} = \frac{2720\text{ mAh}}{0.92\text{ mA} \times 24\text{ h/day}} = \frac{2720}{22.08} = 123.1\text{ days} \quad (> 4\text{ months})$$

---

## 7. Detailed Sub-Circuit Schematics & Interfacing

### 7.1 MPPT Solar Charger & Power Path Management (TI BQ25798)
The BQ25798 IC regulates solar panel input dynamically using Maximum Power Point Tracking (MPPT). The internal algorithm perturbs input voltage to maximize charging current into the $3.2\text{ V}$ $\text{LiFePO}_4$ cell.

```
       +-----------------------------------------------------------------------+
       |                           TI BQ25798 MPPT SCHEMATIC                   |
       |                                                                       |
       |  PV+ (6V) ---+---> [SMBJ6.0CA] ---> VBUS (Pin 1,2)                    |
       |              |                            |                           |
       |            [10µF]                    [4.0x4.0mm]                      |
       |              |                     SW1 --[1.5µH]-- SW2                |
       |             GND                           |                           |
       |                                    SYS Rail (3.2V-3.65V)              |
       |                                           |                           |
       |                             +-------------+-------------+             |
       |                             |                           |             |
       |                             v                           v             |
       |                     [TPS62840 Buck]             BAT+ (LiFePO4 Cell)   |
       |                             |                           |             |
       |                       VOUT = 3.30V                 [AON2802 FETs]     |
       |                             |                           |             |
       |                       System Power Rail          [TI BQ29704 Prot]    |
       |                                                         |             |
       |                                                    BAT- / GND         |
       +-----------------------------------------------------------------------+
```

* **Overvoltage Cutoff:** Hardwired to $3.65\text{ V DC}$ via precision feedback divider to prevent LiFePO4 overcharge.
* **Undervoltage Cutoff:** BQ29704 disconnects the cell if terminal voltage drops below $2.50\text{ V DC}$, protecting the cathode structure against copper dissolution.
* **Overcurrent Protection:** Dual AON2802 back-to-back N-channel MOSFETs trip if discharge current exceeds $6.0\text{ A}$.

### 7.2 Ultra-Low Quiescent System Buck Regulator (TI TPS62840)
* **Topology:** High-efficiency step-down converter with DCS-Control topology.
* **Input Range:** $1.8\text{ V}$ to $6.5\text{ V}$ (fully covers LiFePO4 operating envelope: $2.8\text{ V}$ to $3.65\text{ V}$).
* **Output Voltage:** Configured to $3.30\text{ V}$ via $V_{SET}$ pin (pulled to ground via high-precision $0.1\%$ resistor).
* **Efficiency:** $> 92\%$ efficiency at microampere load currents ($10\ \mu\text{A} - 100\ \mu\text{A}$), climbing to $96\%$ at $50\text{ mA}$.
* **Ripple:** $< 12\text{ mV}$ peak-to-peak during full active dual-core inference.

### 7.3 I2C Bus Dual-Domain Segmentation
To prevent slow sensor transactions from blocking real-time thermal image streaming, the design implements two physically isolated $\text{I}^2\text{C}$ buses:
* **$\text{I}^2\text{C}$ Bus 0 (Standard Fast Mode, 400 kHz):**
  * Connects exclusively to the Bosch BME688 MOX gas sensor.
  * Pullup resistors: $4.7\text{ k}\Omega$ to $3.3\text{ V}$.
  * Bus capacitance: $< 45\text{ pF}$.
* **$\text{I}^2\text{C}$ Bus 1 (Fast-Mode Plus, 1.0 MHz with DMA):**
  * Connects exclusively to the Melexis MLX90640 Far-Infrared sensor.
  * Pullup resistors: Stiff $2.2\text{ k}\Omega$ resistors to satisfy the $120\text{ ns}$ maximum rise-time specification for Fast-Mode Plus at $1\text{ MHz}$.
  * Eliminates packet arbitration overhead and enables continuous DMA transfers of full 768-pixel frames at $4\text{ Hz}$.

### 7.4 Acoustic Audio Transduction Sub-Circuit (Knowles INMP441)
* **Clock Routing:** High-speed I2S bit clock (`GPIO14`) is routed with adjacent ground guard traces to prevent RF crosstalk into the LoRa matching network.
* **Power Decoupling:** INMP441 $V_{DD}$ pin is filtered by a dedicated ferrite bead (Murata BLM15HD182SN1D) followed by a $0.1\ \mu\text{F}$ X7R and $10\ \mu\text{F}$ tantalum capacitor, suppressing digital switching ripple from the ESP32-S3 core.
* **Acoustic Port Ingress Protection:** The bottom acoustic port is sealed against the outer enclosure wall using a custom die-cut closed-cell Poron foam gasket (Rogers Corp), backed by a hydrophobic oleophobic PTFE acoustic membrane with an acoustic insertion loss of $< 1.2\text{ dB}$ across $2\text{ kHz} - 8\text{ kHz}$.

### 7.5 Autonomous Actuator Drive Sub-Circuit
```
      3.3V System Rail
            |
            +---------------+
            |               |
         +-----+            |
         | BZ1 | Piezo    +----+ (Flyback Diode)
         |110dB| Siren    | D2 | MBR140T3G
         +-----+          +----+
            |               |
            +-------+-------+
                    |
                    +--------------------+
                    | Drain              |
                 +-----+                 |
  GPIO5 -------->| Q3  | AO3400A         |
  (ALARM_TRIG)   |     | N-MOSFET        |
                 +-----+                 |
                    | Source             |
                   GND                   |
                                         v
                            [LED1: Cree XP-E2 Strobe]
                                         |
                                      +-----+
                       GPIO5 -------->| Q4  | AO3400A
                                      +-----+
                                         |
                                        GND
```

* **Gate Drive:** Driven directly from ESP32-S3 `GPIO5` with a $100\ \Omega$ series damping resistor and a $100\text{ k}\Omega$ pull-down resistor ensuring the alarm remains quiescent during MCU power-on reset.
* **Inductive Clamp:** High-speed Schottky diode D2 (MBR140T3G) clamps back-EMF voltage transients produced by the piezo transducer coil, protecting the AO3400A drain.

---

## 8. Environmental Ruggedization & Manufacturing Directives

### 8.1 PCB Layout & Fabrication Rules
* **Layer Stackup (4-Layer FR4 TG170):**
  * Layer 1 (Top): High-speed signals, RF microstrip, sensor digital lines.
  * Layer 2 (Inner 1): Solid continuous Ground Plane ($0\text{V}$ reference).
  * Layer 3 (Inner 2): Split Power Planes ($3.3\text{V}$ digital, $3.3\text{V}$ analog, $V_{BAT}$).
  * Layer 4 (Bottom): Non-critical I/O, battery connection tabs, power MOSFET traces.
* **RF Transmission Line:** LoRa antenna trace from SX1262 pin to U.FL receptacle designed as a grounded coplanar waveguide ($50.0\ \Omega \pm 5\%$ impedance): trace width $0.35\text{ mm}$, dielectric thickness $0.20\text{ mm}$, ground spacing $0.25\text{ mm}$.
* **Surface Finish:** Electroless Nickel Immersion Gold (ENIG) providing corrosion resistance and planar pad surfaces for fine-pitch LGA/QFN packages.

### 8.2 Ingress Protection (IP67) & Thermal Management
* **Enclosure:** Polycase ML-47F impact-resistant polycarbonate rated UL94-V0 flame retardant and UL508-4X outdoor weather resistance.
* **PTFE Pressure Equilibrium Vent:** Gore PMF100318 vent equalizes internal barometric pressure while maintaining an IP67 liquid water barrier ($> 30\text{ kPa}$ water intrusion pressure) and allowing ambient VOC/particulate exchange.
* **Conformal Coating:** All assembled PCBs receive a dual-coat application of MG Chemicals 422B silicone conformal coating (conforming to IPC-CC-830B and MIL-I-46058C), masking only the MEMS microphone acoustic port, the SPS30 optical chamber, and the BME688 gas sensing aperture.
* **Thermal Relief:** Critical power switching components (BQ25798, TPS62840, AO3400A) interface to thermal ground vias dissipating heat directly into the bottom ground plane, ensuring thermal stability up to $+70^\circ\text{C}$ ambient temperatures.
