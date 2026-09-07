# SentryHive: Defensive Security Architecture & Hardening Specifications

**Specification Version:** 1.0.0  
**Compliance Target:** Defensive Cyber-Physical Architecture & Operational Safety (VoltHacks 2026)  

---

## 1. Defensive Threat Model & Trust Boundaries

The SentryHive platform operates across multiple cyber-physical trust domains:

```text
               TRUST BOUNDARIES & ATTACK SURFACE REDUCTION

  [ Uncontrolled Physical Field ]               [ Wireless Ingestion Gateway ]
  - Tampering with physical nodes               - Malformed LoRa packets
  - Acoustic noise injection                    - Out-of-bounds telemetry
  - Solar / battery depletion                   - CRC-16 corrupted frames
              │                                              │
              ▼                                              ▼
  [ Hardware Boundary Isolation ]               [ FastAPI Input Sanitization ]
  - LittleFS Circular Ring Buffer               - Pydantic strict numeric bounds
  - Hardware WDT auto-reset                     - NaN / Infinity rejection
  - Non-combustible LiFePO4 cell                - Reject oversized JSON (>1MB)
              │                                              │
              └──────────────────────┬───────────────────────┘
                                     ▼
                      [ Local Operational Network ]
                      - Localhost-bound ASGI (127.0.0.1)
                      - Safe relative path resolution (No traversal)
                      - Zero hardcoded secrets / API tokens
```

---

## 2. Defensive Countermeasures & Mitigations

| Threat Vector | Potential Impact | Defensive Mitigation Implemented | Verified Test Case |
| :--- | :--- | :--- | :--- |
| **Malformed Coordinate Injection** | Server crash / NaN floating-point corruption in spatial geometry calculations | Pydantic strict field validators enforcing $[-90, 90]$ for latitude, $[-180, 180]$ for longitude, and rejecting `NaN`/`Infinity`. | `test_security_reject_nan_infinity_coordinates` |
| **Path Traversal via Report API** | Unauthorized filesystem disclosure (e.g. `/etc/passwd`) | Strict URI sanitization and UUID-based incident lookup rejecting dot-dot sequences with HTTP 404/400. | `test_security_safe_incident_report_sanitization` |
| **Denial-of-Service Fleet Scaling** | RAM exhaustion via unbounded virtual node allocation | Bounded scaling endpoint enforcing strict upper threshold ($\le 100\text{ nodes}$). | `test_security_fleet_scale_limits` |
| **Corrupted Binary Radio Packets** | Buffer overflows / memory corruption in C/C++ struct decoders | Fixed-length 52-byte struct validation with CRC-16-CCITT polynomial verification ($0x1021$). Packets failing CRC are dropped immediately. | `test_invalid_binary_frame_rejection` |
| **Negative Physical Quantities** | Model divergence from impossible sensor inputs (e.g., negative wind speed or Kelvin temperatures) | Strict lower-bound clamping and validation schemas ($V_{wind} \ge 0.0\text{ m/s}$). | `test_security_reject_negative_physical_parameters` |
| **Secret Leakage in Version Control** | Credential theft | Exclusion of all `.env`, `.pem`, and credentials from Git; automated regex audit passes with zero leaks found. | `git grep -iE "api_key\|secret"` |

---

## 3. Security Verification Test Execution

Execute the defensive security test suite:

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_security_hardening.py -v
```

```text
============================= test session starts ==============================
collected 5 items

tests/test_security_hardening.py::test_security_reject_nan_infinity_coordinates PASSED [ 20%]
tests/test_security_hardening.py::test_security_reject_out_of_bounds_coordinates PASSED [ 40%]
tests/test_security_hardening.py::test_security_reject_negative_physical_parameters PASSED [ 60%]
tests/test_security_hardening.py::test_security_safe_incident_report_sanitization PASSED [ 80%]
tests/test_security_hardening.py::test_security_fleet_scale_limits PASSED [100%]

======================== 5 passed in 0.42s ========================
```
