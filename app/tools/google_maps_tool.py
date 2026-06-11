import os
import googlemaps
from typing import List, Dict, Any, Optional

class GoogleMapsTool:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        self.client = googlemaps.Client(key=self.api_key) if self.api_key else None
        self.DEFAULT_RADIUS = 15000  # 15km for city-scale searches

    def _mock_response(self, place_type: str, location: str) -> List[Dict[str, Any]]:
        # Fallback if no API key is provided
        return [
            {
                "name": f"Mock {place_type.title()} near {location}",
                "vicinity": f"123 {location} Main St",
                "rating": 4.5,
                "types": [place_type]
            }
        ]

    def _find_places(self, location: str, place_type: str, radius: int = 5000) -> List[Dict[str, Any]]:
        if not self.client:
            return self._mock_response(place_type, location)
            
        try:
            # Geocode the location string to get lat/lng
            geocode_result = self.client.geocode(location)
            if not geocode_result:
                return []
                
            loc = geocode_result[0]['geometry']['location']
            
            # Find places nearby
            places_result = self.client.places_nearby(
                location=loc,
                radius=radius,
                type=place_type
            )
            
            return places_result.get('results', [])
        except Exception as e:
            print(f"Google Maps API error: {e}")
            return self._mock_response(place_type, location)

    def find_hospitals(self, location: str, radius: int = 15000) -> List[Dict[str, Any]]:
        """Find hospitals near a given location."""
        return self._find_places(location, "hospital", radius)

    def find_pharmacies(self, location: str, radius: int = 10000) -> List[Dict[str, Any]]:
        """Find pharmacies near a given location."""
        return self._find_places(location, "pharmacy", radius)

    def find_restaurants(self, location: str, radius: int = 5000) -> List[Dict[str, Any]]:
        """Find restaurants near a given location."""
        return self._find_places(location, "restaurant", radius)
