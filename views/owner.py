# views/owner.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, request
from models.restaurant import RestaurantModel
from models.dish import DishModel
from models.daily_menu import DailyMenuModel
from models.user import UserModel
from config import Config
from functools import wraps
from datetime import datetime
import random
import json
import os
import logging

logger = logging.getLogger(__name__)

owner_bp = Blueprint('owner', __name__, url_prefix='/owner')

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('auth.login'))
        
        user = session.get('user')
        if user.get('role') != 'business_owner':
            flash('Acceso denegado. Se requieren permisos de empresario.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

@owner_bp.route('/dashboard')
@owner_required
def dashboard():
    """Panel de empresario - Solo ve sus restaurantes"""
    user = session.get('user')
    user_id = user.get('id')
    
    restaurants = RestaurantModel.get_by_owner(user_id)
    
    # Agregar nombre de categoría a cada restaurante
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        try:
            with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except:
            categories = []
    
    cat_dict = {cat['id']: cat['name'] for cat in categories}
    for r in restaurants:
        r['category_name'] = cat_dict.get(r.get('category_id'), 'Sin categoría')
    
    total_rest = len(restaurants)
    avg_rating = sum(r.get('rating', 0) for r in restaurants) / total_rest if total_rest > 0 else 0
    total_promos = sum(1 for r in restaurants if r.get('promo'))
    
    # Actividad reciente
    recent_activities = []
    if restaurants:
        latest = sorted(restaurants, key=lambda x: x.get('id', 0), reverse=True)[:3]
        for r in latest:
            recent_activities.append({
                'icon': 'plus',
                'message': f'Actualizaste "{r.get("name")}"',
                'time': 'Recientemente'
            })
    
    if len(recent_activities) < 3:
        recent_activities.append({
            'icon': 'star',
            'message': f'Rating promedio: {avg_rating:.1f} ⭐',
            'time': 'General'
        })
    
    return render_template('owner/dashboard.html',
                         restaurants=restaurants,
                         total_rest=total_rest,
                         avg_rating=round(avg_rating, 2),
                         total_promos=total_promos,
                         recent_activities=recent_activities)

@owner_bp.route('/menu/<int:restaurant_id>')
@owner_required
def menu_management(restaurant_id):
    """Gestión de menú para un restaurante específico"""
    user = session.get('user')
    user_id = user.get('id')
    
    if not RestaurantModel.is_owner(user_id, restaurant_id):
        flash('No tienes permiso para gestionar este restaurante', 'error')
        return redirect(url_for('owner.dashboard'))
    
    restaurant = RestaurantModel.get_by_id(restaurant_id)
    if not restaurant:
        flash('Restaurante no encontrado', 'error')
        return redirect(url_for('owner.dashboard'))
    
    dishes = DishModel.get_by_restaurant(restaurant_id)
    today_menu = DailyMenuModel.get_active(restaurant_id)
    
    return render_template('owner/menu_management.html',
                         restaurant=restaurant,
                         dishes=dishes,
                         today_menu=today_menu)

@owner_bp.route('/dish/add', methods=['POST'])
@owner_required
def add_dish():
    """Agregar un nuevo plato a la carta del restaurante"""
    try:
        user_id = session['user'].get('id')
        data = request.json
        restaurant_id = data.get('restaurant_id')
        
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        dish_data = {
            'restaurant_id': restaurant_id,
            'name': data.get('name'),
            'price': data.get('price'),
            'category': data.get('category'),
            'description': data.get('description', ''),
            'ingredients': data.get('ingredients', []),
            'dietary_info': data.get('dietary_info', []),
            'preparation_time': data.get('preparation_time', 20),
            'spiciness': data.get('spiciness', 0),
            'is_recommended': data.get('is_recommended', False),
            'is_available': True,
            'tags': data.get('tags', []),
            'created_at': datetime.now().isoformat()
        }
        
        new_dish = DishModel.create(dish_data)
        
        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if restaurant:
            dishes_list = restaurant.get('dishes', [])
            if isinstance(dishes_list, list):
                dishes_list.append(new_dish.get('id'))
                restaurant['dishes'] = dishes_list
                RestaurantModel.update(restaurant_id, restaurant)
        
        return jsonify({
            'success': True,
            'dish': new_dish,
            'message': 'Plato agregado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error agregando plato: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/dish/<int:dish_id>/update', methods=['PUT'])
@owner_required
def update_dish(dish_id):
    """Actualizar un plato existente"""
    try:
        user_id = session['user'].get('id')
        dish = DishModel.get_by_id(dish_id)
        
        if not dish:
            return jsonify({'error': 'Plato no encontrado'}), 404
        
        restaurant_id = dish.get('restaurant_id')
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        data = request.json
        for key, value in data.items():
            if key != 'id' and key != 'restaurant_id':
                dish[key] = value
        
        updated = DishModel.update(dish_id, dish)
        
        return jsonify({
            'success': True,
            'dish': updated,
            'message': 'Plato actualizado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error actualizando plato: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/dish/<int:dish_id>/delete', methods=['DELETE'])
@owner_required
def delete_dish(dish_id):
    """Eliminar un plato"""
    try:
        user_id = session['user'].get('id')
        dish = DishModel.get_by_id(dish_id)
        
        if not dish:
            return jsonify({'error': 'Plato no encontrado'}), 404
        
        restaurant_id = dish.get('restaurant_id')
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        DishModel.delete(dish_id)
        
        return jsonify({
            'success': True,
            'message': 'Plato eliminado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error eliminando plato: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/dish/<int:dish_id>/toggle-availability', methods=['POST'])
@owner_required
def toggle_dish_availability(dish_id):
    """Cambiar disponibilidad de un plato"""
    try:
        user_id = session['user'].get('id')
        dish = DishModel.get_by_id(dish_id)
        
        if not dish:
            return jsonify({'error': 'Plato no encontrado'}), 404
        
        restaurant_id = dish.get('restaurant_id')
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        is_available = request.json.get('is_available', False)
        updated = DishModel.update_availability(dish_id, is_available)
        
        return jsonify({
            'success': True,
            'is_available': is_available,
            'message': f'Disponibilidad actualizada'
        })
        
    except Exception as e:
        logger.error(f"Error cambiando disponibilidad: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/generate_menu', methods=['POST'])
@owner_required
def generate_menu():
    """Genera un menú aleatorio sugerido para el empresario"""
    try:
        user_id = session['user'].get('id')
        data = request.json
        restaurant_id = data.get('restaurant_id')
        
        if not restaurant_id:
            return jsonify({'error': 'ID de restaurante requerido'}), 400
        
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        all_dishes = DishModel.get_by_restaurant(restaurant_id)
        available_dishes = [d for d in all_dishes if d.get('is_available', True)]
        
        if len(available_dishes) < 3:
            return jsonify({
                'error': 'No hay suficientes platos disponibles. Agrega más platos primero.'
            }), 400
        
        categories = {
            'Entrada': [],
            'Fondo': [],
            'Postre': [],
            'Bebida': []
        }
        
        for d in available_dishes:
            cat = d.get('category')
            if cat in categories:
                categories[cat].append(d)
        
        suggested_menu = {
            'entradas': random.sample(categories['Entrada'], min(3, len(categories['Entrada']))),
            'fondos': random.sample(categories['Fondo'], min(5, len(categories['Fondo']))),
            'postres': random.sample(categories['Postre'], min(2, len(categories['Postre']))),
            'bebidas': random.sample(categories['Bebida'], min(3, len(categories['Bebida'])))
        }
        
        return jsonify({
            'success': True,
            'menu': suggested_menu,
            'message': 'Menú generado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error generando menú: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/save_daily_menu', methods=['POST'])
@owner_required
def save_daily_menu():
    """Guardar menú diario"""
    try:
        user_id = session['user'].get('id')
        data = request.json
        restaurant_id = data.get('restaurant_id')
        date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
        dish_ids = data.get('dish_ids', [])
        specials = data.get('specials', [])
        price = data.get('price', 0)
        
        if not restaurant_id:
            return jsonify({'error': 'ID de restaurante requerido'}), 400
        
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        dishes = []
        for dish_id in dish_ids:
            dish = DishModel.get_by_id(dish_id)
            if dish:
                dishes.append({
                    'dish_id': dish.get('id'),
                    'name': dish.get('name'),
                    'price': dish.get('price')
                })
        
        menu = DailyMenuModel.create_or_update(
            restaurant_id=restaurant_id,
            date=date,
            dishes=dishes,
            specials=specials,
            price=price
        )
        
        return jsonify({
            'success': True,
            'menu': menu,
            'message': 'Menú diario guardado exitosamente'
        })
        
    except Exception as e:
        logger.error(f"Error guardando menú diario: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/restaurant/<int:restaurant_id>/menu_type', methods=['PUT'])
@owner_required
def update_menu_type(restaurant_id):
    """Actualizar tipo de menú del restaurante"""
    try:
        user_id = session['user'].get('id')
        
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        data = request.json
        menu_type = data.get('menu_type')
        
        if menu_type not in ['fixed', 'daily', 'mixed']:
            return jsonify({'error': 'Tipo de menú inválido'}), 400
        
        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante no encontrado'}), 404
        
        restaurant['menu_type'] = menu_type
        RestaurantModel.update(restaurant_id, restaurant)
        
        return jsonify({
            'success': True,
            'menu_type': menu_type,
            'message': 'Tipo de menú actualizado'
        })
        
    except Exception as e:
        logger.error(f"Error actualizando tipo de menú: {e}")
        return jsonify({'error': str(e)}), 500

@owner_bp.route('/restaurant/<int:restaurant_id>/dishes', methods=['GET'])
@owner_required
def get_restaurant_dishes(restaurant_id):
    """Obtener todos los platos de un restaurante"""
    try:
        user_id = session['user'].get('id')
        
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({'error': 'No autorizado'}), 403
        
        dishes = DishModel.get_by_restaurant(restaurant_id)
        
        return jsonify({
            'success': True,
            'dishes': dishes,
            'total': len(dishes)
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo platos: {e}")
        return jsonify({'error': str(e)}), 500