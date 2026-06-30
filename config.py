import os

class Config:
    # --- CONFIGURACIÓN PERSONALIZABLE ---
    CIUDAD = "Trujillo"
    COORDENADAS_CENTRO = (-8.1118, -79.0287)
    RADIO_MAXIMO_KM = 10
    MONEDA = "S/."
    IDIOMA = "es"
    
    # --- DISTRITOS ---
    DISTRITOS = ["Trujillo", "Victor Larco", "La Esperanza", "Huanchaco", "Moche", "El Porvenir", "Florencia de Mora"]
    
    # --- PALETA DE COLORES ---
    PALETA_PRIMARIA = "#FF385C"
    PALETA_SECUNDARIA = "#008489"
    
    # --- TIPOGRAFÍA ---
    FUENTE_PRINCIPAL = "Inter"
    NOMBRE_APP = "SmartResto"
    
    # --- FLASK CONFIG ---
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-super-secret'
    DEBUG = True
    JSON_AS_ASCII = False

    # --- RUTAS DE DATOS ---
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    RESTAURANTS_FILE = os.path.join(DATA_DIR, 'restaurants.json')
    CATEGORIES_FILE = os.path.join(DATA_DIR, 'categories.json')
    USERS_FILE = os.path.join(DATA_DIR, 'users.json')
    DISHES_FILE = os.path.join(DATA_DIR, 'dishes.json')
    FAVORITES_FILE = os.path.join(DATA_DIR, 'favorites.json')
    HISTORY_FILE = os.path.join(DATA_DIR, 'history.json')
    PROMOTIONS_FILE = os.path.join(DATA_DIR, 'promotions.json')
    REVIEWS_FILE = os.path.join(DATA_DIR, 'reviews.json')
    NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')
    DAILY_MENU_FILE = os.path.join(DATA_DIR, 'daily_menu.json')
    MODERATION_FILE = os.path.join(DATA_DIR, 'moderation.json') 
    
    @classmethod
    def ensure_data_dir(cls):
        """Asegura que el directorio de datos existe"""
        if not os.path.exists(cls.DATA_DIR):
            os.makedirs(cls.DATA_DIR)