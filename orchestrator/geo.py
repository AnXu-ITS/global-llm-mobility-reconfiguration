"""
Geographic helpers for the ground--low-altitude co-simulation.

Canonical CRS exchange is EPSG:4326 / WGS84, coordinate order (lat, lon).
This module is the single source of truth for:
  - bbox computation from the canonical study area
  - Haversine distance (used by geographic alignment validation)

It intentionally avoids third-party geo libraries so it runs in any Python.
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

# WGS84 ellipsoid
_EARTH_RADIUS_M = 6371008.8  # mean radius (IUGG), meters


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two WGS84 (lat, lon) points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def meters_per_deg_lat(lat: float) -> float:
    """Meters per degree of latitude at a given latitude (WGS84)."""
    phi = math.radians(lat)
    return (
        111132.92
        - 559.82 * math.cos(2 * phi)
        + 1.175 * math.cos(4 * phi)
        - 0.0023 * math.cos(6 * phi)
    )


def meters_per_deg_lon(lat: float) -> float:
    """Meters per degree of longitude at a given latitude (WGS84)."""
    phi = math.radians(lat)
    return (
        111412.84 * math.cos(phi)
        - 93.5 * math.cos(3 * phi)
        + 0.118 * math.cos(5 * phi)
    )


def bbox_from_center(center_lat: float, center_lon: float,
                     width_km: float, height_km: float) -> Dict[str, float]:
    """Compute a WGS84 bounding box from a center point and km extent.

    Returns {'south','north','west','east'} in degrees.
    """
    half_h_m = height_km * 1000.0 / 2.0
    half_w_m = width_km * 1000.0 / 2.0
    dlat = half_h_m / meters_per_deg_lat(center_lat)
    dlon = half_w_m / meters_per_deg_lon(center_lat)
    return {
        "south": center_lat - dlat,
        "north": center_lat + dlat,
        "west": center_lon - dlon,
        "east": center_lon + dlon,
    }


def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing (deg, 0..360) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlmb = math.radians(lon2 - lon1)
    y = math.sin(dlmb) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlmb)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def destination(lat: float, lon: float, dist_m: float, brg_deg: float) -> Tuple[float, float]:
    """Destination point given start (lat, lon), distance (m) and bearing (deg)."""
    phi = math.radians(lat)
    lmb = math.radians(lon)
    theta = math.radians(brg_deg)
    delta = dist_m / _EARTH_RADIUS_M
    phi2 = math.asin(
        math.sin(phi) * math.cos(delta) + math.cos(phi) * math.sin(delta) * math.cos(theta)
    )
    lmb2 = lmb + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi),
        math.cos(delta) - math.sin(phi) * math.sin(phi2),
    )
    return math.degrees(phi2), (math.degrees(lmb2) + 540.0) % 360.0 - 180.0
