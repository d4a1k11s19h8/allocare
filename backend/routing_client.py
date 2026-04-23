"""
routing_client.py — Free routing using OSRM (Open Source Routing Machine).
No API key needed. Uses the public OSRM demo server.
Falls back to Haversine-based estimates if OSRM is unavailable.

Features:
- Real road distances and durations
- Route polylines for map display
- Batch routing for multiple volunteers
- Route quality scoring
"""
import math
import logging
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# OSRM public demo server (free, no key needed)
OSRM_BASE = "https://router.project-osrm.org"

# Cache for routes (simple in-memory)
_route_cache = {}
_CACHE_TTL = 300  # 5 minutes


def get_route(
    from_lat: float, from_lng: float,
    to_lat: float, to_lng: float,
    profile: str = "driving"
) -> dict:
    """
    Get a route between two points using OSRM.

    Args:
        from_lat, from_lng: Origin coordinates
        to_lat, to_lng: Destination coordinates
        profile: "driving", "walking", or "cycling"

    Returns:
        {
            "distance_km": float,
            "duration_min": float,
            "polyline": [[lat, lng], ...],  # For Leaflet
            "route_quality": float,  # 0-1 score
            "source": "osrm" or "haversine"
        }
    """
    # Check cache
    cache_key = f"{from_lat:.4f},{from_lng:.4f}-{to_lat:.4f},{to_lng:.4f}-{profile}"
    cached = _route_cache.get(cache_key)
    if cached and time.time() - cached["_time"] < _CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_time"}

    # Try OSRM
    try:
        import requests
        # OSRM uses lng,lat order
        url = f"{OSRM_BASE}/route/v1/{profile}/{from_lng},{from_lat};{to_lng},{to_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
            "alternatives": "false",
        }

        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                distance_m = route["distance"]
                duration_s = route["duration"]

                # Convert GeoJSON coordinates [lng, lat] to Leaflet [lat, lng]
                coords = route["geometry"]["coordinates"]
                polyline = [[c[1], c[0]] for c in coords]

                # Calculate route quality
                straight_line = _haversine(from_lat, from_lng, to_lat, to_lng)
                road_distance = distance_m / 1000
                detour_ratio = road_distance / max(straight_line, 0.1)

                # Good route: detour ratio < 1.5, penalize very winding routes
                if detour_ratio < 1.3:
                    quality = 1.0
                elif detour_ratio < 1.6:
                    quality = 0.85
                elif detour_ratio < 2.0:
                    quality = 0.7
                elif detour_ratio < 3.0:
                    quality = 0.5
                else:
                    quality = 0.3

                result = {
                    "distance_km": round(road_distance, 1),
                    "duration_min": round(duration_s / 60, 1),
                    "polyline": polyline,
                    "route_quality": round(quality, 2),
                    "source": "osrm",
                }

                # Cache it
                _route_cache[cache_key] = {**result, "_time": time.time()}
                return result

    except Exception as e:
        logger.warning(f"[Routing] OSRM failed, using Haversine fallback: {e}")

    # Fallback: Haversine estimate
    return _haversine_route(from_lat, from_lng, to_lat, to_lng)


def _haversine_route(from_lat, from_lng, to_lat, to_lng) -> dict:
    """Haversine-based route estimate when OSRM is unavailable."""
    straight_km = _haversine(from_lat, from_lng, to_lat, to_lng)
    road_km = straight_km * 1.4  # Road distance factor

    # Estimate duration: average 30 km/h in Indian urban, 50 km/h highway
    if road_km < 20:
        speed = 25  # Urban
    elif road_km < 100:
        speed = 40  # Mixed
    else:
        speed = 50  # Highway

    duration_min = (road_km / speed) * 60

    # Generate simple straight-line "polyline" for fallback display
    polyline = [
        [from_lat, from_lng],
        [to_lat, to_lng],
    ]

    return {
        "distance_km": round(road_km, 1),
        "duration_min": round(duration_min, 1),
        "polyline": polyline,
        "route_quality": 0.5,  # Unknown quality for Haversine
        "source": "haversine",
    }


def get_routes_batch(
    origins: list,
    dest_lat: float, dest_lng: float,
    profile: str = "driving",
    max_workers: int = 4
) -> list:
    """
    Batch routing for multiple origins to one destination.
    Uses thread pool for parallel OSRM requests.

    Args:
        origins: list of {"lat": float, "lng": float, "id": str}
        dest_lat, dest_lng: Destination coordinates
        profile: Routing profile
        max_workers: Max concurrent requests

    Returns:
        list of route dicts, each with an added "origin_id" field
    """
    results = []

    def fetch_route(origin):
        route = get_route(
            origin["lat"], origin["lng"],
            dest_lat, dest_lng,
            profile
        )
        route["origin_id"] = origin.get("id", "")
        return route

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_route, o): o for o in origins}
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                origin = futures[future]
                logger.error(f"[Routing] Batch route failed for {origin}: {e}")
                # Fallback for this origin
                fallback = _haversine_route(
                    origin["lat"], origin["lng"],
                    dest_lat, dest_lng
                )
                fallback["origin_id"] = origin.get("id", "")
                results.append(fallback)

    return results


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates straight-line distance between two lat/lng points in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
