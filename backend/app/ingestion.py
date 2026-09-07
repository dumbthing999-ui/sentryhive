"""Telemetry Ingestion Pipeline and Streaming Processor for SentryHive.

Handles:
1. Multi-protocol streaming ingestion:
   - REST API JSON packets
   - Binary LoRa packets (packed binary format & CBOR)
   - WebSockets live uplink / downlink
2. Real-time multi-modal ML evaluation triggering
3. Automated alert dispatch and perimeter projection
4. Time-series ring buffer storage and node health registry
5. Live dashboard broadcast multiplexer
"""

from __future__ import annotations

import asyncio
import struct
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

import cbor2
from fastapi import WebSocket

from backend.app.alerts import alert_dispatcher
from backend.app.ml.fusion_engine import fusion_engine
from backend.app.models import (
    AlertLevel,
    AlertRecord,
    BatteryDegradationTier,
    BatteryMetrics,
    GasMicroclimateData,
    GeoCoordinates,
    NodeConnectionStatus,
    NodeRegistration,
    NodeStatus,
    ParticulateData,
    TelemetryPacket,
    ThermalIRData,
    AcousticData,
)


class IngestionPipeline:
    """Core Telemetry Ingestion and Multi-Modal Fusion Dispatcher."""

    MAX_HISTORY_PER_NODE: int = 500

    def __init__(self) -> None:
        # Node registries
        self._nodes: Dict[str, NodeStatus] = {}
        self._time_series: Dict[str, Deque[TelemetryPacket]] = {}
        self._latest_packets: Dict[str, TelemetryPacket] = {}

        # Connected WebSocket clients (dashboard streams and ingest sockets)
        self._dashboard_clients: Set[WebSocket] = set()
        self._uplink_clients: Set[WebSocket] = set()

        # Ingestion counters
        self.packets_ingested: int = 0
        self.bytes_ingested: int = 0
        self.start_time: float = time.time()

        # Seed reference sensor nodes
        self._initialize_reference_network()

    def _initialize_reference_network(self) -> None:
        """Seed default operational nodes across Sierra Nevada Tahoe Basin."""
        reference_nodes = [
            (
                "NODE-A741",
                "Ridgecrest Ridge",
                GeoCoordinates(
                    latitude=39.1823,
                    longitude=-120.1412,
                    elevation_m=2150.0,
                    canopy_coverage_pct=82.0,
                    vegetation_type="Dense Mixed Conifer",
                ),
            ),
            (
                "NODE-B812",
                "Eagle Rock Overlook",
                GeoCoordinates(
                    latitude=39.1874,
                    longitude=-120.1345,
                    elevation_m=2280.0,
                    canopy_coverage_pct=65.0,
                    vegetation_type="Dry Pine & Granite Scrub",
                ),
            ),
            (
                "NODE-C399",
                "Canyon Creek Gulch",
                GeoCoordinates(
                    latitude=39.1765,
                    longitude=-120.1489,
                    elevation_m=1980.0,
                    canopy_coverage_pct=90.0,
                    vegetation_type="Riparian Fir & Oak Duff",
                ),
            ),
            (
                "NODE-D504",
                "Pine Forest Reserve",
                GeoCoordinates(
                    latitude=39.1801,
                    longitude=-120.1290,
                    elevation_m=2110.0,
                    canopy_coverage_pct=78.0,
                    vegetation_type="Chaparral & Conifer WUI",
                ),
            ),
        ]

        for node_id, name, coords in reference_nodes:
            self._nodes[node_id] = NodeStatus(
                node_id=node_id,
                name=name,
                coordinates=coords,
                status=NodeConnectionStatus.ONLINE,
                battery_tier=BatteryDegradationTier.TIER_0_FULL_NOMINAL,
                battery_voltage=3.95,
                last_seen=time.time(),
                packet_count=0,
                packet_loss_rate=0.0,
                latest_fti=0.04,
                latest_alert_level=AlertLevel.NOMINAL,
            )
            self._time_series[node_id] = deque(maxlen=self.MAX_HISTORY_PER_NODE)

    def register_node(self, registration: NodeRegistration) -> NodeStatus:
        """Register or update an edge node in the network inventory."""
        node = NodeStatus(
            node_id=registration.node_id,
            name=registration.name,
            coordinates=registration.coordinates,
            status=NodeConnectionStatus.ONLINE,
            battery_tier=BatteryDegradationTier.TIER_0_FULL_NOMINAL,
            battery_voltage=3.95,
            last_seen=time.time(),
            packet_count=0,
            packet_loss_rate=0.0,
            latest_fti=0.0,
            latest_alert_level=AlertLevel.NOMINAL,
            firmware_version=registration.firmware_version,
        )
        self._nodes[registration.node_id] = node
        if registration.node_id not in self._time_series:
            self._time_series[registration.node_id] = deque(maxlen=self.MAX_HISTORY_PER_NODE)
        return node

    def get_node(self, node_id: str) -> Optional[NodeStatus]:
        """Lookup node status by ID."""
        return self._nodes.get(node_id)

    def list_nodes(self) -> List[NodeStatus]:
        """Return all active nodes in the fleet."""
        return list(self._nodes.values())

    async def ingest_packet(self, packet: TelemetryPacket) -> Tuple[TelemetryPacket, Optional[AlertRecord]]:
        """Core pipeline: Ingest, evaluate ML fusion, update registry, dispatch alerts."""
        self.packets_ingested += 1

        # 1. Execute Multi-Modal Fusion Engine to verify / compute FTI
        eval_result = fusion_engine.evaluate_telemetry(packet)
        packet.fire_threat_index = eval_result.fire_threat_index
        packet.alert_level = eval_result.alert_level

        node_id = packet.node_id

        # 2. Onboard or update node registry
        node = self._nodes.get(node_id)
        if not node:
            # Auto-register unknown node with default Tahoe coordinates
            default_coords = GeoCoordinates(
                latitude=39.1820 + (hash(node_id) % 100) * 0.0001,
                longitude=-120.1400 + (hash(node_id) % 100) * 0.0001,
                elevation_m=2100.0,
                canopy_coverage_pct=75.0,
                vegetation_type="Mixed Sierra Conifer",
            )
            node = NodeStatus(
                node_id=node_id,
                name=f"Field Node {node_id}",
                coordinates=default_coords,
                status=NodeConnectionStatus.ONLINE,
            )
            self._nodes[node_id] = node
            self._time_series[node_id] = deque(maxlen=self.MAX_HISTORY_PER_NODE)

        # Update node live metrics
        node.last_seen = packet.timestamp
        node.packet_count += 1
        node.battery_voltage = packet.battery.voltage_v
        node.battery_tier = packet.battery.degradation_tier
        node.latest_fti = packet.fire_threat_index
        node.latest_alert_level = packet.alert_level

        if packet.alert_level == AlertLevel.CRITICAL_EVACUATION:
            node.status = NodeConnectionStatus.EMERGENCY
        elif packet.battery.degradation_tier in (
            BatteryDegradationTier.TIER_2_LOW_POWER_TRIAGE,
            BatteryDegradationTier.TIER_3_EMERGENCY_SURVIVAL,
        ):
            node.status = NodeConnectionStatus.DEGRADED
        else:
            node.status = NodeConnectionStatus.ONLINE

        # 3. Store in time-series buffer
        self._time_series[node_id].append(packet)
        self._latest_packets[node_id] = packet

        # 4. Trigger alert dispatcher
        alert_record = alert_dispatcher.process_telemetry(
            packet=packet,
            node_coords=node.coordinates,
        )

        # 5. Broadcast to connected WebSocket clients
        await self.broadcast_event(
            {
                "event": "telemetry",
                "packet": packet.model_dump(),
                "alert": alert_record.model_dump() if alert_record else None,
            }
        )

        return packet, alert_record

    async def ingest_batch(self, packets: List[TelemetryPacket]) -> Dict[str, Any]:
        """Batch ingestion helper."""
        processed: List[TelemetryPacket] = []
        alerts: List[AlertRecord] = []

        for p in packets:
            pkt, alt = await self.ingest_packet(p)
            processed.append(pkt)
            if alt:
                alerts.append(alt)

        return {
            "ingested_count": len(processed),
            "alerts_generated": len(alerts),
            "packets": [p.model_dump() for p in processed],
        }

    PACKET_STRUCT_FMT: str = "<BBHIHHHHHHfhHhhBhBH"
    PACKET_STRUCT_SIZE: int = struct.calcsize(PACKET_STRUCT_FMT)

    def decode_cbor_telemetry(self, raw_bytes: bytes) -> TelemetryPacket:
        """Decode either CBOR format or fixed binary LoRa frame."""
        self.bytes_ingested += len(raw_bytes)

        # Try CBOR decode first
        try:
            cbor_obj = cbor2.loads(raw_bytes)
            if isinstance(cbor_obj, dict):
                node_id = str(cbor_obj.get("node_id", "NODE-A741"))
                return TelemetryPacket(
                    node_id=node_id,
                    timestamp=float(cbor_obj.get("timestamp", time.time())),
                    battery=BatteryMetrics(
                        voltage_v=float(cbor_obj.get("battery_v", 3.95)),
                    ),
                    gas=GasMicroclimateData(
                        temperature_c=float(cbor_obj.get("temp_c", 22.0)),
                        relative_humidity_pct=float(cbor_obj.get("rh_pct", 40.0)),
                        gas_resistance_ohms=float(cbor_obj.get("gas_res", 120000.0)),
                        voc_index=float(cbor_obj.get("voc_index", 50.0)),
                    ),
                    particulates=ParticulateData(
                        pm1_0_ug_m3=float(cbor_obj.get("pm1_0", 2.0)),
                        pm2_5_ug_m3=float(cbor_obj.get("pm2_5", 5.0)),
                        pm10_0_ug_m3=float(cbor_obj.get("pm10", 7.0)),
                    ),
                    thermal=ThermalIRData(
                        thermal_max_temp_c=float(cbor_obj.get("thermal_max", 23.0)),
                        thermal_ambient_temp_c=float(cbor_obj.get("thermal_amb", 22.0)),
                    ),
                    acoustic=AcousticData(
                        acoustic_crackle_event_rate_hz=float(cbor_obj.get("crackle_hz", 0.0)),
                    ),
                )
        except Exception:
            pass

        # Packed binary format fallback
        if len(raw_bytes) >= self.PACKET_STRUCT_SIZE:
            try:
                (
                    proto_ver,
                    flags,
                    node_short_id,
                    ts,
                    bat_mv,
                    fti_x1k,
                    pm1_x10,
                    pm25_x10,
                    pm4_x10,
                    pm10_x10,
                    gas_res,
                    temp_x100,
                    rh_x100,
                    ir_max_x100,
                    ir_mean_x100,
                    crackle_x10,
                    plume_x10,
                    voc_div2,
                    crc,
                ) = struct.unpack(self.PACKET_STRUCT_FMT, raw_bytes[: self.PACKET_STRUCT_SIZE])

                node_id = f"NODE-{node_short_id:04X}"
                return TelemetryPacket(
                    node_id=node_id,
                    timestamp=float(ts) if ts > 0 else time.time(),
                    battery=BatteryMetrics(voltage_v=bat_mv / 1000.0),
                    gas=GasMicroclimateData(
                        temperature_c=temp_x100 / 100.0,
                        relative_humidity_pct=rh_x100 / 100.0,
                        gas_resistance_ohms=float(gas_res),
                        voc_index=float(voc_div2 * 2),
                    ),
                    particulates=ParticulateData(
                        pm1_0_ug_m3=pm1_x10 / 10.0,
                        pm2_5_ug_m3=pm25_x10 / 10.0,
                        pm4_0_ug_m3=pm4_x10 / 10.0,
                        pm10_0_ug_m3=pm10_x10 / 10.0,
                    ),
                    thermal=ThermalIRData(
                        thermal_max_temp_c=ir_max_x100 / 100.0,
                        thermal_ambient_temp_c=ir_mean_x100 / 100.0,
                        thermal_plume_velocity_mm_s=plume_x10 / 10.0,
                    ),
                    acoustic=AcousticData(
                        acoustic_crackle_event_rate_hz=crackle_x10 / 10.0,
                    ),
                    fire_threat_index=fti_x1k / 1000.0,
                    fallback_flags=flags,
                )
            except Exception as e:
                raise ValueError(f"Failed to unpack binary LoRa frame: {e}")

        raise ValueError(
            f"Payload size {len(raw_bytes)} bytes is neither valid CBOR nor {self.PACKET_STRUCT_SIZE}+ byte binary frame."
        )

    @classmethod
    def encode_binary_telemetry(cls, packet: TelemetryPacket) -> bytes:
        """Helper to serialize TelemetryPacket to binary LoRa frame format."""
        try:
            node_short_id = int(packet.node_id.replace("NODE-", "").replace("0x", ""), 16)
        except Exception:
            node_short_id = hash(packet.node_id) & 0xFFFF

        proto_ver = 1
        flags = packet.fallback_flags
        ts = int(packet.timestamp)
        bat_mv = int(packet.battery.voltage_v * 1000)
        fti_x1k = int(packet.fire_threat_index * 1000)
        pm1_x10 = int(packet.particulates.pm1_0_ug_m3 * 10)
        pm25_x10 = int(packet.particulates.pm2_5_ug_m3 * 10)
        pm4_x10 = int(packet.particulates.pm4_0_ug_m3 * 10)
        pm10_x10 = int(packet.particulates.pm10_0_ug_m3 * 10)
        gas_res = float(packet.gas.gas_resistance_ohms)
        temp_x100 = int(packet.gas.temperature_c * 100)
        rh_x100 = int(packet.gas.relative_humidity_pct * 100)
        ir_max_x100 = int(packet.thermal.thermal_max_temp_c * 100)
        ir_mean_x100 = int(packet.thermal.thermal_ambient_temp_c * 100)
        crackle_x10 = int(packet.acoustic.acoustic_crackle_event_rate_hz * 10)
        plume_x10 = int(packet.thermal.thermal_plume_velocity_mm_s * 10)
        voc_div2 = int(packet.gas.voc_index / 2)
        crc = 0xAA55

        return struct.pack(
            cls.PACKET_STRUCT_FMT,
            proto_ver,
            flags,
            node_short_id,
            ts,
            bat_mv,
            fti_x1k,
            pm1_x10,
            pm25_x10,
            pm4_x10,
            pm10_x10,
            gas_res,
            temp_x100,
            rh_x100,
            ir_max_x100,
            ir_mean_x100,
            crackle_x10,
            plume_x10,
            voc_div2,
            crc,
        )

    def get_latest(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """Return latest telemetry snapshot for a single node or all nodes."""
        if node_id:
            pkt = self._latest_packets.get(node_id)
            return {node_id: pkt.model_dump() if pkt else None}
        return {nid: pkt.model_dump() for nid, pkt in self._latest_packets.items()}

    def get_history(self, node_id: str, limit: int = 100) -> List[TelemetryPacket]:
        """Retrieve recent time-series telemetry for a given node."""
        history = self._time_series.get(node_id, deque())
        items = list(history)
        return items[-limit:]

    # WebSocket connection management
    async def connect_client(self, websocket: WebSocket, is_uplink: bool = False) -> None:
        """Register a new WebSocket client."""
        await websocket.accept()
        if is_uplink:
            self._uplink_clients.add(websocket)
        else:
            self._dashboard_clients.add(websocket)

    def disconnect_client(self, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket client."""
        self._dashboard_clients.discard(websocket)
        self._uplink_clients.discard(websocket)

    async def broadcast_event(self, message: Dict[str, Any]) -> None:
        """Broadcast payload to all connected dashboard WebSocket clients."""
        if not self._dashboard_clients:
            return

        dead_clients: List[WebSocket] = []
        for client in self._dashboard_clients:
            try:
                await client.send_json(message)
            except Exception:
                dead_clients.append(client)

        for dead in dead_clients:
            self.disconnect_client(dead)


# Global singleton instance
ingestion_pipeline = IngestionPipeline()
