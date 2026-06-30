from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash, Response
from models.restaurant import RestaurantModel
from models.user import UserModel
from models.favorite import FavoriteModel
from models.category import CategoryModel
from config import Config
from functools import wraps
import json
import os
import datetime
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================
# DECORADORES DE AUTENTICACIÓN
# ============================================

def admin_required(f):
    """Decorador que solo permite acceso a administradores"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('auth.login'))
        
        user = session.get('user')
        if user.get('role') != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

def admin_or_owner_required(f):
    """Decorador que permite acceso a admin y empresarios (dueños de restaurantes)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('user'):
            flash('Debes iniciar sesión', 'warning')
            return redirect(url_for('auth.login'))
        
        user = session.get('user')
        role = user.get('role', 'user')
        
        if role not in ['admin', 'business_owner']:
            flash('Acceso denegado. Se requieren permisos de administrador o empresario.', 'error')
            return redirect(url_for('main.index'))
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# DASHBOARD
# ============================================

@admin_bp.route('/dashboard')
@admin_or_owner_required
def dashboard():
    """Panel de administración - Adaptado según rol"""
    user = session.get('user')
    user_id = user.get('id')
    role = user.get('role')
    
    if role == 'admin':
        restaurants = RestaurantModel.all()
        users = UserModel.all()
        favorites = FavoriteModel.all()
        total_rest = len(restaurants)
        total_users = len(users)
        total_favorites = len(favorites)
        avg_rating = sum(r.get('rating', 0) for r in restaurants) / total_rest if total_rest > 0 else 0
        avg_price = sum(r.get('avg_price', 0) for r in restaurants) / total_rest if total_rest > 0 else 0
        
        return render_template('admin/dashboard.html', 
                               total_rest=total_rest, 
                               total_users=total_users,
                               total_favorites=total_favorites,
                               avg_rating=round(avg_rating, 2),
                               avg_price=round(avg_price, 2),
                               role=role,
                               is_admin=True)
    else:
        restaurants = RestaurantModel.get_by_owner(user_id)
        total_rest = len(restaurants)
        avg_rating = sum(r.get('rating', 0) for r in restaurants) / total_rest if total_rest > 0 else 0
        avg_price = sum(r.get('avg_price', 0) for r in restaurants) / total_rest if total_rest > 0 else 0
        total_promos = sum(1 for r in restaurants if r.get('promo'))
        
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
                               avg_price=round(avg_price, 2),
                               total_promos=total_promos,
                               recent_activities=recent_activities,
                               role=role,
                               is_admin=False)

# ============================================
# GESTIÓN DE RESTAURANTES
# ============================================

