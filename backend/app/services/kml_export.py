"""KML Geospatial Export Utility for Wildfire Incidents.

Generates OGC Keyhole Markup Language (KML) files for direct import
into ATAK (Android Tactical Assault Kit), Google Earth, and Emergency Dispatch Systems.
"""

import math
from typing import List, Tuple

def generate_kml_polygon(
    incident_id: str,
    title: str,
    center_lat: float,
    center_lon: float,
    radius_m: float,
    state: str,
    peak_fti: float
) -> str:
    """Generates KML document containing flame perimeter ring and tactical placemark."""
    points = 36
    coords = []
    
    # Generate circular perimeter polygon
    for i in range(points + 1):
        angle = (i * 360.0 / points)
        d_lat = (radius_m / 111000.0) * math.cos(math.radians(angle))
        d_lon = (radius_m / (111000.0 * math.cos(math.radians(center_lat)))) * math.sin(math.radians(angle))
        coords.append(f"{center_lon + d_lon:.6f},{center_lat + d_lat:.6f},0")

    coords_str = "\n            ".join(coords)
    color_hex = "7f0000ff" if state == "CRITICAL" else "7f00a5ff" # KML aabbggrr format

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{incident_id} - {title}</name>
    <description>SentryHive Cyber-Physical Incident Perimeter. Peak FTI: {peak_fti:.3f}</description>
    <Style id="firePerimeter">
      <LineStyle>
        <color>ff0000ff</color>
        <width>3</width>
      </LineStyle>
      <PolyStyle>
        <color>{color_hex}</color>
      </PolyStyle>
    </Style>
    <Placemark>
      <name>{incident_id} Origin ({state})</name>
      <Point>
        <coordinates>{center_lon:.6f},{center_lat:.6f},0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>{incident_id} Containment Buffer</name>
      <styleUrl>#firePerimeter</styleUrl>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
            {coords_str}
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
    return kml
