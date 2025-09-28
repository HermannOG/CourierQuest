import pygame
import json
import os
import time
import random
import requests
import hashlib
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from collections import deque
import pickle
import math

# Inicializar pygame
pygame.init()

# =============================================================================
# CONSTANTES Y CONFIGURACIÓN
# =============================================================================

# Constantes - VENTANA OPTIMIZADA PARA MEJOR VISUALIZACIÓN
WINDOW_WIDTH = 1800
WINDOW_HEIGHT = 1000
TILE_SIZE = 32
FPS = 144

# Colores mejorados para mejor contraste
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 200)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 200, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
LIGHT_GRAY = (192, 192, 192)
LIGHT_BLUE = (173, 216, 230)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
DARK_GREEN = (0, 150, 0)
DARK_RED = (150, 0, 0)
BRIGHT_GREEN = (50, 255, 50)
BRIGHT_YELLOW = (255, 255, 100)
BRIGHT_RED = (255, 100, 100)

# Colores para UI mejorada - MÁS CONTRASTADOS
UI_BACKGROUND = (245, 245, 250)
UI_BORDER = (70, 70, 120)
UI_HIGHLIGHT = (220, 230, 255)
UI_TEXT_HEADER = (25, 25, 90)
UI_TEXT_NORMAL = (40, 40, 70)
UI_TEXT_SECONDARY = (80, 80, 100)
UI_WARNING = (200, 100, 0)
UI_CRITICAL = (200, 50, 50)
UI_SUCCESS = (0, 150, 50)

# =============================================================================
# CLASES DE DATOS
# =============================================================================

@dataclass
class Position:
    """Representa una posición en la cuadrícula del juego."""
    x: int
    y: int

@dataclass
class Order:
    """Representa un pedido de entrega en el juego."""
    id: str
    pickup: Position
    dropoff: Position
    payout: int
    duration_minutes: float
    weight: int
    priority: int
    release_time: int
    status: str = "waiting_release"
    created_at: float = 0.0
    accepted_at: float = 0.0

@dataclass
class GameState:
    """Estado completo del juego para guardado/carga."""
    player_pos: Position
    stamina: float
    reputation: int
    money: int
    game_time: float
    weather_time: float
    current_weather: str
    weather_intensity: float
    inventory: List[Order]
    available_orders: List[Order]
    completed_orders: List[Order]
    goal: int
    delivery_streak: int
    pending_orders: List[Order]
    # CAMPOS CRÍTICOS PARA GUARDADO/CARGA CORRECTA
    city_width: int
    city_height: int
    tiles: List[List[str]]
    legend: Dict
    city_name: str
    max_game_time: float

# =============================================================================
# SISTEMA DE API MEJORADO
# =============================================================================