@admin_bp.route('/restaurants')
@admin_or_owner_required
def restaurants():
    """Gestión de restaurantes - Adaptado según rol"""
    user = session.get('user')
    user_id = user.get('id')
    role = user.get('role')
    
    if role == 'admin':
        restaurants = RestaurantModel.all()
    else:
        restaurants = RestaurantModel.get_by_owner(user_id)
    
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        try:
            with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except:
            categories = []
    
    cat_dict = {cat['id']: cat['name'] for cat in categories}
    
    now = datetime.datetime.now().strftime('%H:%M')
    for r in restaurants:
        r['category_name'] = cat_dict.get(r.get('category_id'), 'Sin categoría')
        r['is_open'] = r.get('open_time') <= now <= r.get('close_time')
    
    districts = getattr(Config, 'DISTRITOS', ['Trujillo', 'Victor Larco', 'La Esperanza', 'Huanchaco', 'Moche'])
    
    if role == 'business_owner':
        return render_template('owner/restaurants.html',
                             restaurants=restaurants,
                             categories=categories,
                             districts=districts,
                             total_pages=max(1, (len(restaurants) + 9) // 10),
                             role=role,
                             is_admin=False)
    
    return render_template('admin/restaurants.html',
                         restaurants=restaurants,
                         categories=categories,
                         districts=districts,
                         total_pages=max(1, (len(restaurants) + 9) // 10),
                         role=role,
                         is_admin=(role == 'admin'))

@admin_bp.route('/restaurant/new', methods=['GET', 'POST'])
@admin_or_owner_required
def new_restaurant():
    """Crear nuevo restaurante - Asigna dueño automáticamente"""
    if request.method == 'POST':
        tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
        features = [f.strip() for f in request.form.get('features', '').split(',') if f.strip()]
        dietary = [d.strip() for d in request.form.get('dietary_restrictions', '').split(',') if d.strip()]
        
        data = {
            'name': request.form.get('name'),
            'category_id': request.form.get('category_id', type=int),
            'district': request.form.get('district'),
            'lat': request.form.get('lat', type=float),
            'lng': request.form.get('lng', type=float),
            'avg_price': request.form.get('avg_price', type=float),
            'rating': request.form.get('rating', type=float, default=0),
            'open_time': request.form.get('open_time'),
            'close_time': request.form.get('close_time'),
            'tags': tags,
            'features': features,
            'image': request.form.get('image'),
            'description': request.form.get('description'),
            'address': request.form.get('address'),
            'phone': request.form.get('phone'),
            'promo': request.form.get('promo'),
            'dietary_restrictions': dietary,
            'owner_id': session['user']['id'],
            'owner_name': session['user']['profile']['name']
        }
        
        if not data['name'] or not data['category_id'] or not data['district']:
            flash('Por favor completa todos los campos requeridos', 'error')
            return redirect(url_for('admin.new_restaurant'))
        
        RestaurantModel.create(data)
        
        flash('Restaurante creado exitosamente', 'success')
        return redirect(url_for('admin.restaurants'))
    
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        try:
            with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except:
            categories = []
    
    districts = getattr(Config, 'DISTRITOS', ['Trujillo', 'Victor Larco', 'La Esperanza', 'Huanchaco', 'Moche'])
    
    return render_template('admin/restaurant_form.html',
                         categories=categories,
                         districts=districts)

@admin_bp.route('/restaurant/<int:id>/edit', methods=['GET'])
@admin_or_owner_required
def edit_restaurant(id):
    """Página para editar un restaurante"""
    user = session.get('user')
    user_id = user.get('id')
    role = user.get('role')
    
    if role != 'admin' and not RestaurantModel.is_owner(user_id, id):
        flash('No tienes permiso para editar este restaurante', 'error')
        return redirect(url_for('admin.restaurants'))
    
    restaurant = RestaurantModel.get_by_id(id)
    if not restaurant:
        flash('Restaurante no encontrado', 'error')
        return redirect(url_for('admin.restaurants'))
    
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        try:
            with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except:
            categories = []
    
    districts = getattr(Config, 'DISTRITOS', ['Trujillo', 'Victor Larco', 'La Esperanza', 'Huanchaco', 'Moche'])
    
    return render_template('admin/restaurant_edit.html',
                         restaurant=restaurant,
                         categories=categories,
                         districts=districts)

@admin_bp.route('/restaurant/<int:id>/update', methods=['POST'])
@admin_or_owner_required
def update_restaurant(id):
    """Actualizar restaurante desde formulario"""
    user = session.get('user')
    user_id = user.get('id')
    role = user.get('role')
    
    if role != 'admin' and not RestaurantModel.is_owner(user_id, id):
        flash('No tienes permiso para editar este restaurante', 'error')
        return redirect(url_for('admin.restaurants'))
    
    restaurant = RestaurantModel.get_by_id(id)
    if not restaurant:
        flash('Restaurante no encontrado', 'error')
        return redirect(url_for('admin.restaurants'))
    
    tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
    features = [f.strip() for f in request.form.get('features', '').split(',') if f.strip()]
    dietary = [d.strip() for d in request.form.get('dietary_restrictions', '').split(',') if d.strip()]
    
    data = {
        'name': request.form.get('name'),
        'category_id': request.form.get('category_id', type=int),
        'district': request.form.get('district'),
        'lat': request.form.get('lat', type=float),
        'lng': request.form.get('lng', type=float),
        'avg_price': request.form.get('avg_price', type=float),
        'rating': request.form.get('rating', type=float, default=0),
        'open_time': request.form.get('open_time'),
        'close_time': request.form.get('close_time'),
        'tags': tags,
        'features': features,
        'image': request.form.get('image'),
        'description': request.form.get('description'),
        'address': request.form.get('address'),
        'phone': request.form.get('phone'),
        'promo': request.form.get('promo'),
        'dietary_restrictions': dietary
    }
    
    if role != 'admin':
        data['owner_id'] = restaurant.get('owner_id')
        data['owner_name'] = restaurant.get('owner_name')
    
    RestaurantModel.update(id, data)
    
    flash('Restaurante actualizado exitosamente', 'success')
    return redirect(url_for('admin.restaurants'))

@admin_bp.route('/restaurant/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@admin_or_owner_required
def manage_restaurant(id: int):
    """Obtener, actualizar o eliminar restaurante - Verifica permisos"""
    user = session.get('user')
    user_id = user.get('id')
    role = user.get('role')
    
    if role != 'admin':
        if not RestaurantModel.is_owner(user_id, id):
            return jsonify({'error': 'No tienes permiso para gestionar este restaurante'}), 403
    
    if request.method == 'GET':
        restaurant = RestaurantModel.get_by_id(id)
        if restaurant:
            return jsonify(restaurant)
        return jsonify({'error': 'Restaurante no encontrado'}), 404
    
    elif request.method == 'PUT':
        data = request.json
        updated = RestaurantModel.update(id, data)
        if updated:
            return jsonify({'success': True, 'restaurant': updated})
        return jsonify({'success': False, 'error': 'Restaurante no encontrado'}), 404
    
    elif request.method == 'DELETE':
        deleted = RestaurantModel.delete(id)
        if deleted:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Restaurante no encontrado'}), 404

@admin_bp.route('/restaurant/<int:id>/promo', methods=['POST'])
@admin_or_owner_required
def add_promotion(id: int):
    """Agregar promoción a un restaurante - Verifica permisos"""
    user = session.get('user')
    user_id = user.get('id')
    role = user.get('role')
    
    if role != 'admin':
        if not RestaurantModel.is_owner(user_id, id):
            return jsonify({'error': 'No tienes permiso para gestionar este restaurante'}), 403
    
    data = request.json
    promo = data.get('promo')
    
    if not promo:
        return jsonify({'error': 'Se requiere texto de promoción'}), 400
    
    restaurant = RestaurantModel.get_by_id(id)
    
    if not restaurant:
        return jsonify({'error': 'Restaurante no encontrado'}), 404
    
    restaurant['promo'] = promo
    updated = RestaurantModel.update(id, restaurant)
    
    if updated:
        return jsonify({'success': True, 'promo': promo})
    return jsonify({'error': 'Error al actualizar'}), 500

# ============================================
# ANALÍTICAS - Solo admin
# ============================================

@admin_bp.route('/analytics')
@admin_required
def analytics_page():
    """Página de analíticas - Solo admin"""
    restaurants = RestaurantModel.all()
    users = UserModel.all()
    favorites = FavoriteModel.all()
    
    total_favorites = len(favorites)
    avg_rating = sum(r.get('rating', 0) for r in restaurants) / len(restaurants) if restaurants else 0
    avg_price = sum(r.get('avg_price', 0) for r in restaurants) / len(restaurants) if restaurants else 0
    
    recent_activities = []
    
    if restaurants:
        latest = sorted(restaurants, key=lambda x: x.get('id', 0), reverse=True)[:3]
        for r in latest:
            recent_activities.append({
                'icon': 'plus',
                'message': f'Se agregó "{r.get("name")}"',
                'time': 'Recientemente'
            })
    
    if len(recent_activities) < 3:
        recent_activities.append({
            'icon': 'heart',
            'message': f'{total_favorites} restaurantes en favoritos',
            'time': 'Total'
        })
        recent_activities.append({
            'icon': 'star',
            'message': f'Rating promedio: {avg_rating:.1f} ⭐',
            'time': 'General'
        })
    
    return render_template('admin/analytics.html',
                         total_restaurants=len(restaurants),
                         total_users=len(users),
                         avg_rating=round(avg_rating, 1),
                         avg_price=round(avg_price, 2),
                         total_favorites=total_favorites,
                         recent_activities=recent_activities)

@admin_bp.route('/api/analytics')
@admin_required
def analytics_api():
    """API para datos de analíticas (gráficos) - Solo admin"""
    try:
        restaurants = RestaurantModel.all()
        
        # Cargar categorías para obtener nombres
        categories = []
        if os.path.exists(Config.CATEGORIES_FILE):
            try:
                with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                    categories = json.load(f)
            except:
                categories = []
        
        cat_names = {cat['id']: cat['name'] for cat in categories}
        
        # Distribución por categoría (usando nombres legibles)
        cat_dist = {}
        for r in restaurants:
            cat_id = r.get('category_id')
            if cat_id:
                cat_name = cat_names.get(cat_id, f'Categoría {cat_id}')
                cat_dist[cat_name] = cat_dist.get(cat_name, 0) + 1
        
        # Distribución por distrito
        dist_dist = {}
        for r in restaurants:
            district = r.get('district', 'Desconocido')
            dist_dist[district] = dist_dist.get(district, 0) + 1
        
        # ✅ Precio vs Rating - AHORA INCLUIDO
        price_rating = []
        for r in restaurants:
            price = r.get('avg_price')
            rating = r.get('rating')
            if price is not None and rating is not None:
                price_rating.append({
                    'price': price,
                    'rating': rating,
                    'name': r.get('name', 'Restaurante')
                })
        
        # ✅ Promociones - AHORA INCLUIDO
        with_promo = sum(1 for r in restaurants if r.get('promo'))
        without_promo = len(restaurants) - with_promo
        
        # Ratings y precios (para los otros gráficos)
        ratings = [r.get('rating', 0) for r in restaurants if r.get('rating') is not None]
        prices = [r.get('avg_price', 0) for r in restaurants if r.get('avg_price') is not None]
        
        return jsonify({
            'categories': cat_dist,
            'districts': dist_dist,
            'ratings': ratings,
            'prices': prices,
            'price_rating': price_rating,  # ✅ NUEVO
            'promotions': {                # ✅ NUEVO
                'with_promo': with_promo,
                'without_promo': without_promo
            },
            'total': len(restaurants)
        })
        
    except Exception as e:
        logger.error(f"Error en analytics_api: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# GESTIÓN DE USUARIOS - Solo admin
# ============================================

@admin_bp.route('/users')
@admin_required
def users():
    """Lista de usuarios - Solo admin"""
    users = UserModel.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/user/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@admin_required
def manage_user(id: int):
    """Obtener, actualizar o eliminar usuario - Solo admin"""
    if request.method == 'GET':
        user = UserModel.get_by_id(id)
        if user:
            if 'password' in user:
                del user['password']
            return jsonify(user)
        return jsonify({'error': 'Usuario no encontrado'}), 404
    
    elif request.method == 'PUT':
        data = request.json
        if 'password' in data:
            del data['password']
        updated = UserModel.update(id, data)
        if updated:
            return jsonify({'success': True, 'user': updated})
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404
    
    elif request.method == 'DELETE':
        deleted = UserModel.delete(id)
        if deleted:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

# ============================================
# GESTIÓN DE CATEGORÍAS - Solo admin
# ============================================

@admin_bp.route('/categories')
@admin_required
def categories():
    """Lista de categorías - Solo admin"""
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        try:
            with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except:
            categories = []
    
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/category', methods=['POST'])
@admin_required
def new_category():
    """Crear nueva categoría - Solo admin"""
    data = {
        'name': request.form.get('name'),
        'slug': request.form.get('slug'),
        'icon': request.form.get('icon', 'restaurant'),
        'image_url': request.form.get('image_url', '')
    }
    
    if not data['name'] or not data['slug']:
        flash('Nombre y slug son requeridos', 'error')
        return redirect(url_for('admin.categories'))
    
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
            categories = json.load(f)
    
    max_id = max([cat.get('id', 0) for cat in categories], default=0)
    data['id'] = max_id + 1
    
    categories.append(data)
    
    with open(Config.CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)
    
    flash('Categoría creada exitosamente', 'success')
    return redirect(url_for('admin.categories'))

@admin_bp.route('/category/<int:id>', methods=['DELETE'])
@admin_required
def delete_category(id: int):
    """Eliminar categoría - Solo admin"""
    categories = []
    if os.path.exists(Config.CATEGORIES_FILE):
        with open(Config.CATEGORIES_FILE, 'r', encoding='utf-8') as f:
            categories = json.load(f)
    
    categories = [cat for cat in categories if cat.get('id') != id]
    
    with open(Config.CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)
    
    return jsonify({'success': True})

# ============================================
# ESTADÍSTICAS - Solo admin
# ============================================

@admin_bp.route('/api/stats')
@admin_required
def stats_api():
    """API para estadísticas generales - Solo admin"""
    restaurants = RestaurantModel.all()
    users = UserModel.all()
    favorites = FavoriteModel.all()
    
    return jsonify({
        'total_restaurants': len(restaurants),
        'total_users': len(users),
        'total_favorites': len(favorites),
        'avg_rating': sum(r.get('rating', 0) for r in restaurants) / len(restaurants) if restaurants else 0,
        'avg_price': sum(r.get('avg_price', 0) for r in restaurants) / len(restaurants) if restaurants else 0,
        'with_promo': sum(1 for r in restaurants if r.get('promo')),
        'total_reviews': sum(r.get('reviews', 0) for r in restaurants)
    })
    
@admin_bp.route('/moderation')
@admin_required
def moderation_dashboard():
    """Panel de moderación - Solo admin"""
    from models.moderation import ModerationModel
    from utils.content_filter import ContentFilter
    
    moderation_model = ModerationModel()
    
    # Estadísticas
    stats = moderation_model.get_stats()
    
    # Contenido pendiente
    pending = moderation_model.get_pending_reviews()
    
    # Contenido marcado
    flagged = moderation_model.get_flagged_content()
    
    # ✅ Obtener restaurantes PENDIENTES de aprobación
    pending_restaurants = RestaurantModel.get_pending()
    
    # Verificar automáticamente restaurantes pendientes
    auto_flagged = []
    for restaurant in pending_restaurants:
        result = ContentFilter.filter_restaurant(restaurant)
        if not result['is_ok']:
            real_issues = []
            for issue in result['issues']:
                if 'no relacionado con comida' in issue and result['result']['food_score'] > 20:
                    continue
                real_issues.append(issue)
            
            if real_issues:
                auto_flagged.append({
                    'restaurant': restaurant,
                    'issues': real_issues,
                    'result': result,
                    'food_score': result['result']['food_score']
                })
    
    # ✅ Restaurantes pendientes que NO tienen problemas (se pueden aprobar fácilmente)
    clean_pending = []
    for restaurant in pending_restaurants:
        if restaurant.get('id') not in [item['restaurant']['id'] for item in auto_flagged]:
            clean_pending.append(restaurant)
    
    auto_flagged.sort(key=lambda x: x.get('food_score', 0))
    
    return render_template('admin/moderation.html',
                         stats=stats,
                         pending=pending,
                         flagged=flagged,
                         auto_flagged=auto_flagged,
                         clean_pending=clean_pending,
                         total_restaurants=len(RestaurantModel.all()))

@admin_bp.route('/moderation/restaurant/<int:id>/review', methods=['POST'])
@admin_required
def review_restaurant(id):
    """Revisar un restaurante específico"""
    from models.moderation import ModerationModel
    
    try:
        data = request.json
        action = data.get('action')
        notes = data.get('notes', '')
        
        restaurant = RestaurantModel.get_by_id(id)
        if not restaurant:
            return jsonify({'error': 'Restaurante no encontrado'}), 404
        
        # Buscar entrada de moderación existente
        entries = ModerationModel._load_data()
        entry = next((e for e in entries if e.get('content_id') == id and e.get('content_type') == 'restaurant'), None)
        
        if action == 'approve':
            # ✅ Marcar como verificado/aprobado
            restaurant['verified'] = True
            restaurant['moderation_notes'] = notes
            restaurant['moderated_at'] = datetime.datetime.now().isoformat()
            RestaurantModel.update(id, restaurant)
            
            if entry:
                ModerationModel.approve_content(entry.get('id'), notes)
            
            message = '✅ Restaurante aprobado y visible para todos los usuarios'
            
        elif action == 'reject':
            # ❌ Marcar como rechazado
            restaurant['verified'] = False
            restaurant['moderation_notes'] = notes
            restaurant['moderated_at'] = datetime.datetime.now().isoformat()
            restaurant['rejected'] = True
            RestaurantModel.update(id, restaurant)
            
            if entry:
                ModerationModel.reject_content(entry.get('id'), notes)
            
            message = '❌ Restaurante rechazado. No será visible para los usuarios.'
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500