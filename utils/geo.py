from haversine import haversine, Unit
from geopy.geocoders import Nominatim
from config import Config
import time

# Cache para geocoding
_geocode_cache = {}

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en kilómetros entre dos puntos.
    Paradigma: Funcional.
    """
    try:
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 999.99
        return round(haversine((lat1, lon1), (lat2, lon2)), 2)
    except:
        return 999.99

def get_address_from_coords(lat, lng):
    """
    Obtiene una dirección legible a partir de coordenadas.
    """
    cache_key = f"{lat},{lng}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    
    try:
        geolocator = Nominatim(user_agent="smart_resto_app")
        time.sleep(1)  # Respetar límites de rate
        location = geolocator.reverse(f"{lat}, {lng}")
        address = location.address if location else "Dirección no encontrada"
        _geocode_cache[cache_key] = address
        return address
    except Exception as e:
        print(f"Error en geocoding: {e}")
        return "Servicio de geolocalización no disponible"