class TigerAPIManager:
    """Gestor de API mejorado con mejor manejo de errores."""
    
    def __init__(self, base_url="https://tigerds-api.kindflower-ccaf48b6.eastus.azurecontainerapps.io"):
        self.base_url = base_url
        self.cache_dir = "api_cache"
        self.data_dir = "data"
        self._ensure_directories()
        self.tile_images = {}
        self._load_tile_images()
    


    def _load_tile_images(self):
        """Carga las imágenes para tiles especiales."""
        try:
            # Cargar imagen de parque (tu archivo pixilart-drawing.png)
            park_image = pygame.image.load("pixilart-drawing.png")
            # Redimensionar la imagen al tamaño del tile
            self.tile_images["P"] = pygame.transform.scale(park_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de parque cargada correctamente desde pixilart-drawing.png")
            
            # Puedes agregar más imágenes para otros tipos de tiles
            # edificio_image = pygame.image.load("assets/images/building.png")
            # self.tile_images["B"] = pygame.transform.scale(edificio_image, (TILE_SIZE, TILE_SIZE))
            
        except FileNotFoundError as e:
            print(f"⚠️ No se pudo cargar imagen: {e}")
            print("📁 Asegúrate de que exista la carpeta 'assets/images/' con 'park.png'")
            # Crear una imagen de respaldo si no existe el archivo
            self._create_fallback_images()
        except Exception as e:
            print(f"❌ Error cargando imágenes: {e}")
            self._create_fallback_images()

    def _create_fallback_images(self):
        """Crea imágenes de respaldo si no se pueden cargar las originales."""
        # Crear una imagen simple de parque con pygame
        park_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
        park_surface.fill(GREEN)
        
        # Dibujar algunos "árboles" simples
        tree_color = (0, 100, 0)
        for i in range(3):
            for j in range(3):
                if (i + j) % 2 == 0:  # Patrón de tablero
                    tree_rect = pygame.Rect(
                        i * (TILE_SIZE // 3) + 2, 
                        j * (TILE_SIZE // 3) + 2, 
                        TILE_SIZE // 3 - 4, 
                        TILE_SIZE // 3 - 4
                    )
                    pygame.draw.ellipse(park_surface, tree_color, tree_rect)
        
        self.tile_images["P"] = park_surface
        print("✅ Imagen de respaldo para parque creada")


    def _ensure_directories(self):
        for directory in [self.cache_dir, self.data_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def make_request(self, endpoint, timeout=30):
        """Realiza una petición a la API con manejo de errores."""
        try:
            resp = requests.get(self.base_url + endpoint, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"❌ Error {resp.status_code} en {endpoint}")
                return None
        except Exception as e:
            print(f"❌ Error de conexión en {endpoint}: {e}")
            return None
    #draw_game_over_overlay
    def get_city_map(self) -> dict:
        """Obtiene el mapa de la ciudad desde la API real."""
        print("🚀 Obteniendo mapa de TigerCity desde API...")
        map_data = self.make_request("/city/map")
        
        if map_data and 'data' in map_data:
            # Convertir el formato de la API al formato que espera el juego
            api_data = map_data['data']
            game_map = {
                'width': api_data['width'],
                'height': api_data['height'],
                'tiles': api_data['tiles'],
                'legend': self._convert_legend(api_data['legend']),
                'goal': 3000,  # 🎯 META FORZADA: Siempre $3000 independiente de la API
                'city_name': api_data.get('city_name', 'TigerCity'),
                'max_time': api_data.get('max_time', 600),
                'version': api_data.get('version', '1.0')
            }
            
            # Guardar en caché
            self._save_to_cache("map.json", game_map)
            print(f"✅ Mapa cargado: {game_map['width']}x{game_map['height']} - {game_map['city_name']}")
            return game_map
        else:
            print("❌ No se pudo obtener el mapa de la API, usando datos locales...")
            return self._get_fallback_map()
    
    def get_city_jobs(self) -> list:
        """Obtiene los trabajos/pedidos desde la API real - MEJORADO PARA MÁS PEDIDOS."""
        print("🚀 Obteniendo trabajos de TigerCity desde API...")
        jobs_data = self.make_request("/city/jobs")
        
        if jobs_data:
            # Convertir el formato de la API al formato del juego
            orders = self._convert_jobs_to_orders(jobs_data)
            
            # IMPORTANTE: Si hay pocos pedidos, generar más para fluidez del juego
            if len(orders) < 25:
                print(f"⚠️ Solo {len(orders)} pedidos de API, generando adicionales para fluidez...")
                additional_orders = self._generate_additional_orders(25 - len(orders))
                orders.extend(additional_orders)
            
            # Guardar en caché
            self._save_to_cache("jobs.json", orders)
            print(f"✅ {len(orders)} pedidos cargados (API + generados para fluidez)")
            return orders
        else:
            print("❌ No se pudieron obtener los trabajos de la API, usando datos locales...")
            return self._get_fallback_orders()
    
    def _generate_additional_orders(self, count: int) -> list:
        """Genera pedidos adicionales para mantener la fluidez del juego - MEJORADO."""
        additional_orders = []
        
        for i in range(count):
            # Generar posiciones aleatorias válidas
            pickup_x = random.randint(1, 28)
            pickup_y = random.randint(1, 23)
            dropoff_x = random.randint(1, 28)
            dropoff_y = random.randint(1, 23)
            
            # Asegurar distancia mínima entre pickup y dropoff
            attempts = 0
            while abs(pickup_x - dropoff_x) + abs(pickup_y - dropoff_y) < 4 and attempts < 10:
                dropoff_x = random.randint(1, 28)
                dropoff_y = random.randint(1, 23)
                attempts += 1
            
            # 🚀 MEJORA: Duración MÁS CORTA para mayor dinamismo
            distance = abs(pickup_x - dropoff_x) + abs(pickup_y - dropoff_y)
            duration = max(1.5, min(4.5, distance * 0.25 + random.uniform(1.0, 2.0)))
            
            # 🚀 MEJORA: Release times MÁS FRECUENTES (aparecen más rápido)
            release_time = random.randint(0, 180)  # 0-3 minutos en lugar de 0-7.5 minutos
            
            # Crear el pedido adicional
            order = Order(
                id=f"GEN_{i+100:03d}",
                pickup=Position(pickup_x, pickup_y),
                dropoff=Position(dropoff_x, dropoff_y),
                payout=random.randint(120, 280),  # Pago ligeramente mayor por ser más urgente
                duration_minutes=duration,
                weight=random.randint(1, 4),
                priority=random.choices([0, 1, 2], weights=[50, 35, 15])[0],  # Más pedidos prioritarios
                release_time=release_time
            )
            additional_orders.append(order)
        
        return additional_orders
    
    def _convert_legend(self, api_legend: dict) -> dict:
        """Convierte la leyenda de la API al formato del juego."""
        game_legend = {}
        
        for tile_type, tile_info in api_legend.items():
            game_tile = {
                'name': tile_info['name'],
                'surface_weight': tile_info.get('surface_weight', 1.0)
            }
            
            if tile_info.get('blocked', False):
                game_tile['blocked'] = True
            
            # Agregar bonus de descanso para parques
            if tile_info['name'].lower() == 'park':
                game_tile['rest_bonus'] = 20.0
            
            game_legend[tile_type] = game_tile
        
        return game_legend
    
    def _convert_jobs_to_orders(self, jobs_data: dict) -> list:
        """Convierte los trabajos de la API a pedidos del juego."""
        orders = []
        
        # Extraer la lista de trabajos - MANEJO MEJORADO
        jobs_list = None
        
        try:
            if isinstance(jobs_data, dict):
                if 'data' in jobs_data and isinstance(jobs_data['data'], dict) and 'jobs' in jobs_data['data']:
                    jobs_list = jobs_data['data']['jobs']
                elif 'jobs' in jobs_data:
                    jobs_list = jobs_data['jobs']
                elif 'data' in jobs_data and isinstance(jobs_data['data'], list):
                    jobs_list = jobs_data['data']
            elif isinstance(jobs_data, list):
                jobs_list = jobs_data
            
            # Si no se pudo extraer una lista válida, crear datos de respaldo
            if not jobs_list or not isinstance(jobs_list, list):
                print("⚠️ Estructura de datos de trabajos inesperada, usando respaldo")
                return self._get_fallback_orders()
            
            # Procesar cada trabajo
            for i, job in enumerate(jobs_list):
                try:
                    # Manejar tanto objetos dict como strings
                    if isinstance(job, str):
                        # Si es un string, crear un trabajo básico
                        order_id = f"STR_{i:03d}"
                        payout = random.randint(100, 200)
                    elif isinstance(job, dict):
                        # Si es un dict, extraer datos
                        order_id = job.get('id', f"API_{i:03d}")
                        payout = job.get('salary', job.get('payout', random.randint(100, 200)))
                    else:
                        # Tipo no reconocido, saltar
                        continue
                    
                    # Asegurar que payout sea un entero
                    if isinstance(payout, str):
                        try:
                            payout = int(float(payout.replace('$', '').replace(',', '')))
                        except:
                            payout = random.randint(100, 200)
                    elif not isinstance(payout, int):
                        payout = random.randint(100, 200)
                    
                    # Generar posiciones aleatorias válidas
                    pickup_x = random.randint(1, 28)
                    pickup_y = random.randint(1, 23)
                    dropoff_x = random.randint(1, 28)
                    dropoff_y = random.randint(1, 23)
                    
                    # Asegurar distancia mínima entre pickup y dropoff
                    attempts = 0
                    while abs(pickup_x - dropoff_x) + abs(pickup_y - dropoff_y) < 5 and attempts < 10:
                        dropoff_x = random.randint(1, 28)
                        dropoff_y = random.randint(1, 23)
                        attempts += 1
                    
                    # 🚀 MEJORA EXTREMA: Duración ULTRA CORTA para máximo dinamismo (30 segundos!)
                    distance = abs(pickup_x - dropoff_x) + abs(pickup_y - dropoff_y)
                    duration = max(0.3, min(0.8, distance * 0.05 + random.uniform(0.2, 0.5)))  # 18-48 segundos
                    
                    # Crear el pedido
                    order = Order(
                        id=str(order_id),
                        pickup=Position(pickup_x, pickup_y),
                        dropoff=Position(dropoff_x, dropoff_y),
                        payout=int(payout),
                        duration_minutes=duration,  # Duración adaptada según prioridad
                        weight=random.randint(1, 3),  # Peso menor
                        priority=int(api_priority),  # Usar prioridad de la API
                        release_time=random.randint(0, 180)  # 🚀 MEJORA: Aparecen más rápido (0-3 min)
                    )
                    orders.append(order)
                    
                except Exception as e:
                    print(f"⚠️ Error procesando trabajo {i}: {e}")
                    # Crear un pedido de respaldo
                    fallback_order = Order(
                        id=f"FALLBACK_{i:03d}",
                        pickup=Position(random.randint(1, 28), random.randint(1, 23)),
                        dropoff=Position(random.randint(1, 28), random.randint(1, 23)),
                        payout=random.randint(100, 200),
                        duration_minutes=random.uniform(5.0, 10.0),
                        weight=random.randint(1, 4),
                        priority=random.randint(0, 2),
                        release_time=random.randint(0, 300)
                    )
                    orders.append(fallback_order)
                    continue
            
            # Si no se crearon pedidos, usar respaldo
            if not orders:
                print("⚠️ No se pudieron crear pedidos desde la API, usando respaldo completo")
                return self._get_fallback_orders()
            
            print(f"✅ {len(orders)} pedidos procesados correctamente desde API")
            return orders
            
        except Exception as e:
            print(f"❌ Error general convirtiendo trabajos: {e}")
            return self._get_fallback_orders()
    
    def _save_to_cache(self, filename: str, data: Any):
        """Guarda datos en la caché local."""
        try:
            cache_path = os.path.join(self.cache_dir, filename)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando en caché {filename}: {e}")
    
    def _load_from_cache(self, filename: str) -> Optional[Any]:
        """Carga datos desde la caché local."""
        try:
            cache_path = os.path.join(self.cache_dir, filename)
            if os.path.exists(cache_path):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error cargando de caché {filename}: {e}")
        return None
    
    def _get_fallback_map(self) -> dict:
        """Mapa de respaldo si la API falla."""
        fallback_map = self._load_from_cache("map.json")
        if fallback_map:
            return fallback_map
        
        # Crear un mapa básico de respaldo
        return {
            "width": 30,
            "height": 25,
            "tiles": [["C"] * 30 for _ in range(25)],
            "legend": {
                "C": {"name": "calle", "surface_weight": 1.00},
                "B": {"name": "edificio", "blocked": True},
                "P": {"name": "parque", "surface_weight": 0.95, "rest_bonus": 15.0}
            },
            "goal": 3000,  # 🎯 META FIJA: Siempre $3000 para consistencia
            "city_name": "TigerCity",
            "max_time": 600,
            "version": "1.0"
        }
    
    def _get_fallback_orders(self) -> list:
        """Pedidos de respaldo si la API falla - MÁS PEDIDOS PARA FLUIDEZ."""
        fallback_orders = self._load_from_cache("jobs.json")
        if fallback_orders:
            return fallback_orders
        
        # Crear pedidos básicos de respaldo - AUMENTADO A 35 PARA MÁS FLUIDEZ
        orders = []
        for i in range(35):  # 🚀 MEJORA: Más pedidos de respaldo
            pickup_x = random.randint(1, 28)
            pickup_y = random.randint(1, 23)
            dropoff_x = random.randint(1, 28)
            dropoff_y = random.randint(1, 23)
            
            # Asegurar distancia mínima
            while abs(pickup_x - dropoff_x) + abs(pickup_y - dropoff_y) < 4:
                dropoff_x = random.randint(1, 28)
                dropoff_y = random.randint(1, 23)
            
            # 🎯 SISTEMA PRIORITARIO: Adaptar duración según prioridad - EXTREMADAMENTE REDUCIDO
            priority = random.choices([0, 1, 2], weights=[40, 40, 20])[0]
            base_duration = random.uniform(5.0, 12.0)  # Duración base realista
            
            if priority >= 2:  # Alta prioridad
                duration = max(0.13, min(0.25, base_duration * 0.05))  # 5% - ULTRA URGENTE
            elif priority == 1:  # Media prioridad
                duration = max(0.17, min(0.30, base_duration * 0.07))  # 7% - MUY URGENTE
            else:  # Baja prioridad
                duration = max(0.20, min(0.37, base_duration * 0.09))  # 9% - URGENTE
            
            orders.append(Order(
                id=f"FALLBACK_{i:03d}",
                pickup=Position(pickup_x, pickup_y),
                dropoff=Position(dropoff_x, dropoff_y),
                payout=random.randint(150, 400) + (50 * priority),  # Más pago por prioridad
                duration_minutes=duration,
                weight=random.randint(1, 3),  # Peso menor para compensar urgencia
                priority=priority,
                release_time=random.randint(0, 180)  # 🚀 MEJORA: Liberación más frecuente
            ))
        
        return orders

# =============================================================================
# ALGORITMOS DE ORDENAMIENTO
# =============================================================================

class SortingAlgorithms:
    """Implementación de algoritmos de ordenamiento para el juego."""
    
    @staticmethod
    def quicksort_by_priority(orders: List[Order]) -> List[Order]:
        """Ordena pedidos por prioridad usando QuickSort."""
        if len(orders) <= 1:
            return orders.copy()
        
        pivot = orders[len(orders) // 2]
        left = [x for x in orders if x.priority > pivot.priority]
        middle = [x for x in orders if x.priority == pivot.priority]
        right = [x for x in orders if x.priority < pivot.priority]
        
        return (SortingAlgorithms.quicksort_by_priority(left) + 
                middle + 
                SortingAlgorithms.quicksort_by_priority(right))
    
    @staticmethod
    def mergesort_by_deadline(orders: List[Order], game_time: float) -> List[Order]:
        """Ordena pedidos por tiempo restante usando MergeSort."""
        if len(orders) <= 1:
            return orders.copy()
        
        mid = len(orders) // 2
        left = SortingAlgorithms.mergesort_by_deadline(orders[:mid], game_time)
        right = SortingAlgorithms.mergesort_by_deadline(orders[mid:], game_time)
        
        return SortingAlgorithms._merge_by_deadline(left, right, game_time)
    
    @staticmethod
    def _merge_by_deadline(left: List[Order], right: List[Order], game_time: float) -> List[Order]:
        """Función auxiliar para merge sort."""
        result = []
        i = j = 0
        
        def get_time_remaining(order):
            if order.status == "waiting_release":
                return order.duration_minutes * 60
            elapsed = game_time - order.created_at
            return max(0, order.duration_minutes * 60 - elapsed)
        
        while i < len(left) and j < len(right):
            if get_time_remaining(left[i]) <= get_time_remaining(right[j]):
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        
        result.extend(left[i:])
        result.extend(right[j:])
        return result
    
    @staticmethod
    def insertion_sort_by_distance(orders: List[Order], player_pos: Position) -> List[Order]:
        """Ordena pedidos por distancia usando Insertion Sort."""
        result = orders.copy()
        
        def manhattan_distance(order):
            return abs(order.pickup.x - player_pos.x) + abs(order.pickup.y - player_pos.y)
        
        for i in range(1, len(result)):
            key = result[i]
            key_distance = manhattan_distance(key)
            j = i - 1
            
            while j >= 0 and manhattan_distance(result[j]) > key_distance:
                result[j + 1] = result[j]
                j -= 1
            
            result[j + 1] = key
        
        return result

# =============================================================================
# ESTRUCTURAS DE DATOS OPTIMIZADAS
# =============================================================================

class OptimizedPriorityQueue:
    """Cola de prioridad optimizada usando inserción binaria."""
    
    def __init__(self):
        self.items = []
    
    def enqueue(self, item: Order):
        """Inserta un pedido manteniendo el orden por prioridad."""
        if not self.items:
            self.items.append(item)
            return
        
        left, right = 0, len(self.items)
        while left < right:
            mid = (left + right) // 2
            if self.items[mid].priority < item.priority:
                right = mid
            else:
                left = mid + 1
        
        self.items.insert(left, item)
    
    def dequeue(self) -> Optional[Order]:
        """Extrae el pedido de mayor prioridad."""
        return self.items.pop(0) if self.items else None
    
    def size(self) -> int:
        return len(self.items)
    
    def remove(self, order: Order) -> bool:
        try:
            self.items.remove(order)
            return True
        except ValueError:
            return False

class MemoryEfficientHistory:
    """Sistema de historial eficiente usando diferencias."""
    
    def __init__(self, max_size: int = 20):
        self.diffs = []
        self.max_size = max_size
        self.base_state = None
    
    def push(self, state: GameState):
        if self.base_state is None:
            self.base_state = state
            return
        
        diff = {}
        if (self.base_state.player_pos.x != state.player_pos.x or 
            self.base_state.player_pos.y != state.player_pos.y):
            diff['player_pos'] = (state.player_pos.x, state.player_pos.y)
        
        if abs(self.base_state.stamina - state.stamina) > 1.0:
            diff['stamina'] = state.stamina
        
        if self.base_state.money != state.money:
            diff['money'] = state.money
            
        if self.base_state.reputation != state.reputation:
            diff['reputation'] = state.reputation
        
        if diff:
            self.diffs.append(diff)
            if len(self.diffs) >= self.max_size:
                self.diffs.pop(0)
    
    def pop(self) -> Optional[GameState]:
        if not self.diffs:
            return None
        
        diff = self.diffs.pop()
        new_state = GameState(
            player_pos=Position(
                diff.get('player_pos', (self.base_state.player_pos.x, self.base_state.player_pos.y))[0],
                diff.get('player_pos', (self.base_state.player_pos.x, self.base_state.player_pos.y))[1]
            ),
            stamina=diff.get('stamina', self.base_state.stamina),
            reputation=diff.get('reputation', self.base_state.reputation),
            money=diff.get('money', self.base_state.money),
            game_time=self.base_state.game_time,
            weather_time=self.base_state.weather_time,
            current_weather=self.base_state.current_weather,
            weather_intensity=self.base_state.weather_intensity,
            inventory=list(self.base_state.inventory),
            available_orders=list(self.base_state.available_orders),
            completed_orders=list(self.base_state.completed_orders),
            goal=self.base_state.goal,
            delivery_streak=0,
            pending_orders=list(getattr(self.base_state, 'pending_orders', [])),
            # Campos para guardado/carga correcta
            city_width=getattr(self.base_state, 'city_width', 30),
            city_height=getattr(self.base_state, 'city_height', 25),
            tiles=getattr(self.base_state, 'tiles', []),
            legend=getattr(self.base_state, 'legend', {}),
            city_name=getattr(self.base_state, 'city_name', 'TigerCity'),
            max_game_time=getattr(self.base_state, 'max_game_time', 600.0)
        )
        return new_state
    
    def size(self) -> int:
        return len(self.diffs)

# =============================================================================
# SISTEMA DE CLIMA
# =============================================================================

class EnhancedWeatherSystem:
    """Sistema de clima dinámico basado en cadenas de Markov."""
    
    TRANSITION_MATRIX = {
        'clear': {'clear': 0.4, 'clouds': 0.3, 'wind': 0.2, 'heat': 0.1},
        'clouds': {'clear': 0.2, 'clouds': 0.3, 'rain_light': 0.3, 'fog': 0.2},
        'rain_light': {'clouds': 0.3, 'rain_light': 0.2, 'rain': 0.3, 'clear': 0.2},
        'rain': {'rain_light': 0.3, 'rain': 0.2, 'storm': 0.2, 'clouds': 0.3},
        'storm': {'rain': 0.4, 'storm': 0.2, 'clouds': 0.4},
        'fog': {'fog': 0.3, 'clouds': 0.4, 'clear': 0.3},
        'wind': {'wind': 0.2, 'clear': 0.3, 'clouds': 0.3, 'cold': 0.2},
        'heat': {'heat': 0.3, 'clear': 0.4, 'clouds': 0.3},
        'cold': {'cold': 0.3, 'clear': 0.2, 'clouds': 0.3, 'wind': 0.2}
    }
    
    SPEED_MULTIPLIERS = {
        'clear': 1.00, 'clouds': 0.98, 'rain_light': 0.90, 'rain': 0.85,
        'storm': 0.75, 'fog': 0.88, 'wind': 0.92, 'heat': 0.90, 'cold': 0.92
    }
    
    STAMINA_PENALTIES = {
        'clear': 0.0, 'clouds': 0.0, 'rain_light': 0.05, 'rain': 0.1,
        'storm': 0.3, 'fog': 0.0, 'wind': 0.1, 'heat': 0.2, 'cold': 0.05
    }
    
    WEATHER_COLORS = {
        'clear': (200, 150, 100), 'clouds': (180, 180, 180),
        'rain_light': (100, 150, 200), 'rain': (70, 120, 180),
        'storm': (50, 50, 100), 'fog': (200, 200, 200),
        'wind': (150, 200, 150), 'heat': (255, 100, 100),
        'cold': (150, 200, 255)
    }
    
    def __init__(self):
        self.current_condition = 'clear'
        self.current_intensity = 0.5
        self.time_in_current = 0
        self.burst_duration = 30
        self.weather_memory = deque(maxlen=5)
        self.transitioning = False
        self.transition_start_time = 0
        self.transition_duration = 3.0
        self.previous_condition = 'clear'
        self.previous_intensity = 0.5
        self.target_condition = 'clear'
        self.target_intensity = 0.5
        self.weather_notifications = []
        self.notification_timer = 0
    
    def update(self, dt: float):
        self.time_in_current += dt
        self.notification_timer += dt
        self.weather_notifications = [
            (msg, time_left - dt) for msg, time_left in self.weather_notifications 
            if time_left - dt > 0
        ]
        
        if self.transitioning:
            elapsed_transition = time.time() - self.transition_start_time
            progress = min(1.0, elapsed_transition / self.transition_duration)
            smooth_progress = (1 - math.cos(progress * math.pi)) / 2
            self.current_intensity = self.previous_intensity + (self.target_intensity - self.previous_intensity) * smooth_progress
            
            if progress >= 1.0:
                self.transitioning = False
                self.current_condition = self.target_condition
                self.current_intensity = self.target_intensity
                effect_desc = self._get_weather_effect_description()
                self.weather_notifications.append((f"🌦️ {self.get_weather_description()} - {effect_desc}", 4.0))
        
        if self.time_in_current >= self.burst_duration and not self.transitioning:
            self._initiate_weather_change()
    
    def _initiate_weather_change(self):
        transitions = self.TRANSITION_MATRIX.get(self.current_condition, {'clear': 1.0})
        conditions = list(transitions.keys())
        weights = list(transitions.values())
        
        new_condition = random.choices(conditions, weights=weights)[0]
        new_intensity = random.uniform(0.4, 0.9)
        
        self.transitioning = True
        self.transition_start_time = time.time()
        self.previous_condition = self.current_condition
        self.previous_intensity = self.current_intensity
        self.target_condition = new_condition
        self.target_intensity = new_intensity
        
        self.time_in_current = 0
        self.burst_duration = random.randint(25, 40)
        self.weather_memory.append(new_condition)
        
        transition_desc = f"Cambiando de {self._get_condition_name(self.previous_condition)} a {self._get_condition_name(new_condition)}"
        self.weather_notifications.append((f"⚡ {transition_desc}", 3.0))
    
    def _get_condition_name(self, condition: str) -> str:
        names = {
            'clear': 'Despejado', 'clouds': 'Nublado', 'rain_light': 'Llovizna',
            'rain': 'Lluvia', 'storm': 'Tormenta', 'fog': 'Niebla',
            'wind': 'Viento', 'heat': 'Calor', 'cold': 'Frío'
        }
        return names.get(condition, condition)
    
    def _get_weather_effect_description(self) -> str:
        speed_mult = self.get_speed_multiplier()
        stamina_penalty = self.get_stamina_penalty()
        
        if speed_mult < 0.8:
            speed_desc = "Velocidad muy reducida"
        elif speed_mult < 0.9:
            speed_desc = "Velocidad reducida"
        elif speed_mult < 0.95:
            speed_desc = "Velocidad ligeramente reducida"
        else:
            speed_desc = "Velocidad normal"
        
        if stamina_penalty > 0.2:
            stamina_desc = "Resistencia se agota muy rápido"
        elif stamina_penalty > 0.1:
            stamina_desc = "Resistencia se agota más rápido"
        elif stamina_penalty > 0.05:
            stamina_desc = "Resistencia se agota un poco más rápido"
        else:
            stamina_desc = "Resistencia normal"
        
        return f"{speed_desc} | {stamina_desc}"
    
    def get_speed_multiplier(self) -> float:
        if self.transitioning:
            elapsed_transition = time.time() - self.transition_start_time
            progress = min(1.0, elapsed_transition / self.transition_duration)
            smooth_progress = (1 - math.cos(progress * math.pi)) / 2
            prev_mult = self.SPEED_MULTIPLIERS[self.previous_condition]
            target_mult = self.SPEED_MULTIPLIERS[self.target_condition]
            base_mult = prev_mult + (target_mult - prev_mult) * smooth_progress
        else:
            base_mult = self.SPEED_MULTIPLIERS[self.current_condition]
        
        return base_mult * (1.0 - (self.current_intensity * 0.2))
    
    def get_stamina_penalty(self) -> float:
        if self.transitioning:
            elapsed_transition = time.time() - self.transition_start_time
            progress = min(1.0, elapsed_transition / self.transition_duration)
            smooth_progress = (1 - math.cos(progress * math.pi)) / 2
            prev_penalty = self.STAMINA_PENALTIES[self.previous_condition]
            target_penalty = self.STAMINA_PENALTIES[self.target_condition]
            base_penalty = prev_penalty + (target_penalty - prev_penalty) * smooth_progress
        else:
            base_penalty = self.STAMINA_PENALTIES[self.current_condition]
        
        return base_penalty * self.current_intensity
    
    def get_weather_description(self) -> str:
        condition_to_use = self.target_condition if self.transitioning else self.current_condition
        base_desc = self._get_condition_name(condition_to_use)
        
        if self.transitioning:
            base_desc += " (Cambiando)"
        
        if self.current_intensity >= 0.8:
            return f"{base_desc} (Intenso)"
        elif self.current_intensity >= 0.6:
            return f"{base_desc} (Moderado)"
        else:
            return f"{base_desc} (Leve)"
    
    def get_weather_color(self) -> tuple:
        condition_to_use = self.target_condition if self.transitioning else self.current_condition
        return self.WEATHER_COLORS.get(condition_to_use, WHITE)

# =============================================================================
# SISTEMA DE ARCHIVOS MEJORADO
# =============================================================================

class RobustFileManager:
    """Gestor robusto de archivos con validación y backups."""
    
    def __init__(self):
        self._ensure_directory_structure()
    
    def _ensure_directory_structure(self):
        directories = ['data', 'saves', 'api_cache', 'backups']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def save_game_with_validation(self, game_state: GameState, slot: int = 1) -> bool:
        """GUARDADO CORREGIDO - Incluye todos los datos del mapa."""
        try:
            save_file = f"saves/slot{slot}.sav"
            
            save_data = {
                'version': '3.1_map_fixed',
                'timestamp': time.time(),
                'game_state': game_state,
                'metadata': {
                    'saved_at': datetime.now().isoformat(),
                    'game_time': game_state.game_time,
                    'player_position': (game_state.player_pos.x, game_state.player_pos.y),
                    'completion_percentage': (game_state.money / game_state.goal) * 100,
                    'city_info': f"{game_state.city_name} ({game_state.city_width}x{game_state.city_height})"
                }
            }
            
            with open(save_file, 'wb') as f:
                pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"✅ Juego guardado en slot {slot} - {game_state.city_name} {game_state.city_width}x{game_state.city_height}")
            return True
                
        except Exception as e:
            print(f"❌ Error saving game: {e}")
            return False
        
    def load_scores(self) -> list:
        """ Carga los puntajes desde el archivo JSON."""
        scores_file = "data/puntajes.json"
        
        try:
            # Asegurar que el directorio existe
            os.makedirs("data", exist_ok=True)
            
            # Si el archivo no existe, crearlo vacío
            if not os.path.exists(scores_file):
                with open(scores_file, 'w') as f:
                    json.dump([], f)
                return []
            
            # Cargar los puntajes existentes
            with open(scores_file, 'r') as f:
                scores = json.load(f)
                
            # Validar que sea una lista
            if not isinstance(scores, list):
                print(" Archivo de puntajes corrupto, creando nuevo")
                return []
                
            # Ordenar por puntaje descendente
            scores.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return scores
            
        except json.JSONDecodeError:
            print(" Error leyendo archivo de puntajes, creando nuevo")
            try:
                with open(scores_file, 'w') as f:
                    json.dump([], f)
            except:
                pass
            return []
        except Exception as e:
            print(f" Error cargando puntajes: {e}")
            return []
    
    def load_game_with_validation(self, slot: int = 1) -> Optional[GameState]:
        """CARGA CORREGIDA - Valida datos del mapa."""
        save_file = f"saves/slot{slot}.sav"
        
        if not os.path.exists(save_file):
            return None
            
        try:
            with open(save_file, 'rb') as f:
                save_data = pickle.load(f)
            
            if not isinstance(save_data, dict):
                return None
            
            game_state = save_data['game_state']
            
            # VALIDAR que el estado tiene los campos críticos del mapa
            if not hasattr(game_state, 'city_width') or not hasattr(game_state, 'city_height'):
                print("⚠️ Estado guardado antiguo sin datos de mapa completos")
                return None
            
            print(f"✅ Juego cargado desde slot {slot} - {game_state.city_name} {game_state.city_width}x{game_state.city_height}")
            return game_state
                
        except Exception as e:
            print(f"❌ Error loading from {save_file}: {e}")
            return None
    
    def get_save_info(self, slot: int) -> Optional[dict]:
        save_file = f"saves/slot{slot}.sav"
        
        if not os.path.exists(save_file):
            return None
        
        try:
            with open(save_file, 'rb') as f:
                save_data = pickle.load(f)
            
            if 'metadata' in save_data:
                return save_data['metadata']
        except:
            return None
        return None

# =============================================================================
# SISTEMA DE MENÚS
# =============================================================================

class GameMenu:
    """Sistema de menús del juego."""
    
    def __init__(self):
        self.state = "main_menu"
        self.main_options = ["Nuevo Juego", "Cargar Partida", "Tutorial", "Ver Puntajes", "Salir"]
        self.selected = 0
        self.file_manager = RobustFileManager()
        
        self.title_font = pygame.font.Font(None, 48)
        self.menu_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
    
    def handle_menu_input(self, event) -> Optional[str]:
        if event.type == pygame.KEYDOWN:
            if self.state == "main_menu":
                return self._handle_main_menu_input(event)
            elif self.state == "load_menu":
                return self._handle_load_menu_input(event)
            elif self.state == "scores_menu":  # ✅ NUEVA línea agregada
                return self._handle_scores_menu_input(event)  # ✅ NUEVA línea
        return None
    

    def _handle_scores_menu_input(self, event) -> Optional[str]:
        """✅ NUEVO: Manejo de menú de puntajes."""
        if event.key == pygame.K_b or event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
            self.state = "main_menu"
            self.selected = 3  # Volver a "Ver Puntajes"
        return None
    
    def _handle_main_menu_input(self, event) -> Optional[str]:
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.main_options)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.main_options)
        elif event.key == pygame.K_RETURN:
            option = self.main_options[self.selected]
            if option == "Nuevo Juego":
                return "start_new_game"
            elif option == "Cargar Partida":
                self.state = "load_menu"
                self.selected = 0
            elif option == "Tutorial":
                return "start_tutorial"
            elif option == "Ver Puntajes":
                self.state = "scores_menu"
                self.selected = 0 
            elif option == "Salir":
                return "exit"
        elif event.key == pygame.K_ESCAPE:
            return "exit"
        return None
    
    def _handle_load_menu_input(self, event) -> Optional[str]:
        # ✅ CORREGIDO: Solo mostrar 1 slot + opción volver
        if event.key == pygame.K_UP:
            self.selected = max(0, self.selected - 1)
        elif event.key == pygame.K_DOWN:
            self.selected = min(1, self.selected + 1)  # Solo 2 opciones: slot 1 + volver
        elif event.key == pygame.K_RETURN:
            if self.selected == 1:  # Volver
                self.state = "main_menu"
                self.selected = 1
            else:  # Slot 1
                return "load_slot_1"
        elif event.key == pygame.K_b or event.key == pygame.K_ESCAPE:  # ✅ TECLA B para volver
            self.state = "main_menu"
            self.selected = 1
        return None
    
    def draw(self, screen):
        screen.fill((20, 25, 40))
        
        if self.state == "main_menu":
            self._draw_main_menu(screen)
        elif self.state == "load_menu":
            self._draw_load_menu(screen)
        elif self.state == "scores_menu":  # ✅ NUEVA línea agregada
            self._draw_scores_menu(screen)



    def _draw_scores_menu(self, screen):
        """✅ NUEVO: Pantalla de puntajes."""
        title = self.title_font.render("TABLA DE PUNTAJES", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 80))
        screen.blit(title, title_rect)
        
        scores = self.file_manager.load_scores()
        
        if not scores:
            no_scores_text = self.menu_font.render("No hay puntajes registrados", True, (150, 150, 150))
            text_rect = no_scores_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2))
            screen.blit(no_scores_text, text_rect)
        else:
            # Mostrar los primeros 10 puntajes
            start_y = 150
            headers = ["#", "Puntaje", "Dinero", "Rep.", "Pedidos", "Fecha", "Estado"]
            header_positions = [100, 200, 320, 420, 520, 650, 850]
            
            # Dibujar encabezados
            for i, header in enumerate(headers):
                header_text = self.menu_font.render(header, True, (200, 200, 255))
                screen.blit(header_text, (header_positions[i], start_y))
            
            # Línea separadora
            pygame.draw.line(screen, (100, 100, 150), (80, start_y + 35), (WINDOW_WIDTH - 80, start_y + 35), 2)
            
            # Mostrar puntajes
            for i, score in enumerate(scores[:10]):
                y_pos = start_y + 50 + i * 35
                rank_color = (255, 215, 0) if i == 0 else (192, 192, 192) if i == 1 else (205, 127, 50) if i == 2 else (255, 255, 255)
                
                # Número de ranking
                rank_text = self.small_font.render(f"{i+1}", True, rank_color)
                screen.blit(rank_text, (header_positions[0], y_pos))
                
                # Puntaje
                score_text = self.small_font.render(f"{score.get('score', 0)}", True, rank_color)
                screen.blit(score_text, (header_positions[1], y_pos))
                
                # Dinero
                money_text = self.small_font.render(f"${score.get('money', 0)}", True, (100, 255, 100))
                screen.blit(money_text, (header_positions[2], y_pos))
                
                # Reputación
                rep = score.get('reputation', 0)
                rep_color = (100, 255, 100) if rep >= 80 else (255, 255, 100) if rep >= 50 else (255, 100, 100)
                rep_text = self.small_font.render(f"{rep}", True, rep_color)
                screen.blit(rep_text, (header_positions[3], y_pos))
                
                # Pedidos completados
                orders_text = self.small_font.render(f"{score.get('completed_orders', 0)}", True, (150, 200, 255))
                screen.blit(orders_text, (header_positions[4], y_pos))
                
                # Fecha (solo día y hora)
                date_str = score.get('date', '')[:16].replace('T', ' ')
                date_text = self.small_font.render(date_str, True, (150, 150, 150))
                screen.blit(date_text, (header_positions[5], y_pos))
                
                # Estado (Victoria/Derrota)
                victory = score.get('victory', False)
                status_text = "VICTORIA" if victory else "DERROTA"
                status_color = (100, 255, 100) if victory else (255, 100, 100)
                status_surface = self.small_font.render(status_text, True, status_color)
                screen.blit(status_surface, (header_positions[6], y_pos))
    
        # Instrucciones para volver
        back_text = self.small_font.render("Presiona B, ESC o ENTER para volver al menú principal", True, (150, 150, 150))
        back_rect = back_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        screen.blit(back_text, back_rect)
    
    def _draw_main_menu(self, screen):
        title = self.title_font.render("COURIER QUEST", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        screen.blit(title, title_rect)
        
        subtitle = self.menu_font.render("API REAL INTEGRADA - EIF-207", True, (100, 255, 100))
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 200))
        screen.blit(subtitle, subtitle_rect)
        
        start_y = 300
        for i, option in enumerate(self.main_options):
            color = (255, 255, 100) if i == self.selected else (255, 255, 255)
            text = self.menu_font.render(option, True, color)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, start_y + i * 50))
            
            if i == self.selected:
                pygame.draw.rect(screen, (50, 50, 100), 
                               (text_rect.x - 20, text_rect.y - 5, text_rect.width + 40, text_rect.height + 10))
            
            screen.blit(text, text_rect)
        
        instructions = self.small_font.render("Usa ↑↓ para navegar, ENTER para seleccionar", True, (150, 150, 150))
        instructions_rect = instructions.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT - 50))
        screen.blit(instructions, instructions_rect)
    
    def _draw_load_menu(self, screen):
        """✅ CORREGIDO: Solo mostrar 1 slot."""
        title = self.title_font.render("CARGAR PARTIDA", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 100))
        screen.blit(title, title_rect)
        
        start_y = 250
        
        # Solo mostrar Slot 1
        slot_info = self.file_manager.get_save_info(1)
        
        if self.selected == 0:
            color = (255, 255, 100)
            bg_color = (50, 50, 100)
        elif slot_info:
            color = (255, 255, 255)
            bg_color = (30, 30, 50)
        else:
            color = (100, 100, 100)
            bg_color = (20, 20, 30)
        
        slot_rect = pygame.Rect(WINDOW_WIDTH // 2 - 300, start_y - 5, 600, 70)
        pygame.draw.rect(screen, bg_color, slot_rect)
        pygame.draw.rect(screen, color, slot_rect, 2)
        
        if slot_info:
            slot_text = f"Slot 1 - {slot_info.get('saved_at', 'Desconocido')[:19]}"
            progress_text = f"Progreso: {slot_info.get('completion_percentage', 0):.1f}%"
            city_text = slot_info.get('city_info', 'Ciudad desconocida')
            
            slot_label = self.menu_font.render(slot_text, True, color)
            progress_label = self.small_font.render(progress_text, True, color)
            city_label = self.small_font.render(city_text, True, color)
            
            screen.blit(slot_label, (WINDOW_WIDTH // 2 - 280, start_y))
            screen.blit(progress_label, (WINDOW_WIDTH // 2 - 280, start_y + 25))
            screen.blit(city_label, (WINDOW_WIDTH // 2 - 280, start_y + 45))
        else:
            empty_text = "Slot 1 - Vacío"
            empty_label = self.menu_font.render(empty_text, True, color)
            screen.blit(empty_label, (WINDOW_WIDTH // 2 - 280, start_y + 20))
        
        # ✅ Opción volver con tecla B
        volver_color = (255, 255, 100) if self.selected == 1 else (255, 255, 255)
        volver_text = self.menu_font.render("← Volver al menú principal (B)", True, volver_color)
        volver_rect = volver_text.get_rect(center=(WINDOW_WIDTH // 2, start_y + 120))
        
        if self.selected == 1:
            pygame.draw.rect(screen, (50, 50, 100), 
                        (volver_rect.x - 20, volver_rect.y - 5, volver_rect.width + 40, volver_rect.height + 10))
        
        screen.blit(volver_text, volver_rect)

# =============================================================================
# SISTEMA DE TUTORIAL
# =============================================================================

class TutorialSystem:
    """Sistema de tutorial integrado."""
    
    def __init__(self):
        self.tutorial_steps = [
            {
                "title": "Bienvenido a Courier Quest",
                "message": "Eres un repartidor en bicicleta conectado a la API real de TigerCity. Tu objetivo es ganar $3000 antes de que termine la jornada laboral.",
                "keys": ["ENTER para continuar"]
            },
            {
                "title": "Movimiento Básico", 
                "message": "Usa WASD o las flechas para moverte por la ciudad. Solo puedes moverte por calles (grises) y parques. Los edificios están bloqueados.",
                "keys": ["WASD o ↑↓←→ para moverse", "ENTER para continuar"]
            },
            {
                "title": "Resistencia y Estados",
                "message": "Tu resistencia (0-100) baja al moverte. Si llega a 0, quedas exhausto. Recupera hasta 30 para moverte de nuevo. Los parques te ayudan a recuperar más rápido.",
                "keys": ["Resistencia >30: Normal", "10-30: Cansado (x0.8 velocidad)", "≤0: Exhausto (no te mueves)"]
            },
            {
                "title": "Gestión de Pedidos",
                "message": "Presiona O para ver pedidos disponibles, I para inventario. Usa E en puntos de recogida y entrega. Los pedidos NO aparecen en edificios bloqueados.",
                "keys": ["O: Ver pedidos", "I: Inventario", "E: Interactuar", "ENTER para continuar"]
            },
            {
                "title": "Algoritmos de Ordenamiento",
                "message": "Usa algoritmos para organizar pedidos: P (QuickSort por prioridad), T (MergeSort por tiempo), D (Insertion Sort por distancia).",
                "keys": ["P: Ordenar por prioridad", "T: Ordenar por tiempo", "D: Ordenar por distancia", "ENTER para comenzar"]
            }
        ]
        
        self.current_step = 0
        self.tutorial_active = True
        self.font = pygame.font.Font(None, 28)
        self.title_font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 20)
    
    def handle_input(self, event) -> bool:
        if not self.tutorial_active:
            return False
            
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.current_step += 1
            if self.current_step >= len(self.tutorial_steps):
                self.tutorial_active = False
                return False
        
        return True
    
    def draw(self, screen):
        if not self.tutorial_active or self.current_step >= len(self.tutorial_steps):
            return
        
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
        
        step = self.tutorial_steps[self.current_step]
        
        panel_width = 900
        panel_height = 500
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        panel_y = (WINDOW_HEIGHT - panel_height) // 2
        
        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(screen, (40, 50, 70), panel_rect, border_radius=15)
        pygame.draw.rect(screen, (100, 150, 200), panel_rect, 3, border_radius=15)
        
        title = self.title_font.render(step["title"], True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, panel_y + 50))
        screen.blit(title, title_rect)
        
        self._draw_wrapped_text(screen, step["message"], 
                               panel_x + 40, panel_y + 100, 
                               panel_width - 80, self.font, (220, 220, 220))
        
        controls_y = panel_y + panel_height - 150
        for i, key_info in enumerate(step["keys"]):
            key_text = self.small_font.render(f"• {key_info}", True, (150, 200, 255))
            screen.blit(key_text, (panel_x + 40, controls_y + i * 25))
        
        progress_text = f"Paso {self.current_step + 1} de {len(self.tutorial_steps)}"
        progress = self.small_font.render(progress_text, True, (150, 150, 150))
        progress_rect = progress.get_rect(center=(WINDOW_WIDTH // 2, panel_y + panel_height - 20))
        screen.blit(progress, progress_rect)
    
    def _draw_wrapped_text(self, surface, text, x, y, max_width, font, color):
        words = text.split(' ')
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        for i, line in enumerate(lines):
            line_surface = font.render(line, True, color)
            surface.blit(line_surface, (x, y + i * (font.get_height() + 5)))
    
    def is_active(self) -> bool:
        return self.tutorial_active

# =============================================================================
# CLASE PRINCIPAL DEL JUEGO CORREGIDA
# =============================================================================

class CourierQuest:
    """Clase principal del juego Courier Quest - VERSIÓN CON IMÁGENES."""
    
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Courier Quest - Versión con Imágenes")
        self.clock = pygame.time.Clock()
        
        # Fuentes optimizadas
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        self.large_font = pygame.font.Font(None, 32)
        self.title_font = pygame.font.Font(None, 38)
        self.header_font = pygame.font.Font(None, 28)

        # ✅ MODIFICADO: Sistema de imágenes para tiles, clima Y JUGADOR
        self.tile_images = {}
        self.weather_images = {}
        self.player_image = None  # ← NUEVA LÍNEA AGREGADA

        # Sistemas del juego (mantener todo lo existente)
        self.api_manager = TigerAPIManager()
        self.weather_system = EnhancedWeatherSystem()
        self.history = MemoryEfficientHistory()
        self.file_manager = RobustFileManager()
        self.sorting_algorithms = SortingAlgorithms()
        self.menu_system = GameMenu()
        self.tutorial_system = TutorialSystem()

        # Estados del juego (mantener todo lo existente)
        self.game_state = "menu"
        self.running = True
        self.paused = False
        self.game_over = False
        self.victory = False

        # Datos del mundo - DESDE API REAL CON CORRECCIONES
        self.map_data = {}
        self.city_width = 30
        self.city_height = 25
        self.tiles = []
        self.legend = {}
        self.goal = 3000
        self.city_name = "TigerCity"
        self.max_game_time = 600.0

        # POSICIÓN DEL MAPA CORREGIDA
        self.map_offset_x = 20
        self.map_offset_y = 35
        self.map_pixel_width = self.city_width * TILE_SIZE
        self.map_pixel_height = self.city_height * TILE_SIZE

        # Estado del jugador (mantener todo lo existente)
        self.player_pos = Position(2, 2)
        self.stamina = 100.0        
        self.max_stamina = 100.0      
        self.reputation = 70
        self.money = 0
        self.max_weight = 10
        self.base_speed = 3.0

        # Tiempo del juego
        self.game_time = 0.0

        # Gestión de pedidos - ESTRUCTURAS DE DATOS CORRECTAS
        self.pending_orders = deque()
        self.available_orders = OptimizedPriorityQueue()
        self.inventory = deque()
        self.completed_orders = []

        # Estadísticas
        self.delivery_streak = 0
        self.last_delivery_was_clean = True

        # Interfaz de usuario
        self.show_inventory = False
        self.show_orders = False
        self.selected_order_index = 0
        self.selected_inventory_index = 0

        # Control de movimiento
        self.move_cooldown = 0.08
        self.last_move_time = 0

        # Mensajes del juego
        self.game_messages = []
        self.message_timer = 0

        # Métricas de rendimiento
        self.fps_counter = 0
        self.fps_timer = 0
        self.current_fps = 60

        # ✅ MODIFICADO: Cargar imágenes de tiles, clima Y JUGADOR
        self._load_tile_images()
        self._load_weather_images()
        self._load_player_image()  # ← NUEVA LÍNEA AGREGADA
        
        self._ensure_data_files()
        print("🎮 Courier Quest inicializado - VERSIÓN CON IMÁGENES COMPLETAS + JUGADOR")



    def _load_player_image(self):
        """✅ NUEVO: Carga la imagen del jugador/repartidor."""
        try:
            # Cargar imagen del repartidor
            player_image = pygame.image.load("Repartidor.png")
            # Redimensionar la imagen al tamaño del tile (con pequeño margen)
            player_size = TILE_SIZE - 4  # Un poco más pequeño que el tile para mejor visibilidad
            self.player_image = pygame.transform.scale(player_image, (player_size, player_size))
            print("✅ Imagen del repartidor cargada correctamente desde Repartidor.png")
            
        except FileNotFoundError as e:
            print(f"⚠️ No se pudo cargar imagen del repartidor: {e}")
            print("📁 Asegúrate de que exista 'Repartidor.png' en la carpeta del juego")
            self._create_fallback_player_image()
        except Exception as e:
            print(f"❌ Error cargando imagen del repartidor: {e}")
            self._create_fallback_player_image()



    def _create_fallback_player_image(self):
        """✅ NUEVO: Crea una imagen de respaldo para el jugador si no se puede cargar la original."""
        player_size = TILE_SIZE - 4
        fallback_surface = pygame.Surface((player_size, player_size), pygame.SRCALPHA)
        
        # Crear un repartidor simple usando formas geométricas
        center_x = player_size // 2
        center_y = player_size // 2
        
        # Cuerpo (círculo azul)
        pygame.draw.circle(fallback_surface, BLUE, (center_x, center_y), player_size // 3)
        
        # Cabeza (círculo más pequeño, color piel)
        head_color = (255, 220, 177)  # Color piel
        pygame.draw.circle(fallback_surface, head_color, (center_x, center_y - player_size // 4), player_size // 6)
        
        # Casco/gorra (semicírculo)
        helmet_color = (255, 255, 0)  # Amarillo
        helmet_rect = pygame.Rect(center_x - player_size // 8, center_y - player_size // 3, player_size // 4, player_size // 6)
        pygame.draw.ellipse(fallback_surface, helmet_color, helmet_rect)
        
        # Borde del jugador
        pygame.draw.circle(fallback_surface, BLACK, (center_x, center_y), player_size // 3, 2)
        
        self.player_image = fallback_surface

    def _load_weather_images(self):
        """Carga las imágenes para los diferentes estados del clima."""
        
        # Mapeo de estados del clima a archivos de imagen
        weather_files = {
            'clear': 'Despejado.png',
            'clouds': 'Nublado.png', 
            'rain_light': 'Llovizna.png',
            'rain': 'Lluvioso.png',
            'storm': 'Tormenta.png',
            'fog': 'Nublado.png',      # Usa la misma imagen que nublado
            'wind': 'Ventoso.png',
            'heat': 'Despejado.png',   # Usa la misma imagen que despejado
            'cold': 'Ventoso.png'      # Usa la misma imagen que ventoso
        }
        
        weather_loaded = 0
        weather_size = 60  # ✅ AUMENTADO de 40 a 60 píxeles para imagen más grande
        
        for weather_state, filename in weather_files.items():
            try:
                weather_image = pygame.image.load(filename)
                # Redimensionar al tamaño más grande
                self.weather_images[weather_state] = pygame.transform.scale(weather_image, (weather_size, weather_size))
                print(f"✅ Imagen de clima '{weather_state}' cargada desde {filename} (Tamaño: {weather_size}x{weather_size})")
                weather_loaded += 1
            except Exception as e:
                print(f"⚠️ No se pudo cargar imagen de clima '{weather_state}' desde {filename}: {e}")
        
        # Resumen de carga de clima
        total_weather_states = len(weather_files)
        if weather_loaded == total_weather_states:
            print(f"🌤️ ¡PERFECTO! Todas las {weather_loaded} imágenes de clima cargadas (Tamaño: {weather_size}x{weather_size})")
        elif weather_loaded > 0:
            print(f"🌤️ {weather_loaded}/{total_weather_states} imágenes de clima cargadas (Tamaño: {weather_size}x{weather_size})")
        else:
            print("⚠️ No se pudieron cargar imágenes de clima. Usando círculos de colores de respaldo")
        
        # Crear respaldos para climas sin imagen
        self._create_weather_fallbacks()


    def _create_weather_fallbacks(self):
        """Crea íconos de respaldo para climas sin imagen."""
        
        weather_size = 75  # ✅ AJUSTADO: Tamaño que se ajusta mejor al marco
        
        # Colores de respaldo para cada clima
        weather_colors = {
            'clear': (200, 150, 100),
            'clouds': (180, 180, 180),
            'rain_light': (100, 150, 200),
            'rain': (70, 120, 180),
            'storm': (50, 50, 100),
            'fog': (200, 200, 200),
            'wind': (150, 200, 150),
            'heat': (255, 100, 100),
            'cold': (150, 200, 255)
        }
        
        for weather_state, color in weather_colors.items():
            if weather_state not in self.weather_images:
                # Crear superficie circular de respaldo ajustada
                fallback_surface = pygame.Surface((weather_size, weather_size), pygame.SRCALPHA)
                pygame.draw.circle(fallback_surface, color, (weather_size//2, weather_size//2), weather_size//2 - 2)
                pygame.draw.circle(fallback_surface, (100, 100, 100), (weather_size//2, weather_size//2), weather_size//2 - 2, 2)
                
                self.weather_images[weather_state] = fallback_surface
                print(f"✅ Ícono de respaldo creado para clima '{weather_state}' (Tamaño: {weather_size}x{weather_size})")

        
    def _load_tile_images(self):
        """Carga las imágenes para todos los tipos de tiles."""
        images_loaded = 0
        
        try:
            # ✅ Cargar imagen de parque
            park_image = pygame.image.load("pixilart-drawing.png")
            self.tile_images["P"] = pygame.transform.scale(park_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de parque cargada desde pixilart-drawing.png")
            images_loaded += 1
        except Exception as e:
            print(f"⚠️ No se pudo cargar imagen de parque: {e}")
        
        try:
            # ✅ Cargar imagen de calle
            street_image = pygame.image.load("pixil-frame-0 (1).png")
            self.tile_images["C"] = pygame.transform.scale(street_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de calle cargada desde pixil-frame-0 (1).png")
            images_loaded += 1
        except Exception as e:
            print(f"⚠️ No se pudo cargar imagen de calle: {e}")
        
        try:
            # ✅ Cargar imagen de edificio
            building_image = pygame.image.load("pixil-frame-0 (2).png")
            self.tile_images["B"] = pygame.transform.scale(building_image, (TILE_SIZE, TILE_SIZE))
            print("✅ Imagen de edificio cargada desde pixil-frame-0 (2).png")
            images_loaded += 1
        except Exception as e:
            print(f"⚠️ No se pudo cargar imagen de edificio: {e}")
        
        # Resumen de carga
        if images_loaded == 3:
            print(f"🎨 ¡PERFECTO! Todas las {images_loaded} imágenes PNG cargadas correctamente")
        elif images_loaded > 0:
            print(f"🎨 {images_loaded}/3 imágenes PNG cargadas. Usando respaldo para las faltantes")
        else:
            print("⚠️ No se pudieron cargar imágenes PNG. Usando gráficos de respaldo")
        
        # Crear respaldos para las imágenes que no se pudieron cargar
        self._create_fallback_images()


    def get_complete_image_status(self):
        """✅ MODIFICADO: Obtiene el estado completo de todas las imágenes cargadas incluyendo jugador."""
        tile_count = len(self.tile_images)
        
        # Contar imágenes únicas de clima (sin contar respaldos)
        unique_weather_files = set()
        weather_files = {
            'clear': 'Despejado.png',
            'clouds': 'Nublado.png', 
            'rain_light': 'Llovizna.png',
            'rain': 'Lluvioso.png',
            'storm': 'Tormenta.png',
            'fog': 'Nublado.png',
            'wind': 'Ventoso.png',
            'heat': 'Despejado.png',
            'cold': 'Ventoso.png'
        }
        
        for state in self.weather_images:
            if state in weather_files:
                unique_weather_files.add(weather_files[state])
        
        weather_count = len(unique_weather_files)
        
        # Verificar si se cargó la imagen del jugador
        has_player_image = self.player_image is not None
        
        # Estado completo
        if tile_count == 3 and weather_count >= 5 and has_player_image:
            return "✅ Imágenes completas: 3 tiles + clima + jugador"
        elif tile_count == 3 and has_player_image:
            return f"✅ 3 tiles PNG + {weather_count} clima + jugador"
        elif weather_count >= 5 and has_player_image:
            return f"✅ {tile_count} tiles + clima completo + jugador"
        elif has_player_image:
            return f"✅ {tile_count} tiles + {weather_count} clima + jugador + respaldo"
        elif tile_count > 0 or weather_count > 0:
            return f"⚠️ {tile_count} tiles + {weather_count} clima + jugador respaldo"
        else:
            return "⚠️ Solo gráficos de respaldo (incluye jugador)"

    def _create_fallback_images(self):
        """Crea imágenes de respaldo para los tiles que no tienen imagen PNG."""
        
        # ✅ Respaldo para PARQUE (solo si no se cargó la imagen)
        if "P" not in self.tile_images:
            park_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            park_surface.fill(GREEN)
            
            # Dibujar algunos "árboles" simples
            tree_color = (0, 100, 0)
            for i in range(3):
                for j in range(3):
                    if (i + j) % 2 == 0:  # Patrón de tablero
                        tree_rect = pygame.Rect(
                            i * (TILE_SIZE // 3) + 2, 
                            j * (TILE_SIZE // 3) + 2, 
                            TILE_SIZE // 3 - 4, 
                            TILE_SIZE // 3 - 4
                        )
                        pygame.draw.ellipse(park_surface, tree_color, tree_rect)
            
            self.tile_images["P"] = park_surface
            print("✅ Imagen de respaldo para parque creada")
        
        # ✅ Respaldo para CALLE (solo si no se cargó la imagen)
        if "C" not in self.tile_images:
            street_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            street_surface.fill(LIGHT_GRAY)
            
            # Dibujar líneas de calle
            line_color = (180, 180, 180)
            # Línea central horizontal
            pygame.draw.line(street_surface, line_color, 
                        (0, TILE_SIZE // 2), (TILE_SIZE, TILE_SIZE // 2), 2)
            # Línea central vertical
            pygame.draw.line(street_surface, line_color, 
                        (TILE_SIZE // 2, 0), (TILE_SIZE // 2, TILE_SIZE), 2)
            
            self.tile_images["C"] = street_surface
            print("✅ Imagen de respaldo para calle creada")
        
        # ✅ Respaldo para EDIFICIO (solo si no se cargó la imagen)
        if "B" not in self.tile_images:
            building_surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
            building_surface.fill(DARK_GRAY)
            
            # Dibujar ventanas del edificio
            window_color = (100, 100, 100)
            for i in range(2):
                for j in range(2):
                    window_rect = pygame.Rect(
                        4 + i * (TILE_SIZE // 2 - 2), 
                        4 + j * (TILE_SIZE // 2 - 2),
                        TILE_SIZE // 2 - 8, 
                        TILE_SIZE // 2 - 8
                    )
                    pygame.draw.rect(building_surface, window_color, window_rect)
            
            self.tile_images["B"] = building_surface
            print("✅ Imagen de respaldo para edificio creada")

    # ✅ NUEVO MÉTODO: Obtener colores base
    def _get_tile_base_color(self, tile_type):
        """Obtiene el color base para un tipo de tile."""
        if tile_type == "C":
            return LIGHT_GRAY  # Calles
        elif tile_type == "B":
            return DARK_GRAY   # Edificios bloqueados
        elif tile_type == "P":
            return GREEN       # Parques (color de fondo)
        elif tile_type == "R":
            return PURPLE      # Puntos de descanso
        else:
            return WHITE       # Desconocido
    
    def _ensure_data_files(self):
        os.makedirs("data", exist_ok=True)
        os.makedirs("saves", exist_ok=True)
        os.makedirs("api_cache", exist_ok=True)
        
        if not os.path.exists("data/puntajes.json"):
            with open("data/puntajes.json", 'w') as f:
                json.dump([], f)
    
    def initialize_game_data(self):
        """INICIALIZACIÓN CORREGIDA - Carga datos del mapa correctamente."""
        try:
            print("🚀 Inicializando datos del juego...")
            
            # Obtener mapa desde la API real
            self.map_data = self.api_manager.get_city_map()
            
            # CORRECCIÓN: Extraer datos del mapa correctamente
            self.city_width = self.map_data.get('width', 30)
            self.city_height = self.map_data.get('height', 25)
            self.tiles = self.map_data.get('tiles', [])
            self.legend = self.map_data.get('legend', {})
            self.goal = self.map_data.get('goal', 3000)
            self.city_name = self.map_data.get('city_name', 'TigerCity')
            self.max_game_time = self.map_data.get('max_time', 600.0)
            
            # CORRECCIÓN: Recalcular dimensiones del mapa según datos reales
            self.map_pixel_width = self.city_width * TILE_SIZE
            self.map_pixel_height = self.city_height * TILE_SIZE
            
            # VALIDAR POSICIÓN INICIAL DEL JUGADOR
            self.player_pos = self._find_valid_starting_position()
            
            # Obtener pedidos desde la API real - MEJORADO PARA MÁS FLUIDEZ
            orders_data = self.api_manager.get_city_jobs()
            
            # APLICAR REGLAS DE VALIDACIÓN DE PEDIDOS
            for order_data in orders_data:
                try:
                    # REGLA: Los pedidos NO pueden estar en edificios bloqueados
                    if not self._validate_order_positions(order_data):
                        print(f"⚠️ Pedido {order_data.id} tiene posiciones inválidas, corrigiendo...")
                        order_data = self._fix_order_positions(order_data)
                    
                    self.pending_orders.append(order_data)
                except (KeyError, ValueError) as e:
                    print(f"⚠️ Error cargando pedido: {e}")
                    continue
            
            # Ordenar pedidos por tiempo de liberación
            self.pending_orders = deque(sorted(self.pending_orders, key=lambda x: x.release_time))
            
            print(f"✅ {self.city_name} cargada: {self.city_width}x{self.city_height}")
            print(f"✅ {len(self.pending_orders)} pedidos validados cargados")
            print(f"✅ Meta: ${self.goal} | Tiempo: {self.max_game_time}s")
            print(f"✅ Jugador iniciado en posición válida: ({self.player_pos.x}, {self.player_pos.y})")
            
            # Mensaje de bienvenida
            self.add_game_message(f"¡Bienvenido a {self.city_name}! Meta: ${self.goal}", 4.0, GREEN)
            
        except Exception as e:
            print(f"❌ Error cargando datos del mundo: {e}")
            self._create_fallback_data()
    
    def _find_valid_starting_position(self) -> Position:
        """Encuentra una posición inicial válida para el jugador."""
        # Intentar posiciones comunes primero
        common_positions = [
            (2, 2), (3, 3), (1, 1), (4, 4), (5, 5),
            (2, 3), (3, 2), (1, 2), (2, 1)
        ]
        
        for x, y in common_positions:
            if self._is_position_walkable(x, y):
                print(f"✅ Posición inicial válida encontrada: ({x}, {y})")
                return Position(x, y)
        
        # Buscar cualquier posición válida
        for y in range(min(10, self.city_height)):
            for x in range(min(10, self.city_width)):
                if self._is_position_walkable(x, y):
                    print(f"✅ Posición inicial de respaldo: ({x}, {y})")
                    return Position(x, y)
        
        # Fallback final
        print("⚠️ No se encontró posición válida, usando (1, 1)")
        return Position(1, 1)
    
    def _is_position_walkable(self, x: int, y: int) -> bool:
        """Verifica si una posición es caminable según las reglas del juego"""
        if not (0 <= x < self.city_width and 0 <= y < self.city_height):
            return False
        
        if y < len(self.tiles) and x < len(self.tiles[y]):
            tile_type = self.tiles[y][x]
            tile_info = self.legend.get(tile_type, {})
            return not tile_info.get("blocked", False)
        
        return True
    
    def _validate_order_positions(self, order: Order) -> bool:
        """Valida que las posiciones del pedido sean válidas."""
        pickup_valid = self._is_position_walkable(order.pickup.x, order.pickup.y)
        dropoff_valid = self._is_position_walkable(order.dropoff.x, order.dropoff.y)
        
        if not pickup_valid:
            print(f"❌ Pickup de {order.id} en posición bloqueada: ({order.pickup.x}, {order.pickup.y})")
        if not dropoff_valid:
            print(f"❌ Dropoff de {order.id} en posición bloqueada: ({order.dropoff.x}, {order.dropoff.y})")
        
        return pickup_valid and dropoff_valid
    
    def _fix_order_positions(self, order: Order) -> Order:
        """Corrige las posiciones de un pedido para que sean válidas"""
        # Corregir pickup si es necesario
        if not self._is_position_walkable(order.pickup.x, order.pickup.y):
            order.pickup = self._find_nearest_walkable_position(order.pickup.x, order.pickup.y)
            print(f"🔧 Pickup corregido a: ({order.pickup.x}, {order.pickup.y})")
        
        # Corregir dropoff si es necesario
        if not self._is_position_walkable(order.dropoff.x, order.dropoff.y):
            order.dropoff = self._find_nearest_walkable_position(order.dropoff.x, order.dropoff.y)
            print(f"🔧 Dropoff corregido a: ({order.dropoff.x}, {order.dropoff.y})")
        
        return order
    
    def _find_nearest_walkable_position(self, x: int, y: int) -> Position:
        """Encuentra la posición caminable más cercana"""
        # Buscar en espiral desde la posición original
        for radius in range(1, min(self.city_width, self.city_height) // 2):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:  # Solo el borde del cuadrado
                        nx, ny = x + dx, y + dy
                        if self._is_position_walkable(nx, ny):
                            return Position(nx, ny)
        
        # Fallback: encontrar cualquier posición válida
        for ty in range(self.city_height):
            for tx in range(self.city_width):
                if self._is_position_walkable(tx, ty):
                    return Position(tx, ty)
        
        return Position(1, 1)  # Último recurso
    
    def _create_fallback_data(self):
        """Crea datos por defecto si falla la carga de la API."""
        self.city_width = 20
        self.city_height = 15
        self.tiles = [["C"] * 20 for _ in range(15)]
        self.legend = {"C": {"name": "calle", "surface_weight": 1.00}}
        self.goal = 2000
        self.city_name = "Ciudad de Respaldo"
        self.max_game_time = 600.0
        print("🔧 Usando datos de respaldo")

    def add_game_message(self, message: str, duration: float = 3.0, color: tuple = WHITE):
        """Añade un mensaje temporal al juego."""
        self.game_messages.append((message, duration, color))
    
    # SISTEMA DE TIEMPO Y URGENCIA
    def get_order_time_remaining(self, order: Order) -> float:
        """Calcula el tiempo restante de un pedido."""
        if order.status == "waiting_release":
            return order.duration_minutes * 60
        
        elapsed_since_created = self.game_time - order.created_at
        total_duration_seconds = order.duration_minutes * 60
        return max(0, total_duration_seconds - elapsed_since_created)
    
    def get_order_urgency_color(self, order: Order) -> tuple:
        """Determina el color basado en urgencia del pedido."""
        time_remaining = self.get_order_time_remaining(order)
        total_duration = order.duration_minutes * 60
        
        if time_remaining <= 0:
            return DARK_RED
        
        progress = time_remaining / total_duration
        
        if progress > 0.66:
            return DARK_GREEN
        elif progress > 0.33:
            return YELLOW
        else:
            return RED
    
    def get_order_status_text(self, order: Order) -> str:
        time_remaining = self.get_order_time_remaining(order)
        
        if time_remaining <= 0:
            return "EXPIRADO"
        
        minutes = int(time_remaining // 60)
        seconds = int(time_remaining % 60)
        
        if minutes > 0:
            return f"{minutes}:{seconds:02d}"
        else:
            return f"0:{seconds:02d}"
    
    def _get_district_name(self, x: int, y: int) -> str:
        """Sistema de distritos para mejor organización"""
        if y < self.city_height // 3:
            return "Norte"
        elif y < 2 * self.city_height // 3:
            return "Centro"  
        else:
            return "Sur"
    
    def handle_events(self, events):
        """Maneja eventos de pygame."""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if self.game_state == "playing":
                    self._handle_game_events(event)
                elif self.game_state == "menu":
                    self._handle_menu_events(event)
                elif self.game_state == "tutorial":
                    self._handle_tutorial_events(event)
    
    def _handle_game_events(self, event):
        """Maneja eventos durante el juego."""
        if event.key == pygame.K_SPACE:
            self.paused = not self.paused
        elif event.key == pygame.K_i:
            self.show_inventory = not self.show_inventory
            if self.show_inventory:
                self.selected_inventory_index = 0
        elif event.key == pygame.K_o:
            self.show_orders = not self.show_orders
            if self.show_orders:
                self.selected_order_index = 0
        elif event.key == pygame.K_ESCAPE:
            if self.game_over:
                self.game_state = "menu"
                self.game_over = False
                self.victory = False
            else:
                self.paused = not self.paused
        elif event.key == pygame.K_e:
            self.interact_at_position()
        elif event.key == pygame.K_F5:
            self.save_game()
        elif event.key == pygame.K_F9:
            self.load_game()
        elif event.key == pygame.K_z and pygame.key.get_pressed()[pygame.K_LCTRL]:
            self.undo_move()
        elif event.key == pygame.K_p:
            self._sort_inventory_by_priority()
        elif event.key == pygame.K_t:
            self._sort_inventory_by_deadline()
        elif event.key == pygame.K_d:
            self._sort_orders_by_distance()
        
        # Navegación en menús
        elif self.show_inventory:
            if event.key == pygame.K_UP:
                self.selected_inventory_index = max(0, self.selected_inventory_index - 1)
            elif event.key == pygame.K_DOWN:
                max_index = len(self.inventory) - 1
                self.selected_inventory_index = min(max_index, self.selected_inventory_index + 1)
            elif event.key == pygame.K_RETURN:
                self.deliver_selected_order()
        
        elif self.show_orders:
            if event.key == pygame.K_UP:
                self.selected_order_index = max(0, self.selected_order_index - 1)
            elif event.key == pygame.K_DOWN:
                max_index = min(len(self.available_orders.items) - 1, 6)
                self.selected_order_index = min(max_index, self.selected_order_index + 1)
            elif event.key == pygame.K_RETURN:
                self.accept_selected_order()
    
    def _handle_menu_events(self, event):
        """Maneja eventos del menú principal."""
        action = self.menu_system.handle_menu_input(event)
        if action == "start_new_game":
            self.initialize_game_data()
            self.game_state = "playing"
        elif action == "start_tutorial":
            self.tutorial_system = TutorialSystem()
            self.game_state = "tutorial"
        elif action == "exit":
            self.running = False
        elif action and action.startswith("load_slot_"):
            slot = int(action.split("_")[-1])
            if self._load_game(slot):
                self.game_state = "playing"
    
    def _handle_tutorial_events(self, event):
        """Maneja eventos durante el tutorial."""
        if not self.tutorial_system.handle_input(event):
            self.initialize_game_data()
            self.game_state = "playing"
    
    # ALGORITMOS DE ORDENAMIENTO
    def _sort_inventory_by_priority(self):
        """Ordena el inventario por prioridad usando QuickSort."""
        if not self.inventory:
            self.add_game_message("Inventario vacío", 2.0, YELLOW)
            return
        
        inventory_list = list(self.inventory)
        sorted_list = self.sorting_algorithms.quicksort_by_priority(inventory_list)
        self.inventory = deque(sorted_list)
        self.add_game_message("Inventario ordenado por PRIORIDAD (QuickSort)", 3.0, GREEN)
    
    def _sort_inventory_by_deadline(self):
        """Ordena el inventario por tiempo restante usando MergeSort."""
        if not self.inventory:
            self.add_game_message("Inventario vacío", 2.0, YELLOW)
            return
        
        inventory_list = list(self.inventory)
        sorted_list = self.sorting_algorithms.mergesort_by_deadline(inventory_list, self.game_time)
        self.inventory = deque(sorted_list)
        self.add_game_message("Inventario ordenado por TIEMPO RESTANTE (MergeSort)", 3.0, GREEN)
    
    def _sort_orders_by_distance(self):
        """Ordena pedidos disponibles por distancia usando Insertion Sort."""
        if not self.available_orders.items:
            self.add_game_message("No hay pedidos disponibles", 2.0, YELLOW)
            return
        
        orders_list = self.available_orders.items.copy()
        sorted_list = self.sorting_algorithms.insertion_sort_by_distance(orders_list, self.player_pos)
        self.available_orders.items = sorted_list
        self.add_game_message("Pedidos ordenados por DISTANCIA (Insertion Sort)", 3.0, GREEN)
    
    def handle_input(self, keys, dt):
        """Maneja entrada del teclado durante el juego."""
        if self.paused or self.game_over:
            return

        # ✅ BLOQUEO COMPLETO: Si está exhausto (≤30), no procesar ningún movimiento
        if self.stamina <= 30:
            current_time = time.time()
            if not hasattr(self, '_last_exhausted_message') or current_time - self._last_exhausted_message > 3.0:
                if self.stamina <= 0:
                    self.add_game_message("¡EXHAUSTO! Espera a recuperar resistencia hasta 30", 3.0, RED)
                else:
                    self.add_game_message(f"Resistencia baja ({self.stamina:.0f}/30). Espera hasta 30 para moverte", 3.0, YELLOW)
                self._last_exhausted_message = current_time
            return

        actual_speed = self.calculate_actual_speed()
        adjusted_cooldown = self.move_cooldown / max(0.1, actual_speed / self.base_speed)

        self.last_move_time += dt
        if self.last_move_time < adjusted_cooldown:
            return

        direction = (0, 0)
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction = (-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction = (1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            direction = (0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction = (0, 1)
        
        if direction != (0, 0):
            new_pos = Position(
                self.player_pos.x + direction[0], 
                self.player_pos.y + direction[1]
            )
            if self.is_valid_move(new_pos):
                self.move_player(new_pos)
                self.last_move_time = 0
            else:
                # ✅ Mensaje específico cuando el movimiento no es válido por resistencia
                if self.stamina <= 30:
                    if self.stamina <= 0:
                        self.add_game_message("No te puedes mover - ¡Estás exhausto!", 1.5, RED)
                    else:
                        self.add_game_message(f"No te puedes mover - Resistencia baja ({self.stamina:.0f}/30)", 1.5, YELLOW)
    
    def is_valid_move(self, pos: Position) -> bool:
        """✅ CORREGIDO: Verifica si un movimiento es válido con regla de exhausto."""
        if not (0 <= pos.x < self.city_width and 0 <= pos.y < self.city_height):
            return False
        
        # REGLA: No se puede caminar en edificios bloqueados
        if pos.y < len(self.tiles) and pos.x < len(self.tiles[pos.y]):
            tile_type = self.tiles[pos.y][pos.x]
            tile_info = self.legend.get(tile_type, {})
            if tile_info.get("blocked", False):
                return False
        
        # ✅ REGLA CRÍTICA: Si está exhausto (resistencia = 0), NO puede moverse hasta llegar a 30
        if self.stamina <= 0:
            return False
        
        # REGLA: Necesita resistencia mínima para moverse (debe tener suficiente para el costo)
        stamina_cost = self.calculate_stamina_cost()
        return self.stamina >= stamina_cost
    
    # SISTEMA DE VELOCIDAD
    def calculate_actual_speed(self) -> float:
        """Calcula la velocidad actual considerando todos los factores."""
        # ✅ BLOQUEO TOTAL: Si está exhausto (=0), velocidad CERO
        if self.stamina <= 0:
            return 0.0
        
        v0 = self.base_speed  # 3 celdas/seg
        M_clima = self.weather_system.get_speed_multiplier()
        
        # Multiplicador de peso según documento
        total_weight = sum(order.weight for order in self.inventory)
        M_peso = max(0.8, 1.0 - 0.03 * total_weight)
        
        # Multiplicador de reputación según documento
        M_rep = 1.03 if self.reputation >= 90 else 1.0
        
        # ✅ CORREGIDO: Multiplicador de resistencia según documento
        if self.stamina <= 30:
            M_resistencia = 0.8  # Cansado (1-30)
        else:
            M_resistencia = 1.0  # Normal (>30)
        
        # Surface weight del tile actual
        surface_weight = 1.0
        if (self.player_pos.y < len(self.tiles) and 
            self.player_pos.x < len(self.tiles[self.player_pos.y])):
            tile_type = self.tiles[self.player_pos.y][self.player_pos.x]
            tile_info = self.legend.get(tile_type, {})
            surface_weight = tile_info.get("surface_weight", 1.0)
        
        # FÓRMULA OFICIAL
        final_speed = v0 * M_clima * M_peso * M_rep * M_resistencia * surface_weight
        return max(0.0, final_speed)
    
    # SISTEMA DE RESISTENCIA
    def calculate_stamina_cost(self) -> float:
        """Calcula el costo de resistencia por movimiento."""
        base_cost = 0.5  # Base según documento: -0.5 por celda
        
        # Penalización por peso según documento
        total_weight = sum(order.weight for order in self.inventory)
        if total_weight > 3:
            weight_penalty = 0.2 * (total_weight - 3)
            base_cost += weight_penalty
        
        # Penalizaciones climáticas según documento
        if self.weather_system.current_condition in ['rain', 'wind']:
            base_cost += 0.1
        elif self.weather_system.current_condition == 'storm':
            base_cost += 0.3
        elif self.weather_system.current_condition == 'heat':
            base_cost += 0.2
        
        # Penalización por superficie
        if (self.player_pos.y < len(self.tiles) and 
            self.player_pos.x < len(self.tiles[self.player_pos.y])):
            tile_type = self.tiles[self.player_pos.y][self.player_pos.x]
            tile_info = self.legend.get(tile_type, {})
            surface_weight = tile_info.get("surface_weight", 1.0)
            
            if surface_weight < 1.0:
                base_cost += (1.0 - surface_weight) * 0.2
        
        return base_cost
    
    def move_player(self, new_pos: Position):
        """✅ CORREGIDO: Mueve el jugador con regla de exhausto."""
        # ✅ VERIFICACIÓN DOBLE: Si está exhausto (=0), no puede moverse
        if self.stamina <= 0:
            self.add_game_message("¡Exhausto! Recupera hasta 30 de resistencia para moverte", 2.0, RED)
            return
        
        stamina_cost = self.calculate_stamina_cost()
        
        # ✅ VERIFICACIÓN TRIPLE: Asegurar que tiene suficiente resistencia
        if self.stamina < stamina_cost:
            self.add_game_message("¡Resistencia insuficiente para moverse!", 2.0, RED)
            return
        
        # Efectos climáticos visuales
        if self.weather_system.current_condition in ['rain', 'storm']:
            if random.random() < 0.1:
                self.add_game_message(f"El {self.weather_system._get_condition_name(self.weather_system.current_condition).lower()} dificulta el movimiento", 2.0, CYAN)
        
        self.player_pos = new_pos
        self.stamina = max(0, self.stamina - stamina_cost)
        
        # ✅ CORREGIDO: Mensajes de estado según documento
        if self.stamina <= 0:
            self.add_game_message("¡Exhausto! No puedes moverte hasta recuperar 30 de resistencia", 3.0, RED)
        elif self.stamina <= 30:
            self.add_game_message(f"Cansado ({self.stamina:.0f}/30) - velocidad reducida", 2.0, YELLOW)
    
    def interact_at_position(self):
        """Maneja interacciones en la posición actual del jugador."""
        interaction_found = False
        
        # Verificar recogida de pedidos
        for order in self.available_orders.items[:]:
            if (order.pickup.x == self.player_pos.x and 
                order.pickup.y == self.player_pos.y and 
                order.status in ["available", "accepted"]):
                
                time_remaining = self.get_order_time_remaining(order)
                if time_remaining <= 0:
                    self.add_game_message(f"{order.id} ha expirado!", 3.0, RED)
                    interaction_found = True
                    break
                
                total_weight = sum(o.weight for o in self.inventory)
                if total_weight + order.weight <= self.max_weight:
                    order.status = "picked_up"
                    order.accepted_at = self.game_time
                    self.inventory.append(order)
                    self.available_orders.remove(order)
                    time_text = self.get_order_status_text(order)
                    district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                    self.add_game_message(f"{order.id} recogido ({time_text}) → ({order.dropoff.x},{order.dropoff.y}) [{district}]", 4.0, GREEN)
                    interaction_found = True
                else:
                    self.add_game_message(f"No hay capacidad para {order.id} (necesario: {order.weight}kg)", 3.0, ORANGE)
                    interaction_found = True
                break
        
        # Verificar entrega de pedidos
        if not interaction_found:
            for order in list(self.inventory):
                if (order.dropoff.x == self.player_pos.x and 
                    order.dropoff.y == self.player_pos.y and 
                    order.status == "picked_up"):
                    
                    time_remaining = self.get_order_time_remaining(order)
                    if time_remaining <= 0:
                        self.add_game_message(f"{order.id} expiró mientras lo transportabas!", 3.0, RED)
                        interaction_found = True
                        break
                    
                    self.deliver_order(order)
                    interaction_found = True
                    break
        
        # Mostrar pedidos cercanos si no hay interacción directa
        if not interaction_found:
            self._show_nearby_interactions()

    def _show_nearby_interactions(self):
        """Muestra información sobre pedidos cercanos"""
        nearby_pickups = []
        nearby_dropoffs = []
        
        for order in self.available_orders.items:
            if order.status in ["available", "accepted"]:
                time_remaining = self.get_order_time_remaining(order)
                if time_remaining > 0:
                    distance = abs(order.pickup.x - self.player_pos.x) + abs(order.pickup.y - self.player_pos.y)
                    if distance <= 3:
                        nearby_pickups.append((order, distance))
        
        for order in self.inventory:
            if order.status == "picked_up":
                time_remaining = self.get_order_time_remaining(order)
                if time_remaining > 0:
                    distance = abs(order.dropoff.x - self.player_pos.x) + abs(order.dropoff.y - self.player_pos.y)
                    if distance <= 3:
                        nearby_dropoffs.append((order, distance))
        
        if nearby_pickups:
            closest = min(nearby_pickups, key=lambda x: x[1])
            order, dist = closest
            time_text = self.get_order_status_text(order)
            district = self._get_district_name(order.pickup.x, order.pickup.y)
            self.add_game_message(f"{order.id} ({time_text}) está a {dist} celdas en ({order.pickup.x}, {order.pickup.y}) [{district}]", 3.0, YELLOW)
        elif nearby_dropoffs:
            closest = min(nearby_dropoffs, key=lambda x: x[1])
            order, dist = closest
            time_text = self.get_order_status_text(order)
            district = self._get_district_name(order.dropoff.x, order.dropoff.y)
            self.add_game_message(f"Entrega {order.id} ({time_text}) está a {dist} celdas en ({order.dropoff.x}, {order.dropoff.y}) [{district}]", 3.0, YELLOW)
        else:
            self.add_game_message("No hay nada para interactuar aquí", 2.0, GRAY)

    # SISTEMA DE REPUTACIÓN
    def deliver_order(self, order: Order):
        """Entrega un pedido y actualiza reputación."""
        time_remaining = self.get_order_time_remaining(order)
        total_duration = order.duration_minutes * 60
        time_used = total_duration - time_remaining
        
        rep_change = 0
        status_msg = ""
        delivery_was_clean = True
        
        # REGLAS DE REPUTACIÓN SEGÚN DOCUMENTO
        if time_remaining > total_duration * 0.8:  # Entrega muy temprana (≥20% antes)
            rep_change = 5
            status_msg = "Entrega muy temprana"
        elif time_remaining > total_duration * 0.3:  # Entrega a tiempo
            rep_change = 3
            status_msg = "Entrega puntual"
        elif time_remaining > 0:  # Tarde pero no expirado
            if time_used <= 30:  # Tarde ≤30s
                rep_change = -2
                status_msg = "Entrega ligeramente tarde"
                delivery_was_clean = False
            elif time_used <= 120:  # Tarde 31-120s
                rep_change = -5
                status_msg = "Entrega tarde"
                delivery_was_clean = False
            else:  # Tarde >120s
                rep_change = -10
                status_msg = "Entrega muy tarde"
                delivery_was_clean = False
        else:  # Expirado
            rep_change = -10
            status_msg = "Entrega muy tarde (expirado)"
            delivery_was_clean = False
        
        # REGLA: Primera tardanza del día con reputación ≥85 tiene penalización reducida
        if rep_change < 0 and self.reputation >= 85 and not hasattr(self, '_first_late_penalty_applied'):
            rep_change = rep_change // 2
            status_msg += " (Penalización reducida)"
            self._first_late_penalty_applied = True
        
        self.reputation = max(0, min(100, self.reputation + rep_change))
        
        # SISTEMA DE RACHAS PERFECTAS
        if delivery_was_clean and self.last_delivery_was_clean:
            self.delivery_streak += 1
            
            if self.delivery_streak == 3:
                self.reputation = min(100, self.reputation + 2)
                status_msg += " ¡Racha de 3! (+2 reputación extra)"
                self.delivery_streak = 0
        else:
            if not delivery_was_clean:
                self.delivery_streak = 0
        
        self.last_delivery_was_clean = delivery_was_clean
        
        # BONUS DE PAGO POR REPUTACIÓN ALTA (≥90)
        payout = order.payout
        if self.reputation >= 90:
            payout = int(payout * 1.05)  # +5% bonus
            status_msg += " (+5% bonus)"
        
        self.money += payout
        
        order.status = "delivered"
        self.inventory.remove(order)
        self.completed_orders.append(order)
        
        time_text = self.get_order_status_text(order)
        district = self._get_district_name(order.dropoff.x, order.dropoff.y)
        self.add_game_message(f"{status_msg} - ${payout} (Rep: {self.reputation}) [{district}] [{time_text} restante]", 4.0, GREEN if delivery_was_clean else ORANGE)
        
        if self.delivery_streak > 0:
            self.add_game_message(f"Racha perfecta: {self.delivery_streak}/3", 2.0, ORANGE)
    
    def accept_selected_order(self):
        """Acepta el pedido seleccionado."""
        if not self.available_orders.items or self.selected_order_index >= len(self.available_orders.items):
            self.add_game_message("No hay pedidos disponibles para aceptar", 2.0, RED)
            return
        
        order = self.available_orders.items[self.selected_order_index]
        
        time_remaining = self.get_order_time_remaining(order)
        if time_remaining <= 0:
            self.add_game_message(f"{order.id} ha expirado!", 3.0, RED)
            return
        
        total_weight = sum(o.weight for o in self.inventory)
        if total_weight + order.weight <= self.max_weight:
            order.status = "accepted"
            order.accepted_at = self.game_time
            time_text = self.get_order_status_text(order)
            district = self._get_district_name(order.pickup.x, order.pickup.y)
            self.add_game_message(f"Aceptado {order.id} ({time_text}) - Ve a ({order.pickup.x}, {order.pickup.y}) [{district}]", 4.0, GREEN)
            
            if self.selected_order_index >= len(self.available_orders.items):
                self.selected_order_index = max(0, len(self.available_orders.items) - 1)
        else:
            available_capacity = self.max_weight - total_weight
            self.add_game_message(f"Capacidad insuficiente: {available_capacity}kg disponible, necesario {order.weight}kg", 3.0, ORANGE)
    
    def deliver_selected_order(self):
        """Entrega el pedido seleccionado del inventario."""
        if not self.inventory or self.selected_inventory_index >= len(self.inventory):
            return
        
        inventory_list = list(self.inventory)
        order = inventory_list[self.selected_inventory_index]
        
        if (order.dropoff.x == self.player_pos.x and 
            order.dropoff.y == self.player_pos.y):
            self.deliver_order(order)
            
            if self.selected_inventory_index >= len(self.inventory):
                self.selected_inventory_index = max(0, len(self.inventory) - 1)
        else:
            distance = abs(order.dropoff.x - self.player_pos.x) + abs(order.dropoff.y - self.player_pos.y)
            time_text = self.get_order_status_text(order)
            district = self._get_district_name(order.dropoff.x, order.dropoff.y)
            self.add_game_message(f"Ir a ({order.dropoff.x}, {order.dropoff.y}) ({time_text}) [{district}] - {distance} celdas", 3.0, YELLOW)
    
    def undo_move(self):
        """Deshace el último movimiento usando el historial."""
        if self.history.size() > 0:
            state = self.history.pop()
            if state:
                self.player_pos = state.player_pos
                self.stamina = state.stamina
                self.reputation = state.reputation
                self.money = state.money
                self.delivery_streak = getattr(state, 'delivery_streak', 0)
                self.add_game_message(f"Estado restaurado ({self.history.size()} restantes)", 2.0, CYAN)
            else:
                self.add_game_message("No hay más estados para deshacer", 2.0, RED)
        else:
            self.add_game_message("No hay movimientos para deshacer", 2.0, RED)
    
    def save_game(self, slot: int = 1):
        """GUARDADO CORREGIDO - Incluye todos los datos del mapa."""
        try:
            # CORRECCIÓN: Crear estado completo con todos los datos del mapa
            state = GameState(
                player_pos=self.player_pos,
                stamina=self.stamina,
                reputation=self.reputation,
                money=self.money,
                game_time=self.game_time,
                weather_time=self.weather_system.time_in_current,
                current_weather=self.weather_system.current_condition,
                weather_intensity=self.weather_system.current_intensity,
                inventory=list(self.inventory),
                available_orders=self.available_orders.items,
                completed_orders=self.completed_orders,
                goal=self.goal,
                delivery_streak=self.delivery_streak,
                pending_orders=list(self.pending_orders),
                # CAMPOS CRÍTICOS PARA GUARDADO/CARGA CORRECTA
                city_width=self.city_width,
                city_height=self.city_height,
                tiles=self.tiles,
                legend=self.legend,
                city_name=self.city_name,
                max_game_time=self.max_game_time
            )
            
            if self.file_manager.save_game_with_validation(state, slot):
                self.add_game_message(f"Juego guardado en slot {slot} ({self.city_name} {self.city_width}x{self.city_height})", 2.0, GREEN)
            else:
                self.add_game_message(f"Error guardando en slot {slot}", 3.0, RED)
            
        except Exception as e:
            self.add_game_message(f"Error guardando: {e}", 3.0, RED)
    
    def _load_game(self, slot: int = 1) -> bool:
        """CARGA CORREGIDA - Restaura todos los datos del mapa."""
        state = self.file_manager.load_game_with_validation(slot)
        
        if state is None:
            self.add_game_message(f"No se pudo cargar el slot {slot}", 3.0, RED)
            return False
        
        # CORRECCIÓN: Restaurar TODOS los datos del estado incluyendo mapa
        self.player_pos = state.player_pos
        self.stamina = state.stamina
        self.reputation = state.reputation
        self.money = state.money
        self.game_time = state.game_time
        self.weather_system.time_in_current = state.weather_time
        self.weather_system.current_condition = state.current_weather
        self.weather_system.current_intensity = state.weather_intensity
        self.inventory = deque(state.inventory)
        self.available_orders.items = state.available_orders
        self.completed_orders = state.completed_orders
        self.goal = state.goal
        self.delivery_streak = getattr(state, 'delivery_streak', 0)
        self.pending_orders = deque(getattr(state, 'pending_orders', []))
        
        # CORRECCIÓN CRÍTICA: Restaurar datos del mapa
        self.city_width = getattr(state, 'city_width', 30)
        self.city_height = getattr(state, 'city_height', 25)
        self.tiles = getattr(state, 'tiles', [])
        self.legend = getattr(state, 'legend', {})
        self.city_name = getattr(state, 'city_name', 'TigerCity')
        self.max_game_time = getattr(state, 'max_game_time', 600.0)
        
        # CORRECCIÓN: Recalcular dimensiones del mapa tras la carga
        self.map_pixel_width = self.city_width * TILE_SIZE
        self.map_pixel_height = self.city_height * TILE_SIZE
        
        self.add_game_message(f"Juego cargado desde slot {slot} - {self.city_name} {self.city_width}x{self.city_height}", 2.0, GREEN)
        return True
    
    def load_game(self, slot: int = 1):
        """Función pública para cargar juego."""
        self._load_game(slot)
    
    def _process_order_releases(self, dt: float):
        """🚀 AJUSTADO: Liberación de pedidos con límite reducido para mayor enfoque."""
        MAX_ACTIVE_ORDERS = 10  # 🎯 AJUSTE: Reducido de 30 a 10 para mayor enfoque estratégico
        current_active_orders = len(self.available_orders.items)
        
        released_count = 0
        orders_to_release = 0
        
        # 🎯 AJUSTE: Sistema de oleadas ajustado para menor cantidad pero más estratégico
        if current_active_orders < MAX_ACTIVE_ORDERS // 3:  # Si hay muy pocos pedidos
            orders_to_release = 3  # Liberar 3 a la vez
        elif current_active_orders < MAX_ACTIVE_ORDERS // 2:  # Si hay pocos pedidos
            orders_to_release = 2  # Liberar 2 a la vez
        elif current_active_orders < MAX_ACTIVE_ORDERS:
            orders_to_release = 1  # Liberar 1 normal
        
        while (self.pending_orders and 
               released_count < orders_to_release and
               self.pending_orders[0].release_time <= self.game_time and
               current_active_orders < MAX_ACTIVE_ORDERS):
            
            order = self.pending_orders.popleft()
            
            # VALIDAR POSICIONES ANTES DE LIBERAR
            if not self._validate_order_positions(order):
                order = self._fix_order_positions(order)
            
            order.status = "available"
            order.created_at = self.game_time
            self.available_orders.enqueue(order)
            released_count += 1
            current_active_orders += 1
            
            if released_count <= 3:
                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"
                duration_text = f"{order.duration_minutes * 60:.0f}s"
                district = getattr(order, 'district', self._get_district_name(order.pickup.x, order.pickup.y))
                # 🚀 Indicadores de EXTREMA urgencia por tiempos súper cortos
                if order.priority >= 2:
                    urgency_indicator = "🔥💨💀"  # CRÍTICO: 8-15 segundos
                elif order.priority == 1:
                    urgency_indicator = "🔥💨"     # URGENTE: 10-18 segundos
                else:
                    urgency_indicator = "🔥"       # NORMAL: 12-22 segundos
                self.add_game_message(f"📋 {urgency_indicator}{order.id} ({priority_text}) ${order.payout} ({duration_text}) [{district}]", 2.0, YELLOW)
        
        if released_count > 2:
            self.add_game_message(f"📋 {released_count} pedidos ULTRA URGENTES (8-22s) disponibles", 2.0, BRIGHT_RED)
    
    def _check_expired_orders(self, dt: float):
        """Verifica y maneja pedidos expirados."""
        expired_orders = []
        
        # Verificar pedidos disponibles
        for order in self.available_orders.items[:]:
            time_remaining = self.get_order_time_remaining(order)
            if time_remaining <= 0:
                expired_orders.append(order)
                self.available_orders.remove(order)
        
        # Verificar pedidos en inventario
        for order in list(self.inventory):
            time_remaining = self.get_order_time_remaining(order)
            if time_remaining <= 0:
                expired_orders.append(order)
                self.inventory.remove(order)
        
        # Aplicar penalizaciones por expiración según documento
        for order in expired_orders:
            self.reputation -= 6  # Perder/expirar paquete: -6
            self.delivery_streak = 0
            self.last_delivery_was_clean = False
            self.add_game_message(f"❌ {order.id} expiró! (-6 reputación)", 4.0, RED)
    
    def _get_stamina_recovery_rate(self) -> float:
        """Calcula la tasa de recuperación de resistencia."""
        base_recovery = 5.0  # +5 por segundo según documento
        
        # Verificar si está en punto de descanso
        if (self.player_pos.y < len(self.tiles) and 
            self.player_pos.x < len(self.tiles[self.player_pos.y])):
            tile_type = self.tiles[self.player_pos.y][self.player_pos.x]
            tile_info = self.legend.get(tile_type, {})
            
            # Puntos de descanso opcionales: +10/seg adicional
            if tile_info.get("rest_bonus", 0) > 0:
                bonus_recovery = base_recovery + 10.0  # Total: +15/seg en puntos de descanso
                # ✅ Mensaje de bonus de recuperación
                if not hasattr(self, '_last_bonus_message') or time.time() - self._last_bonus_message > 5.0:
                    if self.stamina <= 0:
                        self.add_game_message("¡En un parque! Recuperarás resistencia más rápido", 3.0, GREEN)
                    self._last_bonus_message = time.time()
                return bonus_recovery
        
        return base_recovery
    
    def update(self, dt: float):
        """Actualiza la lógica del juego."""
        if self.game_state != "playing" or self.paused or self.game_over:
            return
        
        # Contar FPS
        self.fps_counter += 1
        self.fps_timer += dt
        if self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.fps_timer = 0
        
        # Guardar estado para historial
        if self.history.size() == 0 or self.game_time - getattr(self, '_last_history_save', 0) > 8.0:
            current_state = GameState(
                player_pos=Position(self.player_pos.x, self.player_pos.y),
                stamina=self.stamina,
                reputation=self.reputation,
                money=self.money,
                game_time=self.game_time,
                weather_time=self.weather_system.time_in_current,
                current_weather=self.weather_system.current_condition,
                weather_intensity=self.weather_system.current_intensity,
                inventory=list(self.inventory),
                available_orders=self.available_orders.items,
                completed_orders=self.completed_orders,
                goal=self.goal,
                delivery_streak=self.delivery_streak,
                pending_orders=list(self.pending_orders),
                # Campos para guardado/carga correcta
                city_width=self.city_width,
                city_height=self.city_height,
                tiles=self.tiles,
                legend=self.legend,
                city_name=self.city_name,
                max_game_time=self.max_game_time
            )
            self.history.push(current_state)
            self._last_history_save = self.game_time
        
        self.game_time += dt
        self.weather_system.update(dt)
        
        self._process_order_releases(dt)
        self._check_expired_orders(dt)
        
        self.message_timer += dt
        self.game_messages = [
            (msg, time_left - dt, color) for msg, time_left, color in self.game_messages 
            if time_left - dt > 0
        ]
        
        # ✅ RECUPERACIÓN DE RESISTENCIA - Mensaje cuando se recupera del exhausto
        previous_stamina = getattr(self, '_previous_stamina', self.stamina)
        
        if self.stamina < self.max_stamina and self.last_move_time > 1.0:
            recovery_rate = self._get_stamina_recovery_rate()
            new_stamina = min(self.max_stamina, self.stamina + recovery_rate * dt)
            
            # ✅ Mensaje cuando se recupera del estado exhausto (pasa de 0 a >0 y llega a 30)
            if previous_stamina <= 0 and new_stamina > 0:
                if new_stamina >= 30:
                    self.add_game_message("¡Ya puedes moverte de nuevo! (Resistencia recuperada a 30+)", 3.0, GREEN)
                else:
                    self.add_game_message(f"Recuperando... {new_stamina:.0f}/30 para moverte", 2.0, YELLOW)
            # ✅ Mensaje cuando alcanza 30 desde un estado de recuperación
            elif previous_stamina < 30 and new_stamina >= 30:
                self.add_game_message("¡Ya puedes moverte! Resistencia: 30/100", 3.0, GREEN)
            
            self.stamina = new_stamina
        
        self._previous_stamina = self.stamina
        
        # CONDICIONES DE VICTORIA/DERROTA
        if self.reputation < 20:  # Derrota por reputación baja
            self.game_over = True
            self.add_game_message("¡Juego terminado! Reputación muy baja.", 5.0, RED)
        elif self.money >= self.goal:  # Victoria por alcanzar meta
            self.victory = True
            self.game_over = True
            self.add_game_message("¡Victoria! Meta de ingresos alcanzada.", 5.0, GREEN)
        elif self.game_time >= self.max_game_time:  # Fin de jornada
            self.game_over = True
            if self.money >= self.goal:
                self.victory = True
                self.add_game_message("¡Victoria! Tiempo agotado pero meta cumplida.", 5.0, GREEN)
            else:
                self.add_game_message("¡Tiempo agotado! No se cumplió la meta.", 5.0, RED)
    
    def save_score(self, score: int):
        """✅ CORREGIDO: Guarda el puntaje usando el método correcto."""
        try:
            # Cargar puntajes existentes usando el método del file_manager
            scores = self.file_manager.load_scores()
            
            final_score = self._calculate_final_score()
            
            new_score = {
                "score": final_score,
                "money": self.money,
                "reputation": self.reputation,
                "completed_orders": len(self.completed_orders),
                "game_time": round(self.game_time, 1),
                "date": datetime.now().isoformat(),
                "victory": self.victory,
                "delivery_streak_record": getattr(self, 'delivery_streak', 0),
                "city_name": self.city_name,
                "city_size": f"{self.city_width}x{self.city_height}",
                "api_source": "TigerCity_Real"
            }
            
            scores.append(new_score)
            scores.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # Mantener solo los mejores 10
            scores = scores[:10]
            
            # Guardar usando el file_manager
            scores_file = "data/puntajes.json"
            os.makedirs("data", exist_ok=True)
            
            with open(scores_file, 'w') as f:
                json.dump(scores, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Puntaje guardado: {final_score} puntos")
            
        except Exception as e:
            print(f"❌ Error guardando puntaje: {e}")
            self.add_game_message(f"Error guardando puntaje: {e}", 3.0, RED)
    
    def _calculate_final_score(self) -> int:
        """Calcula el puntaje final según las reglas del documento."""
        # Base: suma de pagos afectada por reputación alta
        pay_mult = 1.05 if self.reputation >= 90 else 1.0
        score_base = self.money * pay_mult
        
        # Bonus por tiempo (terminar antes del 80% del tiempo)
        bonus_tiempo = 0
        if self.victory and self.game_time < self.max_game_time * 0.8:
            time_bonus_factor = (self.max_game_time * 0.8 - self.game_time) / (self.max_game_time * 0.8)
            bonus_tiempo = int(500 * time_bonus_factor)
        
        # Bonus por entregas completadas
        delivery_bonus = len(self.completed_orders) * 10
        
        # Bonus por reputación
        reputation_bonus = max(0, (self.reputation - 70) * 5)
        
        final_score = int(score_base + bonus_tiempo + delivery_bonus + reputation_bonus)
        return max(0, final_score)

    def draw(self):
        """Dibuja toda la interfaz del juego."""
        if self.game_state == "menu":
            self.menu_system.draw(self.screen)
        elif self.game_state == "tutorial":
            self.screen.fill((20, 25, 40))
            self.tutorial_system.draw(self.screen)
        elif self.game_state == "playing":
            self._draw_game()
        
        pygame.display.flip()
    




    
    def _draw_game(self):
        """Dibuja la pantalla principal del juego."""
        self.screen.fill(UI_BACKGROUND)
        
        self.draw_weather_background()
        self.draw_full_map()  # ✅ Usa el método mejorado con imágenes
        self.draw_orders()
        self.draw_player()
        self.draw_ui()
        
        if self.show_inventory:
            self.draw_inventory_overlay()
        
        if self.show_orders:
            self.draw_orders_overlay()
        
        self.draw_game_messages()
        self.draw_weather_notifications()
        
        if self.paused:
            self.draw_pause_overlay()
        
        if self.game_over:
            self.draw_game_over_overlay()
    
    def draw_weather_background(self):
        weather_color = self.weather_system.get_weather_color()
        alpha = int(25 * self.weather_system.current_intensity)
        
        if alpha > 5:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            overlay.set_alpha(alpha)
            overlay.fill(weather_color)
            self.screen.blit(overlay, (0, 0))
    
    def draw_game_messages(self):
        """✅ CORREGIDO: Mensajes en esquina inferior derecha."""
        # Posición en esquina inferior derecha
        base_x = WINDOW_WIDTH - 450  # 450 píxeles desde la derecha
        base_y = WINDOW_HEIGHT - 200  # 200 píxeles desde abajo
        
        for i, (message, time_left, color) in enumerate(self.game_messages[-5:]):
            alpha = min(255, int(255 * (time_left / 3.0)))
            
            text_surface = self.small_font.render(message, True, color)
            y_offset = base_y + i * 22
            
            # Fondo semi-transparente
            bg_rect = pygame.Rect(base_x - 10, y_offset - 2, text_surface.get_width() + 20, 20)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(120)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, bg_rect)
            
            # Borde del mensaje
            pygame.draw.rect(self.screen, (255, 255, 255, 50), bg_rect, 1)
            
            text_surface.set_alpha(alpha)
            self.screen.blit(text_surface, (base_x, y_offset))
    
    def draw_weather_notifications(self):
        """✅ CORREGIDO: Notificaciones del clima en esquina inferior derecha."""
        # Posición en esquina inferior derecha (debajo de los mensajes del juego)
        base_x = WINDOW_WIDTH - 500  # 500 píxeles desde la derecha
        base_y = WINDOW_HEIGHT - 120  # 120 píxeles desde abajo (arriba de los mensajes del juego)
        
        for i, (notification, time_left) in enumerate(self.weather_system.weather_notifications):
            alpha = min(255, int(255 * (time_left / 4.0)))
            
            text_surface = self.font.render(notification, True, self.weather_system.get_weather_color())
            y_offset = base_y + i * 28
            
            # Fondo semi-transparente
            bg_rect = pygame.Rect(base_x - 10, y_offset - 2, text_surface.get_width() + 20, 24)
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(120)
            bg_surface.fill((0, 0, 0))
            self.screen.blit(bg_surface, bg_rect)
            
            # Borde
            pygame.draw.rect(self.screen, (255, 255, 255, 50), bg_rect, 1)
            
            text_surface.set_alpha(alpha)
            self.screen.blit(text_surface, (base_x, y_offset))
    
    # ✅ MÉTODO MODIFICADO: draw_full_map con soporte para imágenes
    def draw_full_map(self):
        """MEJORADO: Dibuja el mapa completo con imágenes para tiles especiales."""
        for y in range(self.city_height):
            for x in range(self.city_width):
                if y < len(self.tiles) and x < len(self.tiles[y]):
                    tile_type = self.tiles[y][x]
                    
                    screen_x = x * TILE_SIZE + self.map_offset_x
                    screen_y = y * TILE_SIZE + self.map_offset_y
                    
                    rect = pygame.Rect(screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                    
                    # ✅ NUEVO: Verificar si hay imagen disponible para este tipo de tile
                    if tile_type in self.tile_images:
                        # Dibujar fondo primero
                        base_color = self._get_tile_base_color(tile_type)
                        pygame.draw.rect(self.screen, base_color, rect)
                        
                        # ✅ NUEVO: Dibujar la imagen encima
                        self.screen.blit(self.tile_images[tile_type], (screen_x, screen_y))
                        
                        # ✅ NUEVO: Efecto especial para parques si el jugador está cerca
                        if tile_type == "P":
                            player_screen_x = self.player_pos.x * TILE_SIZE + self.map_offset_x
                            player_screen_y = self.player_pos.y * TILE_SIZE + self.map_offset_y
                            distance = abs(player_screen_x - screen_x) + abs(player_screen_y - screen_y)
                            
                            # Si el jugador está en el parque, mostrar bonus
                            if distance < TILE_SIZE:
                                bonus_text = self.small_font.render("+15/s", True, (255, 255, 255))
                                text_rect = bonus_text.get_rect(center=(screen_x + TILE_SIZE//2, screen_y + TILE_SIZE//2))
                                
                                # Fondo semi-transparente para el texto
                                text_bg = pygame.Rect(text_rect.x - 2, text_rect.y - 1, text_rect.width + 4, text_rect.height + 2)
                                text_bg_surface = pygame.Surface((text_bg.width, text_bg.height))
                                text_bg_surface.set_alpha(150)
                                text_bg_surface.fill((0, 100, 0))
                                self.screen.blit(text_bg_surface, text_bg)
                                
                                self.screen.blit(bonus_text, text_rect)
                    else:
                        # Dibujar color sólido como antes
                        color = self._get_tile_base_color(tile_type)
                        pygame.draw.rect(self.screen, color, rect)
                    
                    # Dibujar borde del tile
                    pygame.draw.rect(self.screen, (100, 100, 100), rect, 1)
        
        self.draw_map_info()

    def draw_map_info(self):
        """CORREGIDO: Información del mapa con datos reales de la API."""
        map_rect = pygame.Rect(
            self.map_offset_x - 3, 
            self.map_offset_y - 3, 
            self.map_pixel_width + 6, 
            self.map_pixel_height + 6
        )
        pygame.draw.rect(self.screen, UI_BORDER, map_rect, 3)
        
        # Título con nombre real de la ciudad Y DIMENSIONES CORRECTAS
        title_text = self.title_font.render(f"{self.city_name.upper()} {self.city_width}x{self.city_height}", True, UI_TEXT_HEADER)
        title_bg = pygame.Rect(
            self.map_offset_x + self.map_pixel_width // 2 - title_text.get_width() // 2 - 10,
            2,
            title_text.get_width() + 20,
            22
        )
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=5)
        pygame.draw.rect(self.screen, UI_BORDER, title_bg, 2, border_radius=5)
        title_rect = title_text.get_rect(center=(
            self.map_offset_x + self.map_pixel_width // 2,
            13
        ))
        self.screen.blit(title_text, title_rect)
        
        # Información de tamaño
        size_text = self.font.render(f"Tiles: {TILE_SIZE}px | {self.city_width * self.city_height} celdas totales", True, UI_TEXT_SECONDARY)
        self.screen.blit(size_text, (self.map_offset_x, self.map_offset_y - 12))
        
        # ✅ NUEVO: Información de las imágenes (tiles y clima)
        tile_count = len(self.tile_images)
        weather_count = len(self.weather_images)
        
        if tile_count == 3 and weather_count >= 9:
            api_text = self.small_font.render("✅ API TigerCity + Imágenes completas (Tiles + Clima)", True, UI_SUCCESS)
        elif tile_count > 0 or weather_count > 0:
            status_parts = []
            if tile_count > 0:
                tile_types = []
                if "P" in self.tile_images: tile_types.append("Parques")
                if "C" in self.tile_images: tile_types.append("Calles")
                if "B" in self.tile_images: tile_types.append("Edificios")
                status_parts.append(f"Tiles: {', '.join(tile_types)}")
            if weather_count > 0:
                status_parts.append(f"Clima: {weather_count} estados")
            
            api_text = self.small_font.render(f"✅ API + PNG: {' | '.join(status_parts)}", True, UI_WARNING)
        else:
            api_text = self.small_font.render("✅ API TigerCity REAL + Gráficos de respaldo completos", True, UI_WARNING)
        self.screen.blit(api_text, (self.map_offset_x, self.map_offset_y - 24))

    def draw_orders(self):
        """Dibuja todos los marcadores de pedidos."""
        # Dibujar puntos de recogida
        for order in self.available_orders.items:
            if order.status in ["available", "accepted"]:
                self.draw_order_marker(order, order.pickup, "P")
        
        # Dibujar puntos de entrega para pedidos aceptados
        for order in self.available_orders.items:
            if order.status == "accepted":
                self.draw_order_marker(order, order.dropoff, "D", is_dropoff=True)
        
        # Dibujar puntos de entrega para pedidos en inventario
        for order in self.inventory:
            if order.status == "picked_up":
                self.draw_order_marker(order, order.dropoff, order.id[-2:], in_inventory=True)
    
    def draw_player(self):
        """✅ MODIFICADO: Dibuja el jugador con imagen PNG o indicadores de estado."""
        screen_x = self.player_pos.x * TILE_SIZE + self.map_offset_x + 2
        screen_y = self.player_pos.y * TILE_SIZE + self.map_offset_y + 2
        
        # ✅ NUEVO: Si hay imagen del jugador, usarla
        if self.player_image is not None:
            # Dibujar la imagen del repartidor
            image_rect = self.player_image.get_rect()
            image_rect.center = (screen_x + (TILE_SIZE - 4) // 2, screen_y + (TILE_SIZE - 4) // 2)
            self.screen.blit(self.player_image, image_rect.topleft)
            
            # ✅ NUEVO: Borde de estado según resistencia (alrededor de la imagen)
            border_rect = pygame.Rect(
                screen_x - 1, screen_y - 1,
                TILE_SIZE - 2, TILE_SIZE - 2
            )
            
            # Color del borde según estado de resistencia
            if self.stamina > 30:
                border_color = (0, 255, 0)     # Verde - Normal
                border_width = 2
            elif self.stamina > 0:
                border_color = (255, 255, 0)   # Amarillo - Cansado
                border_width = 3
            else:
                border_color = (255, 0, 0)     # Rojo - Exhausto
                border_width = 4
            
            pygame.draw.rect(self.screen, border_color, border_rect, border_width)
            
            # ✅ NUEVO: Indicador de alerta si está muy cansado (encima de la imagen)
            if self.stamina <= 30:
                alert_rect = pygame.Rect(screen_x - 2, screen_y - 8, TILE_SIZE, 4)
                alert_color = BRIGHT_RED if self.stamina <= 0 else (255, 200, 0)
                pygame.draw.rect(self.screen, alert_color, alert_rect)
                
                # Texto de estado crítico
                if self.stamina <= 0:
                    status_text = self.small_font.render("EXHAUSTO!", True, WHITE)
                    status_rect = status_text.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y - 12))
                    
                    # Fondo para el texto
                    text_bg = pygame.Rect(status_rect.x - 2, status_rect.y - 1, status_rect.width + 4, status_rect.height + 2)
                    text_bg_surface = pygame.Surface((text_bg.width, text_bg.height))
                    text_bg_surface.set_alpha(200)
                    text_bg_surface.fill((200, 0, 0))
                    self.screen.blit(text_bg_surface, text_bg)
                    
                    self.screen.blit(status_text, status_rect)
        
        else:
            # ✅ FALLBACK: Dibujar jugador con formas geométricas (método original)
            player_rect = pygame.Rect(
                screen_x, screen_y,
                TILE_SIZE - 4, TILE_SIZE - 4
            )
            
            # Color según estado de resistencia
            if self.stamina > 30:
                color = BLUE       # Normal
            elif self.stamina > 0:
                color = YELLOW     # Cansado
            else:
                color = RED        # Exhausto
            
            pygame.draw.ellipse(self.screen, color, player_rect)
            pygame.draw.ellipse(self.screen, BLACK, player_rect, 2)
            
            # Indicador de alerta si está muy cansado
            if self.stamina <= 30:
                alert_rect = pygame.Rect(screen_x - 2, screen_y - 8, TILE_SIZE, 4)
                pygame.draw.rect(self.screen, BRIGHT_RED, alert_rect)
                
                # Texto de estado crítico
                if self.stamina <= 0:
                    status_text = self.small_font.render("EXHAUSTO!", True, WHITE)
                    status_rect = status_text.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y - 12))
                    
                    # Fondo para el texto
                    text_bg = pygame.Rect(status_rect.x - 2, status_rect.y - 1, status_rect.width + 4, status_rect.height + 2)
                    text_bg_surface = pygame.Surface((text_bg.width, text_bg.height))
                    text_bg_surface.set_alpha(200)
                    text_bg_surface.fill((200, 0, 0))
                    self.screen.blit(text_bg_surface, text_bg)
                    
                    self.screen.blit(status_text, status_rect)
    
    def handle_input(self, keys, dt):
        """Maneja entrada del teclado durante el juego."""
        if self.paused or self.game_over:
            return

        # ✅ BLOQUEO COMPLETO: Si está exhausto (=0), no procesar ningún movimiento
        if self.stamina <= 0:
            current_time = time.time()
            if not hasattr(self, '_last_exhausted_message') or current_time - self._last_exhausted_message > 3.0:
                self.add_game_message("¡EXHAUSTO! Espera a recuperar resistencia hasta 30", 3.0, RED)
                self._last_exhausted_message = current_time
            return

        actual_speed = self.calculate_actual_speed()
        adjusted_cooldown = self.move_cooldown / max(0.1, actual_speed / self.base_speed)

        self.last_move_time += dt
        if self.last_move_time < adjusted_cooldown:
            return

        direction = (0, 0)
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction = (-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction = (1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            direction = (0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction = (0, 1)
        
        if direction != (0, 0):
            new_pos = Position(
                self.player_pos.x + direction[0], 
                self.player_pos.y + direction[1]
            )
            if self.is_valid_move(new_pos):
                self.move_player(new_pos)
                self.last_move_time = 0
            else:
                # ✅ Mensaje específico cuando el movimiento no es válido por resistencia
                if self.stamina <= 0:
                    self.add_game_message("No te puedes mover - ¡Estás exhausto!", 1.5, RED)

    def draw_order_marker(self, order, position, label, is_dropoff=False, in_inventory=False):
        """Dibuja un marcador individual de pedido."""
        screen_x = position.x * TILE_SIZE + self.map_offset_x + 1
        screen_y = position.y * TILE_SIZE + self.map_offset_y + 1
        
        marker_rect = pygame.Rect(screen_x, screen_y, TILE_SIZE - 2, TILE_SIZE - 2)
        
        urgency_color = self.get_order_urgency_color(order)
        time_remaining = self.get_order_time_remaining(order)
        
        # Determinar colores según estado y urgencia
        if in_inventory:
            if time_remaining <= 0:
                fill_color = (80, 40, 40)
                border_color = (120, 0, 0)
            elif urgency_color == DARK_GREEN:
                fill_color = (255, 200, 150)
                border_color = (255, 140, 0)
            elif urgency_color == YELLOW:
                fill_color = (255, 180, 255)
                border_color = (255, 100, 255)
            else:
                fill_color = (255, 100, 150)
                border_color = (255, 0, 100)
        elif is_dropoff:
            if urgency_color == DARK_GREEN:
                fill_color = (150, 200, 255)
                border_color = (0, 100, 255)
            elif urgency_color == YELLOW:
                fill_color = (180, 180, 255)
                border_color = (100, 100, 255)
            else:
                fill_color = (200, 150, 255)
                border_color = (150, 0, 255)
        else:
            if time_remaining <= 0:
                fill_color = (100, 50, 50)
                border_color = DARK_RED
            elif urgency_color == DARK_GREEN:
                fill_color = (200, 255, 200)
                border_color = DARK_GREEN
            elif urgency_color == YELLOW:
                fill_color = (255, 255, 200)
                border_color = ORANGE
            else:
                fill_color = (255, 200, 200)
                border_color = RED
        
        pygame.draw.rect(self.screen, fill_color, marker_rect)
        border_width = 3 if time_remaining <= 0 or urgency_color == RED else 2
        pygame.draw.rect(self.screen, border_color, marker_rect, border_width)
        
        # Texto del marcador
        text = self.font.render(label, True, BLACK)
        text_rect = text.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2))
        self.screen.blit(text, text_rect)
        
        # Tiempo restante si hay espacio
        if TILE_SIZE >= 28:
            time_text = self.get_order_status_text(order)
            time_surface = self.small_font.render(time_text[:6], True, BLACK)
            time_rect = time_surface.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2 + 12))
            self.screen.blit(time_surface, time_rect)

    def draw_ui(self):
        """✅ CORREGIDO: Dibuja la interfaz con controles restaurados."""
        sidebar_x = self.map_offset_x + self.map_pixel_width + 25
        sidebar_width = WINDOW_WIDTH - sidebar_x - 25
        panel_spacing = 15
        
        # Dividir el sidebar en dos columnas
        col_width = (sidebar_width - panel_spacing) // 2
        col1_x = sidebar_x
        col2_x = sidebar_x + col_width + panel_spacing
        
        # Columna 1 (Izquierda)
        y1 = 30
        self.draw_compact_header(col1_x, y1, col_width)
        y1 += 85
        self.draw_compact_stats(col1_x, y1, col_width)
        y1 += 140
        self.draw_compact_player_status(col1_x, y1, col_width)
        y1 += 140
        # ✅ Barra de reputación con dimensiones correctas
        self.draw_compact_reputation(col1_x, y1, col_width)
        y1 += 120
        # ✅ Clima con imagen ajustada
        self.draw_compact_weather(col1_x, y1, col_width)
        
        # Columna 2 (Derecha)
        y2 = 30
        self.draw_compact_legend(col2_x, y2, col_width)
        y2 += 85
        self.draw_compact_tips(col2_x, y2, col_width)
        y2 += 100
        self.draw_compact_progress(col2_x, y2, col_width)
        y2 += 90
        # ✅ RESTAURADO: Controles & Algoritmos
        self.draw_compact_controls(col2_x, y2, col_width)
    
    def draw_compact_reputation(self, x: int, y: int, width: int):
        """✅ CORREGIDO: Barra de reputación con mismas dimensiones que Estado Jugador."""
        reputation_bg = pygame.Rect(x - 8, y - 5, width + 16, 110)  # ✅ Misma altura que Estado Jugador
        pygame.draw.rect(self.screen, (240, 255, 240), reputation_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, reputation_bg, 2, border_radius=6)
        
        title = self.header_font.render("REPUTACIÓN", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # Barra de reputación horizontal
        bar_y = y + 25
        bar_width = width - 20
        bar_height = 20
        
        label = self.font.render("REPUTACIÓN:", True, UI_TEXT_NORMAL)
        self.screen.blit(label, (x + 5, bar_y))
        
        bar_bg = pygame.Rect(x + 10, bar_y + 20, bar_width - 10, bar_height)
        pygame.draw.rect(self.screen, DARK_GRAY, bar_bg, border_radius=3)
        
        reputation_progress = self.reputation / 100.0
        fill_width = max(3, int((bar_width - 10) * reputation_progress))
        
        # Colores según nivel de reputación
        if self.reputation >= 90:
            fill_color = BRIGHT_GREEN
        elif self.reputation >= 80:
            fill_color = GREEN
        elif self.reputation >= 70:
            fill_color = YELLOW
        elif self.reputation >= 50:
            fill_color = ORANGE
        elif self.reputation >= 20:
            fill_color = RED
        else:
            fill_color = DARK_RED
        
        if fill_width > 0:
            fill_rect = pygame.Rect(x + 12, bar_y + 22, fill_width - 4, bar_height - 4)
            pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=2)
        
        pygame.draw.rect(self.screen, UI_BORDER, bar_bg, 2, border_radius=3)
        
        # Texto de valor
        reputation_text = f"{self.reputation}/100"
        text_surface = self.small_font.render(reputation_text, True, BLACK)
        text_rect = text_surface.get_rect(center=(x + bar_width // 2, bar_y + 30))
        self.screen.blit(text_surface, text_rect)
        
        # Estado según reputación
        status_y = bar_y + 45
        if self.reputation < 20:
            status_text = "CRÍTICA (¡Perderás!)"
            status_color = UI_CRITICAL
        elif self.reputation >= 90:
            status_text = "EXCELENTE (+5%)"
            status_color = UI_SUCCESS
        elif self.reputation >= 80:
            status_text = "MUY BUENA"
            status_color = UI_SUCCESS
        elif self.reputation >= 70:
            status_text = "BUENA"
            status_color = UI_WARNING
        else:
            status_text = "REGULAR"
            status_color = UI_WARNING
        
        status_surface = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (x + 5, status_y))
        
        # ✅ NUEVO: Información adicional para completar el espacio
        if self.delivery_streak > 0:
            streak_text = f"Racha perfecta: {self.delivery_streak}/3"
            streak_surface = self.small_font.render(streak_text, True, UI_WARNING)
            self.screen.blit(streak_surface, (x + 5, status_y + 20))

    def draw_compact_progress(self, x: int, y: int, width: int):
        """Progreso del juego."""
        progress_bg = pygame.Rect(x - 8, y - 5, width + 16, 80)
        pygame.draw.rect(self.screen, (255, 255, 240), progress_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, progress_bg, 2, border_radius=6)
        
        title = self.header_font.render("PROGRESO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        efficiency = self.calculate_efficiency()
        
        progress_info = [
            f"Completados: {len(self.completed_orders)}",
            f"Tiempo jugado: {self.format_time(self.game_time)}",
            f"Eficiencia: {efficiency:.1f}%"
        ]
        
        for i, info in enumerate(progress_info):
            color = UI_SUCCESS if "Completados" in info else UI_TEXT_NORMAL
            text = self.small_font.render(info, True, color)
            self.screen.blit(text, (x + 5, y + 20 + i * 16))
    
    def draw_compact_stat(self, x: int, y: int, text: str, color: tuple):
        """Dibuja una estadística de forma compacta."""
        text_surface = self.small_font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))
    
    def draw_compact_tips(self, x: int, y: int, width: int):
        """Consejos basados en las reglas del documento."""
        tips_bg = pygame.Rect(x - 8, y - 5, width + 16, 90)
        pygame.draw.rect(self.screen, (240, 255, 240), tips_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, tips_bg, 2, border_radius=6)
        
        title = self.header_font.render("REGLAS DEL JUEGO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # Reglas según documento
        tips = [
            "• Resistencia >30 para moverse",
            "• 🎯 META: $3000 (Mayor desafío)",
            "• 🔥💀 P2: 8-15s | 🔥💨 P1: 10-18s | 🔥 P0: 12-22s",
            "• 💰 Mayor prioridad = Mayor pago"
        ]
        
        for i, tip in enumerate(tips):
            text = self.small_font.render(tip, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 20 + i * 15))

    def draw_inventory_overlay(self):
        """Overlay del inventario con información detallada."""
        overlay_x = self.map_offset_x + self.map_pixel_width + 40
        overlay_y = 400
        overlay_width = 650
        overlay_height = 520
        
        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.screen, UI_BACKGROUND, overlay_rect, border_radius=12)
        pygame.draw.rect(self.screen, UI_BORDER, overlay_rect, 3, border_radius=12)
        
        # Título
        title_bg = pygame.Rect(overlay_x, overlay_y, overlay_width, 45)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=12)
        title = self.large_font.render("INVENTARIO ACTUAL", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(overlay_x + overlay_width // 2, overlay_y + 22))
        self.screen.blit(title, title_rect)
        
        if not self.inventory:
            no_items_text = self.font.render("No hay pedidos en inventario", True, UI_TEXT_SECONDARY)
            text_rect = no_items_text.get_rect(center=(overlay_rect.centerx, overlay_rect.centery))
            self.screen.blit(no_items_text, text_rect)
        else:
            inventory_list = list(self.inventory)
            
            for i, order in enumerate(inventory_list[:7]):
                y_pos = overlay_rect.y + 55 + i * 65
                
                if i == self.selected_inventory_index:
                    selection_rect = pygame.Rect(overlay_rect.x + 8, y_pos - 3, overlay_width - 16, 60)
                    pygame.draw.rect(self.screen, UI_HIGHLIGHT, selection_rect, border_radius=5)
                    pygame.draw.rect(self.screen, UI_BORDER, selection_rect, 2, border_radius=5)
                
                urgency_color = self.get_order_urgency_color(order)
                time_text = self.get_order_status_text(order)
                district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                
                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"
                
                # Información del pedido
                text1 = self.font.render(f"{order.id} ({priority_text}) - {time_text}", True, urgency_color)
                self.screen.blit(text1, (overlay_rect.x + 15, y_pos))
                
                text2 = self.small_font.render(f"Peso: {order.weight}kg - Pago: ${order.payout} - {district}", True, UI_TEXT_NORMAL)
                self.screen.blit(text2, (overlay_rect.x + 15, y_pos + 20))
                
                distance = abs(order.dropoff.x - self.player_pos.x) + abs(order.dropoff.y - self.player_pos.y)
                text3 = self.small_font.render(f"Destino: ({order.dropoff.x}, {order.dropoff.y}) - Distancia: {distance} celdas", True, UI_TEXT_SECONDARY)
                self.screen.blit(text3, (overlay_rect.x + 15, y_pos + 40))
        
        # Instrucciones
        instructions_bg = pygame.Rect(overlay_x, overlay_y + overlay_height - 50, overlay_width, 45)
        pygame.draw.rect(self.screen, (240, 240, 245), instructions_bg, border_radius=12)
        
        instructions = [
            "↑/↓: Navegar | ENTER: Entregar (si estás en destino) | I: Cerrar",
            "P/T: Ordenar con QuickSort/MergeSort según algoritmos implementados"
        ]
        
        for i, instruction in enumerate(instructions):
            color = UI_SUCCESS if "algoritmos" in instruction else UI_TEXT_NORMAL
            text = self.small_font.render(instruction, True, color)
            self.screen.blit(text, (overlay_rect.x + 15, overlay_rect.y + overlay_height - 42 + i * 14))


    def draw_orders_overlay(self):
        """Overlay de pedidos con algoritmos de ordenamiento."""
        overlay_x = self.map_offset_x + self.map_pixel_width + 40
        overlay_y = 50
        overlay_width = 750
        overlay_height = 650
        
        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.screen, UI_BACKGROUND, overlay_rect, border_radius=12)
        pygame.draw.rect(self.screen, UI_BORDER, overlay_rect, 3, border_radius=12)
        
        # Título
        title_bg = pygame.Rect(overlay_x, overlay_y, overlay_width, 50)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=12)
        title = self.large_font.render("PEDIDOS - ALGORITMOS IMPLEMENTADOS", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(overlay_x + overlay_width // 2, overlay_y + 25))
        self.screen.blit(title, title_rect)
        
        if not self.available_orders.items:
            no_orders_text = self.font.render("No hay pedidos disponibles", True, UI_TEXT_SECONDARY)
            text_rect = no_orders_text.get_rect(center=(overlay_rect.centerx, overlay_rect.centery))
            self.screen.blit(no_orders_text, text_rect)
        else:
            # Mostrar pedidos disponibles
            for i, order in enumerate(self.available_orders.items[:7]):
                y_pos = overlay_rect.y + 60 + i * 80
                
                if i == self.selected_order_index:
                    selection_rect = pygame.Rect(overlay_rect.x + 8, y_pos - 3, overlay_width - 16, 75)
                    pygame.draw.rect(self.screen, UI_HIGHLIGHT, selection_rect, border_radius=5)
                    pygame.draw.rect(self.screen, UI_BORDER, selection_rect, 2, border_radius=5)
                
                urgency_color = self.get_order_urgency_color(order)
                time_text = self.get_order_status_text(order)
                
                pickup_district = self._get_district_name(order.pickup.x, order.pickup.y)
                dropoff_district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                
                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"
                
                # Información del pedido
                text1 = self.font.render(f"{order.id} ({priority_text}) - ${order.payout} | {time_text}", True, urgency_color)
                self.screen.blit(text1, (overlay_rect.x + 15, y_pos))
                
                text2 = self.small_font.render(f"Peso: {order.weight}kg | Duración: {order.duration_minutes:.1f}min", True, UI_TEXT_NORMAL)
                self.screen.blit(text2, (overlay_rect.x + 15, y_pos + 20))
                
                pickup_distance = abs(order.pickup.x - self.player_pos.x) + abs(order.pickup.y - self.player_pos.y)
                text3 = self.small_font.render(f"Recoger: ({order.pickup.x}, {order.pickup.y}) [{pickup_district}] - {pickup_distance} celdas", True, UI_TEXT_NORMAL)
                self.screen.blit(text3, (overlay_rect.x + 15, y_pos + 40))
                
                total_route_distance = abs(order.dropoff.x - order.pickup.x) + abs(order.dropoff.y - order.pickup.y)
                text4 = self.small_font.render(f"Entregar: ({order.dropoff.x}, {order.dropoff.y}) [{dropoff_district}] - Ruta: {total_route_distance} celdas", True, UI_TEXT_SECONDARY)
                self.screen.blit(text4, (overlay_rect.x + 15, y_pos + 60))
        
        # Instrucciones con algoritmos
        instructions_bg = pygame.Rect(overlay_x, overlay_y + overlay_height - 80, overlay_width, 75)
        pygame.draw.rect(self.screen, (240, 240, 245), instructions_bg, border_radius=12)
        
        instructions = [
            "↑/↓: Navegar | ENTER: Aceptar pedido | O: Cerrar",
            "",
            "🧮 ALGORITMOS DE ORDENAMIENTO IMPLEMENTADOS:",
            "D: Ordenar por DISTANCIA (Insertion Sort O(n²)) ✅",
            "Usa P/T en inventario para QuickSort/MergeSort ✅"
        ]
        
        for i, instruction in enumerate(instructions):
            if not instruction:
                continue
            if "ALGORITMOS" in instruction:
                color = UI_SUCCESS
            elif "✅" in instruction:
                color = UI_WARNING
            else:
                color = UI_TEXT_NORMAL
            
            text = self.small_font.render(instruction, True, color)
            self.screen.blit(text, (overlay_rect.x + 15, overlay_rect.y + overlay_height - 70 + i * 14))


    def draw_pause_overlay(self):
        """Overlay de pausa."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 50))
        self.screen.blit(overlay, (0, 0))
        
        pause_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, WINDOW_HEIGHT // 2 - 120, 500, 240)
        pygame.draw.rect(self.screen, UI_BACKGROUND, pause_rect, border_radius=15)
        pygame.draw.rect(self.screen, UI_BORDER, pause_rect, 4, border_radius=15)
        
        pause_text = self.title_font.render("JUEGO PAUSADO", True, UI_TEXT_HEADER)
        text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(pause_text, text_rect)
        
        instruction_text = self.large_font.render("Presiona ESPACIO para continuar", True, UI_TEXT_NORMAL)
        text_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10))
        self.screen.blit(instruction_text, text_rect)
        
        # Estado actual del juego
        state_info = [
            f"Dinero: ${self.money}/${self.goal}",
            f"Tiempo restante: {self.format_time(self.max_game_time - self.game_time)}",
            f"Reputación: {self.reputation}/100"
        ]
        
        for i, info in enumerate(state_info):
            text = self.font.render(info, True, UI_TEXT_SECONDARY)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40 + i * 25))
            self.screen.blit(text, text_rect)
    
    
    def draw_game_over_overlay(self):
        """Overlay de fin de juego con estadísticas completas."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((20, 20, 40))
        self.screen.blit(overlay, (0, 0))
        
        game_over_rect = pygame.Rect(WINDOW_WIDTH // 2 - 350, WINDOW_HEIGHT // 2 - 280, 700, 560)
        pygame.draw.rect(self.screen, UI_BACKGROUND, game_over_rect, border_radius=20)
        pygame.draw.rect(self.screen, UI_BORDER, game_over_rect, 5, border_radius=20)
        
        # Título principal
        if self.victory:
            title_text = self.title_font.render("¡VICTORIA!", True, UI_SUCCESS)
            message = f"¡Felicidades! Alcanzaste la meta de ${self.goal}"
        else:
            title_text = self.title_font.render("JUEGO TERMINADO", True, UI_CRITICAL)
            if self.reputation < 20:
                message = "Reputación demasiado baja"
            else:
                message = f"Tiempo agotado. Necesitabas ${self.goal - self.money} más"
        
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 240))
        self.screen.blit(title_text, title_rect)
        
        # Calcular y guardar puntaje final
        final_score = self._calculate_final_score()
        self.save_score(final_score)
        
        final_district = self._get_district_name(self.player_pos.x, self.player_pos.y)
        efficiency = self.calculate_efficiency()
        
        # Estadísticas finales
        stats = [
            message,
            "",
            f"PUNTAJE FINAL: {final_score}",
            f"Dinero obtenido: ${self.money} / ${self.goal}",
            f"Reputación final: {self.reputation}/100",
            f"Pedidos completados: {len(self.completed_orders)}",
            f"Eficiencia: {efficiency:.1f}%",
            f"Ciudad: {self.city_name} ({self.city_width}x{self.city_height})",
            f"Posición final: ({self.player_pos.x}, {self.player_pos.y}) - Distrito {final_district}",
            f"Mejor racha consecutiva: {getattr(self, 'best_streak', self.delivery_streak)}",
            f"Tiempo total jugado: {self.format_time(self.game_time)}"
        ]
        
        for i, stat in enumerate(stats):
            if not stat:
                continue
                
            if "PUNTAJE FINAL" in stat:
                color = UI_SUCCESS if self.victory else UI_CRITICAL
                font = self.large_font
            elif "Dinero obtenido" in stat:
                progress = (self.money / self.goal) * 100
                color = UI_SUCCESS if progress >= 100 else UI_WARNING if progress >= 80 else UI_CRITICAL
                font = self.font
            elif "Reputación" in stat:
                color = UI_SUCCESS if self.reputation >= 80 else UI_WARNING if self.reputation >= 50 else UI_CRITICAL
                font = self.font
            else:
                color = UI_TEXT_NORMAL
                font = self.font
            
            text = font.render(stat, True, color)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 180 + i * 30))
            self.screen.blit(text, text_rect)
        
        # Instrucciones de salida
        exit_text = self.font.render("Presiona ESC para salir al menú principal", True, UI_TEXT_SECONDARY)
        exit_rect = exit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 220))
        self.screen.blit(exit_text, exit_rect)
    
    def format_time(self, seconds: float) -> str:
        """Formatea el tiempo en MM:SS."""
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def calculate_efficiency(self) -> float:
        """Calcula la eficiencia del jugador."""
        if self.game_time <= 0:
            return 0.0
        
        completed = len(self.completed_orders)
        efficiency = (completed / max(1, self.game_time / 60)) * 100
        
        return min(100.0, efficiency)
    
    def run(self):
        """Bucle principal del juego."""
        last_time = time.time()
        
        print("=" * 90)
        print("🎮 COURIER QUEST - VERSIÓN CON REPARTIDOR PNG")
        print("=" * 90)
        print()
        print("🖼️ ESTADO DE IMÁGENES CARGADAS:")
        image_status = self.get_complete_image_status()
        print(f"   {image_status}")
        print()
        print("🎮 Controles del juego:")
        print("   • WASD o Flechas: Movimiento del repartidor")
        print("   • E: Interactuar con pedidos (recoger/entregar)")
        print("   • I: Inventario | O: Pedidos disponibles")
        print("   • P: Ordenar por prioridad (QuickSort)")
        print("   • T: Ordenar por tiempo (MergeSort)")
        print("   • D: Ordenar por distancia (InsertionSort)")
        print("   • F5: Guardar | F9: Cargar")
        print("   • Ctrl+Z: Deshacer movimiento")
        print("   • ESPACIO: Pausar")
        print()
        print("🔥 INDICADORES VISUALES DEL REPARTIDOR:")
        if self.player_image is not None:
            print("   • 🖼️ IMAGEN PNG: Repartidor.png cargada correctamente")
            print("   • 🟢 BORDE VERDE: Resistencia normal (>30)")
            print("   • 🟡 BORDE AMARILLO: Cansado (1-30 resistencia)")
            print("   • 🔴 BORDE ROJO: Exhausto (0 resistencia)")
            print("   • ⚠️ ALERTA ROJA: Indicador visual cuando está crítico")
        else:
            print("   • 🎨 GRÁFICO DE RESPALDO: Círculo con colores de estado")
            print("   • 🔵 AZUL: Normal | 🟡 AMARILLO: Cansado | 🔴 ROJO: Exhausto")
        print()
        
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # Limitar delta time para evitar saltos grandes
            dt = min(dt, 1.0 / 30.0)
            
            # Manejar eventos
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == "playing":
                            if self.game_over:
                                self.game_state = "menu"
                                self.game_over = False
                                self.victory = False
                            else:
                                self.paused = not self.paused
                        elif self.game_state == "menu":
                            self.running = False
            
            self.handle_events(events)
            
            # Manejar input del teclado
            if self.game_state == "playing":
                keys = pygame.key.get_pressed()
                self.handle_input(keys, dt)
            
            # Actualizar lógica del juego
            self.update(dt)
            
            # Dibujar todo
            self.draw()
            
            # Control de FPS
            self.clock.tick(FPS)
        
        pygame.quit()
    
    def draw_compact_header(self, x: int, y: int, width: int):
        """✅ MODIFICADO: Encabezado compacto con información de la API incluyendo estado del jugador."""
        header_bg = pygame.Rect(x - 8, y - 5, width + 16, 75)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, header_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, header_bg, 2, border_radius=6)
        
        # Título con nombre real de la ciudad
        title = self.large_font.render(f"COURIER QUEST - {self.city_name.upper()}", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(x + width // 2, y + 12))
        self.screen.blit(title, title_rect)
        
        # Subtítulo con información de imágenes INCLUYENDO JUGADOR
        tile_count = len(self.tile_images)
        weather_count = len(self.weather_images)
        has_player_image = self.player_image is not None
        
        if tile_count == 3 and weather_count >= 9 and has_player_image:
            subtitle = self.font.render("API REAL + IMÁGENES COMPLETAS + JUGADOR ✅", True, UI_SUCCESS)
        elif tile_count > 0 or weather_count > 0 or has_player_image:
            components = []
            if tile_count > 0:
                components.append(f"{tile_count} TILES")
            if weather_count > 0:
                components.append(f"{weather_count} CLIMA")
            if has_player_image:
                components.append("JUGADOR")
            subtitle = self.font.render(f"API + {' + '.join(components)} ✅", True, UI_SUCCESS)
        else:
            subtitle = self.font.render("API REAL + GRÁFICOS DE RESPALDO ⚠️", True, UI_WARNING)
        subtitle_rect = subtitle.get_rect(center=(x + width // 2, y + 32))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Meta
        progress = (self.money / self.goal) * 100
        meta_color = UI_SUCCESS if progress >= 100 else UI_WARNING if progress >= 80 else UI_CRITICAL
        meta_text = f"Meta: ${self.money}/${self.goal} ({progress:.1f}%)"
        meta = self.small_font.render(meta_text, True, meta_color)
        meta_rect = meta.get_rect(center=(x + width // 2, y + 52))
        self.screen.blit(meta, meta_rect)
    
    def draw_compact_stats(self, x: int, y: int, width: int):
        """Estadísticas principales con reglas exactas."""
        stats_bg = pygame.Rect(x - 8, y - 5, width + 16, 130)
        pygame.draw.rect(self.screen, (250, 250, 255), stats_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, stats_bg, 2, border_radius=6)
        
        title = self.header_font.render("ESTADÍSTICAS", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        stats_y = y + 25
        col_left = x + 5
        col_right = x + width // 2 + 5
        
        # Columna izquierda
        rep_color = UI_SUCCESS if self.reputation >= 80 else UI_WARNING if self.reputation >= 50 else UI_CRITICAL
        self.draw_compact_stat(col_left, stats_y, f"Reputación: {self.reputation}/100", rep_color)
        
        time_left = self.max_game_time - self.game_time
        time_color = UI_SUCCESS if time_left > 300 else UI_WARNING if time_left > 120 else UI_CRITICAL
        self.draw_compact_stat(col_left, stats_y + 20, f"Tiempo: {self.format_time(time_left)}", time_color)
        
        district = self._get_district_name(self.player_pos.x, self.player_pos.y)
        self.draw_compact_stat(col_left, stats_y + 40, f"Distrito: {district}", BLUE)
        
        speed = self.calculate_actual_speed()
        speed_color = UI_SUCCESS if speed >= 2.5 else UI_WARNING if speed >= 2.0 else UI_CRITICAL
        self.draw_compact_stat(col_left, stats_y + 60, f"Velocidad: {speed:.1f} c/s", speed_color)
        
        # Columna derecha
        inv_weight = sum(order.weight for order in self.inventory)
        inv_color = UI_WARNING if inv_weight >= self.max_weight * 0.8 else UI_TEXT_NORMAL
        self.draw_compact_stat(col_right, stats_y, f"Inventario: {inv_weight}/{self.max_weight}kg", inv_color)
        
        active_orders = self.available_orders.size()
        orders_color = UI_SUCCESS if active_orders > 0 else UI_TEXT_SECONDARY
        self.draw_compact_stat(col_right, stats_y + 20, f"Activos: {active_orders}/10", orders_color)
        
        self.draw_compact_stat(col_right, stats_y + 40, f"Pendientes: {len(self.pending_orders)}", UI_TEXT_NORMAL)
        self.draw_compact_stat(col_right, stats_y + 60, f"Completados: {len(self.completed_orders)}", UI_SUCCESS)
    
    
    def draw_compact_player_status(self, x: int, y: int, width: int):
        """Estado del jugador con reglas exactas del documento."""
        status_bg = pygame.Rect(x - 8, y - 5, width + 16, 110)
        pygame.draw.rect(self.screen, (255, 250, 240), status_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, status_bg, 2, border_radius=6)
        
        title = self.header_font.render("ESTADO JUGADOR", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # Barra de resistencia
        bar_y = y + 25
        bar_width = width - 20
        bar_height = 20
        
        label = self.font.render("RESISTENCIA:", True, UI_TEXT_NORMAL)
        self.screen.blit(label, (x + 5, bar_y))
        
        bar_bg = pygame.Rect(x + 10, bar_y + 20, bar_width - 10, bar_height)
        pygame.draw.rect(self.screen, DARK_GRAY, bar_bg, border_radius=3)
        
        stamina_progress = self.stamina / self.max_stamina
        fill_width = max(3, int((bar_width - 10) * stamina_progress))
        
        # ✅ CORREGIDO: Colores según umbrales del documento
        if self.stamina > 30:  # >30: Normal
            fill_color = UI_SUCCESS
        elif self.stamina > 0:  # 1-30: Cansado
            fill_color = UI_WARNING
        else:  # 0: Exhausto
            fill_color = UI_CRITICAL
        
        if fill_width > 0:
            fill_rect = pygame.Rect(x + 12, bar_y + 22, fill_width - 4, bar_height - 4)
            pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=2)
        
        # ✅ Línea indicadora del umbral de 30
        threshold_x = x + 10 + int((30 / self.max_stamina) * (bar_width - 10))
        pygame.draw.line(self.screen, (255, 100, 100), 
                        (threshold_x, bar_y + 20), 
                        (threshold_x, bar_y + 20 + bar_height), 2)
        
        pygame.draw.rect(self.screen, UI_BORDER, bar_bg, 2, border_radius=3)
        
        # Texto de estado
        stamina_text = f"{self.stamina:.0f}/{self.max_stamina}"
        text_surface = self.small_font.render(stamina_text, True, BLACK)
        text_rect = text_surface.get_rect(center=(x + bar_width // 2, bar_y + 30))
        self.screen.blit(text_surface, text_rect)
        
        # ✅ CORREGIDO: Estado según documento - EXHAUSTO no se mueve hasta 30
        status_y = bar_y + 45
        if self.stamina <= 0:
            status_text = "EXHAUSTO (¡BLOQUEADO!)"
            status_color = UI_CRITICAL
        elif self.stamina <= 30:
            status_text = f"CANSADO ({self.stamina:.0f}/30)"
            status_color = UI_WARNING
        else:
            status_text = "NORMAL"
            status_color = UI_SUCCESS
        
        status_surface = self.font.render(status_text, True, status_color)
        self.screen.blit(status_surface, (x + 5, status_y))
        
        # ✅ NUEVO: Indicador de recuperación necesaria
        if self.stamina <= 0:
            recovery_text = "Recupera hasta 30 para moverte"
            recovery_surface = self.small_font.render(recovery_text, True, UI_CRITICAL)
            self.screen.blit(recovery_surface, (x + 5, status_y + 20))
        elif self.stamina <= 30:
            recovery_text = f"Para moverte: {30 - self.stamina:.0f} más"
            recovery_surface = self.small_font.render(recovery_text, True, UI_WARNING)
            self.screen.blit(recovery_surface, (x + 5, status_y + 20))
        
        # Racha perfecta
        if self.delivery_streak > 0 and self.stamina > 0:
            streak_text = f"Racha: {self.delivery_streak}/3"
            streak_surface = self.small_font.render(streak_text, True, UI_WARNING)
            self.screen.blit(streak_surface, (x + width - 80, status_y))
    
    def draw_compact_weather(self, x: int, y: int, width: int):
        """✅ CORREGIDO: Indicador del clima con imagen ajustada al marco."""
        weather_bg = pygame.Rect(x - 8, y - 5, width + 16, 110)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, weather_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, weather_bg, 2, border_radius=6)
        
        title = self.header_font.render("CLIMA DINÁMICO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # ✅ IMAGEN DEL CLIMA AJUSTADA AL MARCO
        current_weather = self.weather_system.current_condition
        image_size = 75  # Tamaño ajustado para que quepa bien en el marco
        weather_image_pos = (x + 12, y + 27)  # Posición ajustada
        
        if current_weather in self.weather_images:
            # Redimensionar la imagen para que se ajuste perfectamente
            scaled_image = pygame.transform.scale(self.weather_images[current_weather], (image_size, image_size))
            self.screen.blit(scaled_image, weather_image_pos)
            
            # Marco alrededor de la imagen ajustado
            image_rect = pygame.Rect(weather_image_pos[0], weather_image_pos[1], image_size, image_size)
            pygame.draw.rect(self.screen, UI_BORDER, image_rect, 2, border_radius=5)
        else:
            # Respaldo: círculo de color ajustado
            weather_color = self.weather_system.get_weather_color()
            circle_rect = pygame.Rect(weather_image_pos[0], weather_image_pos[1], image_size, image_size)
            pygame.draw.ellipse(self.screen, weather_color, circle_rect)
            pygame.draw.ellipse(self.screen, UI_BORDER, circle_rect, 2)
        
        # Información del clima (texto posicionado correctamente)
        weather_name = self.weather_system.get_weather_description()
        name_text = self.font.render(weather_name, True, UI_TEXT_NORMAL)
        self.screen.blit(name_text, (x + image_size + 25, y + 27))
        
        # Efectos según multiplicadores del documento
        speed_mult = self.weather_system.get_speed_multiplier()
        stamina_penalty = self.weather_system.get_stamina_penalty()
        
        speed_color = UI_SUCCESS if speed_mult >= 0.9 else UI_WARNING if speed_mult >= 0.8 else UI_CRITICAL
        stamina_color = UI_SUCCESS if stamina_penalty <= 0.05 else UI_WARNING if stamina_penalty <= 0.1 else UI_CRITICAL
        
        speed_text = f"Velocidad: {speed_mult:.0%}"
        stamina_text = f"Resistencia: -{stamina_penalty*100:.0f}%"
        
        speed_surface = self.small_font.render(speed_text, True, speed_color)
        stamina_surface = self.small_font.render(stamina_text, True, stamina_color)
        
        # Posiciones ajustadas para el texto
        self.screen.blit(speed_surface, (x + image_size + 25, y + 50))
        self.screen.blit(stamina_surface, (x + image_size + 25, y + 70))
    
    def draw_compact_legend(self, x: int, y: int, width: int):
        """Leyenda del mapa con reglas del juego."""
        legend_bg = pygame.Rect(x - 8, y - 5, width + 16, 75)
        pygame.draw.rect(self.screen, (255, 255, 240), legend_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, legend_bg, 2, border_radius=6)
        
        title = self.header_font.render("LEYENDA DEL MAPA", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # Elementos con información de imágenes completa
        items = [
            ("Calles", LIGHT_GRAY, "🖼️ PNG" if "C" in self.tile_images else "Caminable"),
            ("Parques", GREEN, "🖼️ PNG +15/s" if "P" in self.tile_images else "Recupera +15/s"),
            ("Edificios", DARK_GRAY, "🖼️ PNG" if "B" in self.tile_images else "BLOQUEADO"),
            ("Descanso", PURPLE, "Recupera +15/s")
        ]
        
        for i, (name, color, desc) in enumerate(items):
            row = i % 2
            col = i // 2
            item_x = x + 5 + col * (width // 2)
            item_y = y + 20 + row * 18
            
            color_rect = pygame.Rect(item_x, item_y, 10, 10)
            pygame.draw.rect(self.screen, color, color_rect)
            pygame.draw.rect(self.screen, UI_BORDER, color_rect, 1)
            
            # Color especial para tiles con imágenes
            if "🖼️" in desc:
                text = self.small_font.render(f"{name}", True, UI_SUCCESS)
            else:
                text = self.small_font.render(f"{name}", True, UI_TEXT_NORMAL)
            self.screen.blit(text, (item_x + 15, item_y - 2))
    
    def draw_compact_controls(self, x: int, y: int, width: int):
        """✅ CORREGIDO: Controles únicos sin duplicación."""
        controls_bg = pygame.Rect(x - 8, y - 5, width + 16, 230)
        pygame.draw.rect(self.screen, (240, 245, 255), controls_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, controls_bg, 2, border_radius=6)
        
        title = self.header_font.render("CONTROLES & ALGORITMOS", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # Algoritmos implementados
        algo_title = self.font.render("Algoritmos:", True, UI_SUCCESS)
        self.screen.blit(algo_title, (x + 5, y + 25))
        
        algorithms = [
            "P: Prioridad (QuickSort)",
            "T: Tiempo (MergeSort)", 
            "D: Distancia (InsertionSort)"
        ]
        
        for i, algo in enumerate(algorithms):
            text = self.small_font.render(algo, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 45 + i * 16))
        
        # Controles principales
        control_title = self.font.render("Controles:", True, UI_TEXT_HEADER)
        self.screen.blit(control_title, (x + 5, y + 105))
        
        controls = [
            "WASD/Flechas: Moverse | E: Interactuar",
            "I: Inventario | O: Pedidos",
            "F5: Guardar | F9: Cargar",
            "B: Volver (menú cargar)",
            "P/T/D: Algoritmos de ordenamiento"
        ]
        
        for i, control in enumerate(controls):
            text = self.small_font.render(control, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 125 + i * 16))

      

    def draw_compact_progress(self, x: int, y: int, width: int):
        """Progreso del juego."""
        progress_bg = pygame.Rect(x - 8, y - 5, width + 16, 80)
        pygame.draw.rect(self.screen, (255, 255, 240), progress_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, progress_bg, 2, border_radius=6)
        
        title = self.header_font.render("PROGRESO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        efficiency = self.calculate_efficiency()
        
        progress_info = [
            f"Completados: {len(self.completed_orders)}",
            f"Tiempo jugado: {self.format_time(self.game_time)}",
            f"Eficiencia: {efficiency:.1f}%"
        ]
        
        for i, info in enumerate(progress_info):
            color = UI_SUCCESS if "Completados" in info else UI_TEXT_NORMAL
            text = self.small_font.render(info, True, color)
            self.screen.blit(text, (x + 5, y + 20 + i * 16))
    
    def draw_compact_stat(self, x: int, y: int, text: str, color: tuple):
        """Dibuja una estadística de forma compacta."""
        text_surface = self.small_font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))
    
    def draw_compact_tips(self, x: int, y: int, width: int):
        """Consejos basados en las reglas del documento."""
        tips_bg = pygame.Rect(x - 8, y - 5, width + 16, 90)
        pygame.draw.rect(self.screen, (240, 255, 240), tips_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, tips_bg, 2, border_radius=6)
        
        title = self.header_font.render("REGLAS DEL JUEGO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        # Reglas según documento
        tips = [
            "• Resistencia >30 para moverse",
            "• 🎯 META: $3000 (Mayor desafío)",
            "• 🔥💀 P2: 8-15s | 🔥💨 P1: 10-18s | 🔥 P0: 12-22s",
            "• 💰 Mayor prioridad = Mayor pago"
        ]
        
        for i, tip in enumerate(tips):
            text = self.small_font.render(tip, True, UI_TEXT_NORMAL)
            self.screen.blit(text, (x + 5, y + 20 + i * 15))
    
    def draw_compact_progress(self, x: int, y: int, width: int):
        """Progreso del juego."""
        progress_bg = pygame.Rect(x - 8, y - 5, width + 16, 80)
        pygame.draw.rect(self.screen, (255, 255, 240), progress_bg, border_radius=6)
        pygame.draw.rect(self.screen, UI_BORDER, progress_bg, 2, border_radius=6)
        
        title = self.header_font.render("PROGRESO", True, UI_TEXT_HEADER)
        self.screen.blit(title, (x + 5, y))
        
        efficiency = self.calculate_efficiency()
        
        progress_info = [
            f"Completados: {len(self.completed_orders)}",
            f"Tiempo jugado: {self.format_time(self.game_time)}",
            f"Eficiencia: {efficiency:.1f}%"
        ]
        
        for i, info in enumerate(progress_info):
            color = UI_SUCCESS if "Completados" in info else UI_TEXT_NORMAL
            text = self.small_font.render(info, True, color)
            self.screen.blit(text, (x + 5, y + 20 + i * 16))
    
    def draw_compact_stat(self, x: int, y: int, text: str, color: tuple):
        """Dibuja una estadística de forma compacta."""
        text_surface = self.small_font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))

    def draw_inventory_overlay(self):
        """Overlay del inventario con información detallada."""
        overlay_x = self.map_offset_x + self.map_pixel_width + 40
        overlay_y = 400
        overlay_width = 650
        overlay_height = 520
        
        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.screen, UI_BACKGROUND, overlay_rect, border_radius=12)
        pygame.draw.rect(self.screen, UI_BORDER, overlay_rect, 3, border_radius=12)
        
        # Título
        title_bg = pygame.Rect(overlay_x, overlay_y, overlay_width, 45)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=12)
        title = self.large_font.render("INVENTARIO ACTUAL", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(overlay_x + overlay_width // 2, overlay_y + 22))
        self.screen.blit(title, title_rect)
        
        if not self.inventory:
            no_items_text = self.font.render("No hay pedidos en inventario", True, UI_TEXT_SECONDARY)
            text_rect = no_items_text.get_rect(center=(overlay_rect.centerx, overlay_rect.centery))
            self.screen.blit(no_items_text, text_rect)
        else:
            inventory_list = list(self.inventory)
            
            for i, order in enumerate(inventory_list[:7]):
                y_pos = overlay_rect.y + 55 + i * 65
                
                if i == self.selected_inventory_index:
                    selection_rect = pygame.Rect(overlay_rect.x + 8, y_pos - 3, overlay_width - 16, 60)
                    pygame.draw.rect(self.screen, UI_HIGHLIGHT, selection_rect, border_radius=5)
                    pygame.draw.rect(self.screen, UI_BORDER, selection_rect, 2, border_radius=5)
                
                urgency_color = self.get_order_urgency_color(order)
                time_text = self.get_order_status_text(order)
                district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                
                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"
                
                # Información del pedido
                text1 = self.font.render(f"{order.id} ({priority_text}) - {time_text}", True, urgency_color)
                self.screen.blit(text1, (overlay_rect.x + 15, y_pos))
                
                text2 = self.small_font.render(f"Peso: {order.weight}kg - Pago: ${order.payout} - {district}", True, UI_TEXT_NORMAL)
                self.screen.blit(text2, (overlay_rect.x + 15, y_pos + 20))
                
                distance = abs(order.dropoff.x - self.player_pos.x) + abs(order.dropoff.y - self.player_pos.y)
                text3 = self.small_font.render(f"Destino: ({order.dropoff.x}, {order.dropoff.y}) - Distancia: {distance} celdas", True, UI_TEXT_SECONDARY)
                self.screen.blit(text3, (overlay_rect.x + 15, y_pos + 40))
        
        # Instrucciones
        instructions_bg = pygame.Rect(overlay_x, overlay_y + overlay_height - 50, overlay_width, 45)
        pygame.draw.rect(self.screen, (240, 240, 245), instructions_bg, border_radius=12)
        
        instructions = [
            "↑/↓: Navegar | ENTER: Entregar (si estás en destino) | I: Cerrar",
            "P/T: Ordenar con QuickSort/MergeSort según algoritmos implementados"
        ]
        
        for i, instruction in enumerate(instructions):
            color = UI_SUCCESS if "algoritmos" in instruction else UI_TEXT_NORMAL
            text = self.small_font.render(instruction, True, color)
            self.screen.blit(text, (overlay_rect.x + 15, overlay_rect.y + overlay_height - 42 + i * 14))

    def draw_orders_overlay(self):
        """Overlay de pedidos con algoritmos de ordenamiento."""
        overlay_x = self.map_offset_x + self.map_pixel_width + 40
        overlay_y = 50
        overlay_width = 750
        overlay_height = 650
        
        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.screen, UI_BACKGROUND, overlay_rect, border_radius=12)
        pygame.draw.rect(self.screen, UI_BORDER, overlay_rect, 3, border_radius=12)
        
        # Título
        title_bg = pygame.Rect(overlay_x, overlay_y, overlay_width, 50)
        pygame.draw.rect(self.screen, UI_HIGHLIGHT, title_bg, border_radius=12)
        title = self.large_font.render("PEDIDOS - ALGORITMOS IMPLEMENTADOS", True, UI_TEXT_HEADER)
        title_rect = title.get_rect(center=(overlay_x + overlay_width // 2, overlay_y + 25))
        self.screen.blit(title, title_rect)
        
        if not self.available_orders.items:
            no_orders_text = self.font.render("No hay pedidos disponibles", True, UI_TEXT_SECONDARY)
            text_rect = no_orders_text.get_rect(center=(overlay_rect.centerx, overlay_rect.centery))
            self.screen.blit(no_orders_text, text_rect)
        else:
            # Mostrar pedidos disponibles
            for i, order in enumerate(self.available_orders.items[:7]):
                y_pos = overlay_rect.y + 60 + i * 80
                
                if i == self.selected_order_index:
                    selection_rect = pygame.Rect(overlay_rect.x + 8, y_pos - 3, overlay_width - 16, 75)
                    pygame.draw.rect(self.screen, UI_HIGHLIGHT, selection_rect, border_radius=5)
                    pygame.draw.rect(self.screen, UI_BORDER, selection_rect, 2, border_radius=5)
                
                urgency_color = self.get_order_urgency_color(order)
                time_text = self.get_order_status_text(order)
                
                pickup_district = self._get_district_name(order.pickup.x, order.pickup.y)
                dropoff_district = self._get_district_name(order.dropoff.x, order.dropoff.y)
                
                priority_text = f"P{order.priority}" if order.priority > 0 else "Normal"
                
                # Información del pedido
                text1 = self.font.render(f"{order.id} ({priority_text}) - ${order.payout} | {time_text}", True, urgency_color)
                self.screen.blit(text1, (overlay_rect.x + 15, y_pos))
                
                text2 = self.small_font.render(f"Peso: {order.weight}kg | Duración: {order.duration_minutes:.1f}min", True, UI_TEXT_NORMAL)
                self.screen.blit(text2, (overlay_rect.x + 15, y_pos + 20))
                
                pickup_distance = abs(order.pickup.x - self.player_pos.x) + abs(order.pickup.y - self.player_pos.y)
                text3 = self.small_font.render(f"Recoger: ({order.pickup.x}, {order.pickup.y}) [{pickup_district}] - {pickup_distance} celdas", True, UI_TEXT_NORMAL)
                self.screen.blit(text3, (overlay_rect.x + 15, y_pos + 40))
                
                total_route_distance = abs(order.dropoff.x - order.pickup.x) + abs(order.dropoff.y - order.pickup.y)
                text4 = self.small_font.render(f"Entregar: ({order.dropoff.x}, {order.dropoff.y}) [{dropoff_district}] - Ruta: {total_route_distance} celdas", True, UI_TEXT_SECONDARY)
                self.screen.blit(text4, (overlay_rect.x + 15, y_pos + 60))
        
        # Instrucciones con algoritmos
        instructions_bg = pygame.Rect(overlay_x, overlay_y + overlay_height - 80, overlay_width, 75)
        pygame.draw.rect(self.screen, (240, 240, 245), instructions_bg, border_radius=12)
        
        instructions = [
            "↑/↓: Navegar | ENTER: Aceptar pedido | O: Cerrar",
            "",
            "🧮 ALGORITMOS DE ORDENAMIENTO IMPLEMENTADOS:",
            "D: Ordenar por DISTANCIA (Insertion Sort O(n²)) ✅",
            "Usa P/T en inventario para QuickSort/MergeSort ✅"
        ]
        
        for i, instruction in enumerate(instructions):
            if not instruction:
                continue
            if "ALGORITMOS" in instruction:
                color = UI_SUCCESS
            elif "✅" in instruction:
                color = UI_WARNING
            else:
                color = UI_TEXT_NORMAL
            
            text = self.small_font.render(instruction, True, color)
            self.screen.blit(text, (overlay_rect.x + 15, overlay_rect.y + overlay_height - 70 + i * 14))

    def draw_pause_overlay(self):
        """Overlay de pausa."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 50))
        self.screen.blit(overlay, (0, 0))
        
        pause_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, WINDOW_HEIGHT // 2 - 120, 500, 240)
        pygame.draw.rect(self.screen, UI_BACKGROUND, pause_rect, border_radius=15)
        pygame.draw.rect(self.screen, UI_BORDER, pause_rect, 4, border_radius=15)
        
        pause_text = self.title_font.render("JUEGO PAUSADO", True, UI_TEXT_HEADER)
        text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40))
        self.screen.blit(pause_text, text_rect)
        
        instruction_text = self.large_font.render("Presiona ESPACIO para continuar", True, UI_TEXT_NORMAL)
        text_rect = instruction_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10))
        self.screen.blit(instruction_text, text_rect)
        
        # Estado actual del juego
        state_info = [
            f"Dinero: ${self.money}/${self.goal}",
            f"Tiempo restante: {self.format_time(self.max_game_time - self.game_time)}",
            f"Reputación: {self.reputation}/100"
        ]
        
        for i, info in enumerate(state_info):
            text = self.font.render(info, True, UI_TEXT_SECONDARY)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 40 + i * 25))
            self.screen.blit(text, text_rect)
    
    def draw_game_over_overlay(self):
        """Overlay de fin de juego con estadísticas completas."""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)
        overlay.fill((20, 20, 40))
        self.screen.blit(overlay, (0, 0))
        
        game_over_rect = pygame.Rect(WINDOW_WIDTH // 2 - 350, WINDOW_HEIGHT // 2 - 280, 700, 560)
        pygame.draw.rect(self.screen, UI_BACKGROUND, game_over_rect, border_radius=20)
        pygame.draw.rect(self.screen, UI_BORDER, game_over_rect, 5, border_radius=20)
        
        # Título principal
        if self.victory:
            title_text = self.title_font.render("¡VICTORIA!", True, UI_SUCCESS)
            message = f"¡Felicidades! Alcanzaste la meta de ${self.goal}"
        else:
            title_text = self.title_font.render("JUEGO TERMINADO", True, UI_CRITICAL)
            if self.reputation < 20:
                message = "Reputación demasiado baja"
            else:
                message = f"Tiempo agotado. Necesitabas ${self.goal - self.money} más"
        
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 240))
        self.screen.blit(title_text, title_rect)
        
        # Calcular y guardar puntaje final
        final_score = self._calculate_final_score()
        self.save_score(final_score)
        
        final_district = self._get_district_name(self.player_pos.x, self.player_pos.y)
        efficiency = self.calculate_efficiency()
        
        # Estadísticas finales
        stats = [
            message,
            "",
            f"PUNTAJE FINAL: {final_score}",
            f"Dinero obtenido: ${self.money} / ${self.goal}",
            f"Reputación final: {self.reputation}/100",
            f"Pedidos completados: {len(self.completed_orders)}",
            f"Eficiencia: {efficiency:.1f}%",
            f"Ciudad: {self.city_name} ({self.city_width}x{self.city_height})",
            f"Posición final: ({self.player_pos.x}, {self.player_pos.y}) - Distrito {final_district}",
            f"Mejor racha consecutiva: {getattr(self, 'best_streak', self.delivery_streak)}",
            f"Tiempo total jugado: {self.format_time(self.game_time)}"
        ]
        
        for i, stat in enumerate(stats):
            if not stat:
                continue
                
            if "PUNTAJE FINAL" in stat:
                color = UI_SUCCESS if self.victory else UI_CRITICAL
                font = self.large_font
            elif "Dinero obtenido" in stat:
                progress = (self.money / self.goal) * 100
                color = UI_SUCCESS if progress >= 100 else UI_WARNING if progress >= 80 else UI_CRITICAL
                font = self.font
            elif "Reputación" in stat:
                color = UI_SUCCESS if self.reputation >= 80 else UI_WARNING if self.reputation >= 50 else UI_CRITICAL
                font = self.font
            else:
                color = UI_TEXT_NORMAL
                font = self.font
            
            text = font.render(stat, True, color)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 180 + i * 30))
            self.screen.blit(text, text_rect)
        
        # Instrucciones de salida
        exit_text = self.font.render("Presiona ESC para salir al menú principal", True, UI_TEXT_SECONDARY)
        exit_rect = exit_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 220))
        self.screen.blit(exit_text, exit_rect)
    
    def format_time(self, seconds: float) -> str:
        """Formatea el tiempo en MM:SS."""
        if seconds < 0:
            seconds = 0
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def calculate_efficiency(self) -> float:
        """Calcula la eficiencia del jugador."""
        if self.game_time <= 0:
            return 0.0
        
        completed = len(self.completed_orders)
        efficiency = (completed / max(1, self.game_time / 60)) * 100
        
        return min(100.0, efficiency)
    
    def run(self):
        """Bucle principal del juego."""
        last_time = time.time()
        
        print("=" * 90)
        print("🎮 COURIER QUEST - VERSIÓN CORREGIDA")
        print("   ✅ API REAL de TigerCity funcionando correctamente")
        print("   ✅ CORRECCIÓN: Mapa se posiciona correctamente (no se corta)")
        print("   ✅ CORRECCIÓN: Guardado/carga incluye todos los datos del mapa")
        print("   ✅ CORRECCIÓN: Más pedidos generados para fluidez del juego")
        print("   ✅ Todas las reglas de jugabilidad implementadas")
        print("   ✅ Algoritmos de ordenamiento: QuickSort, MergeSort, InsertionSort")
        print("   ✅ Sistema de clima dinámico con cadenas de Markov")
        print("   ✅ Validación completa de posiciones y reglas del documento")
        print("=" * 90)
        
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            # Limitar delta time para evitar saltos grandes
            dt = min(dt, 1.0 / 30.0)
            
            # Manejar eventos
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state == "playing":
                            if self.game_over:
                                self.game_state = "menu"
                                self.game_over = False
                                self.victory = False
                            else:
                                self.paused = not self.paused
                        elif self.game_state == "menu":
                            self.running = False
            
            self.handle_events(events)
            
            # Manejar input del teclado
            if self.game_state == "playing":
                keys = pygame.key.get_pressed()
                self.handle_input(keys, dt)
            
            # Actualizar lógica del juego
            self.update(dt)
            
            # Dibujar todo
            self.draw()
            
            # Control de FPS
            self.clock.tick(FPS)
        
        pygame.quit()

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================
def main():
    """Función principal del programa."""
    print("=" * 90)
    print("🚀 COURIER QUEST - VERSIÓN ULTRA VELOCIDAD")
    print("   Proyecto EIF-207 Estructuras de Datos")
    print("   API REAL + EXTREMA URGENCIA (30 SEGUNDOS)")
    print("=" * 90)
    print()
    print("🔥💨 MEJORAS DE VELOCIDAD EXTREMA:")
    print("   ⚡ DURACIÓN ULTRA CORTA: Solo 18-48 segundos por pedido!")
    print("   🚀 ACCIÓN MÁXIMA: Hasta 30 pedidos activos simultáneamente")
    print("   🌊 OLEADAS EXTREMAS: Hasta 5 pedidos liberados a la vez")
    print("   💰 COMPENSACIÓN PREMIUM: $150-400 por extrema urgencia")
    print("   🎯 ALTA PRIORIDAD: 60% de pedidos prioritarios")
    print("   🔥💨 INDICADORES CRÍTICOS: Emojis de urgencia extrema")
    print("   ⚡ PESO REDUCIDO: Máximo 3kg para movimiento rápido")
    print("   📱 MENSAJES CORTOS: 2 segundos de duración")
    print()
    print("🔗 Todas las correcciones anteriores mantenidas:")
    print("   ✅ MAPA: Posición corregida (ya no se corta)")
    print("   ✅ GUARDADO/CARGA: Incluye todos los datos del mapa")
    print("   ✅ API Real de TigerCity integrada correctamente")
    print("   ✅ Validación completa de posiciones (NO pedidos en edificios)")
    print("   ✅ Todas las reglas del documento implementadas")
    print("   ✅ Sistema de resistencia con umbrales exactos (30/0)")
    print("   ✅ Fórmula de velocidad oficial del documento")
    print("   ✅ Sistema de reputación con reglas exactas")
    print("   ✅ Algoritmos: QuickSort, MergeSort, InsertionSort")
    print("   ✅ Sistema de clima dinámico con cadenas de Markov")
    print("   ✅ Gestión completa de archivos y guardado")
    print("   ✅ Condiciones de victoria/derrota según documento")
    print()
    print("🎮 Controles del juego:")
    print("   • WASD o Flechas: Movimiento")
    print("   • E: Interactuar con pedidos")
    print("   • I: Inventario | O: Pedidos disponibles")
    print("   • P: Ordenar por prioridad (QuickSort)")
    print("   • T: Ordenar por tiempo (MergeSort)")
    print("   • D: Ordenar por distancia (InsertionSort)")
    print("   • F5: Guardar | F9: Cargar")
    print("   • Ctrl+Z: Deshacer movimiento")
    print("   • ESPACIO: Pausar")
    print()
    
    try:
        game = CourierQuest()
        game.run()
        
    except Exception as e:
        print(f"Error ejecutando el juego: {e}")
        import traceback
        traceback.print_exc()
        input("Presiona ENTER para salir...")

if __name__ == "__main__":
    main()
