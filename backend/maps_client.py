"""
maps_client.py — Free geocoding using OpenStreetMap/Nominatim via geopy.
Replaces Google Maps Geocoding API (paid) and Distance Matrix API (paid).
No API key required.
"""
import math
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

logger = logging.getLogger(__name__)

# Initialize Nominatim geocoder (free, no API key)
_geocoder = Nominatim(user_agent="allocare-app/1.0", timeout=5)


def geocode_location(location_text: str) -> dict | None:
    """
    Convert location text to lat/lng using OpenStreetMap Nominatim.
    Biased to India for better results.

    Args:
        location_text: e.g., "Dharavi, Mumbai, India"

    Returns:
        {"lat": float, "lng": float, "formatted_address": str} or None
    """
    if not location_text:
        return None

    # Ensure India context
    if "india" not in location_text.lower():
        location_text += ", India"

    try:
        location = _geocoder.geocode(
            location_text,
            exactly_one=True,
            country_codes=["in"],  # Bias to India
        )

        if location:
            return {
                "lat": location.latitude,
                "lng": location.longitude,
                "formatted_address": location.address or location_text,
            }
        else:
            logger.warning(f"[Geocode] No results for: {location_text}")
            return None

    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        logger.warning(f"[Geocode] Service unavailable for {location_text}: {e}")
        return None
    except Exception as e:
        logger.error(f"[Geocode] Error for {location_text}: {e}")
        return None


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculates straight-line distance between two lat/lng points in km.
    Replaces Google Distance Matrix API (paid).
    """
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_distance_matrix(origins: list[tuple], destination: tuple, mode: str = "driving") -> list[float]:
    """
    Batch distance calculation using Haversine (free, no API needed).
    Returns approximate straight-line distances in km.

    Args:
        origins: list of (lat, lng) tuples for volunteers
        destination: (lat, lng) tuple for need location
        mode: ignored (Haversine is always straight-line)

    Returns:
        list of distances in km, one per origin.
    """
    if not origins or not destination:
        return [-1.0] * len(origins)

    distances = []
    for lat, lng in origins:
        try:
            dist = haversine_distance(lat, lng, destination[0], destination[1])
            # Multiply by 1.3 to approximate road distance from straight-line
            distances.append(round(dist * 1.3, 1))
        except Exception:
            distances.append(-1.0)

    return distances
