"""
maps_client.py: Google Maps API integration for AlloCare
Geocoding API: convert location text to lat/lng
Distance Matrix API: real-world driving distances for volunteer matching
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)

MAPS_API_KEY = os.environ.get("MAPS_API_KEY", "")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DISTANCE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# India bounding box for geocoding bias
INDIA_BOUNDS = "6.4,68.7|35.7,97.4"


def geocode_location(location_text: str) -> dict | None:
    """
    Convert location text to lat/lng using Google Geocoding API.
    Biased to India for better results.

    Args:
        location_text: e.g., "Dharavi, Mumbai, India"

    Returns:
        {"lat": float, "lng": float, "formatted_address": str} or None
    """
    if not location_text or not MAPS_API_KEY:
        return None

    try:
        resp = requests.get(GEOCODE_URL, params={
            "address": location_text,
            "region": "in",
            "bounds": INDIA_BOUNDS,
            "key": MAPS_API_KEY,
        }, timeout=5)

        data = resp.json()

        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            location = result["geometry"]["location"]
            return {
                "lat": location["lat"],
                "lng": location["lng"],
                "formatted_address": result.get("formatted_address", location_text),
            }
        else:
            logger.warning(f"[Geocode] No results for: {location_text} (status: {data.get('status')})")
            return None

    except Exception as e:
        logger.error(f"[Geocode] Error for {location_text}: {e}")
        return None


def get_distance_matrix(origins: list[tuple], destination: tuple, mode: str = "driving") -> list[float]:
    """
    Batch distance calculation using Google Distance Matrix API.

    Args:
        origins: list of (lat, lng) tuples for volunteers
        destination: (lat, lng) tuple for need location
        mode: 'driving' | 'walking'

    Returns:
        list of distances in km, one per origin. -1.0 for failures.
    """
    if not origins or not destination or not MAPS_API_KEY:
        return [-1.0] * len(origins)

    distances = []

    # Process in batches of 25 (API limit)
    for batch_start in range(0, len(origins), 25):
        batch = origins[batch_start:batch_start + 25]
        origins_str = "|".join([f"{lat},{lng}" for lat, lng in batch])
        dest_str = f"{destination[0]},{destination[1]}"

        try:
            resp = requests.get(DISTANCE_URL, params={
                "origins": origins_str,
                "destinations": dest_str,
                "mode": mode,
                "units": "metric",
                "key": MAPS_API_KEY,
            }, timeout=8)

            data = resp.json()

            if data.get("status") == "OK":
                for row in data.get("rows", []):
                    elements = row.get("elements", [{}])
                    if elements and elements[0].get("status") == "OK":
                        distances.append(elements[0]["distance"]["value"] / 1000.0)
                    else:
                        distances.append(-1.0)
            else:
                distances.extend([-1.0] * len(batch))

        except Exception as e:
            logger.error(f"[DistanceMatrix] Error: {e}")
            distances.extend([-1.0] * len(batch))

    return distances
