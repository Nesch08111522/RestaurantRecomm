# models/moderation.py
from models.base import JSONModel
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ModerationModel(JSONModel):
    """Modelo para gestionar la moderación de contenido"""
    file_path = Config.MODERATION_FILE  # ✅ Definir como variable de clase
    
    @classmethod
    def get_pending_reviews(cls):
        """Obtener todas las revisiones pendientes"""
        data = cls._load_data()
        return [item for item in data if item.get('status') == 'pending']
    
    @classmethod
    def get_flagged_content(cls):
        """Obtener contenido marcado como sospechoso"""
        data = cls._load_data()
        return [item for item in data if item.get('flagged', False)]
    
    @classmethod
    def create_moderation_entry(cls, content_type, content_id, content_data, user_id, reason=''):
        """Crear una entrada de moderación"""
        entry = {
            'content_type': content_type,  # 'restaurant', 'dish', 'review', 'user', 'comment'
            'content_id': content_id,
            'content_data': content_data,
            'user_id': user_id,
            'reason': reason,
            'status': 'pending',  # 'pending', 'approved', 'rejected'
            'flagged': False,
            'flags': [],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        return cls.create(entry)
    
    @classmethod
    def flag_content(cls, moderation_id, flag_type, reason):
        """Marcar contenido como sospechoso"""
        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None
        
        if 'flags' not in entry:
            entry['flags'] = []
        
        entry['flags'].append({
            'type': flag_type,  # 'inappropriate', 'spam', 'offensive', 'not_food'
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        entry['flagged'] = True
        entry['status'] = 'pending'
        
        return cls.update(moderation_id, entry)
    
    @classmethod
    def approve_content(cls, moderation_id, admin_notes=''):
        """Aprobar contenido"""
        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None
        
        entry['status'] = 'approved'
        entry['admin_notes'] = admin_notes
        entry['approved_at'] = datetime.now().isoformat()
        entry['updated_at'] = datetime.now().isoformat()
        
        return cls.update(moderation_id, entry)
    
    @classmethod
    def reject_content(cls, moderation_id, admin_notes=''):
        """Rechazar contenido"""
        entry = cls.get_by_id(moderation_id)
        if not entry:
            return None
        
        entry['status'] = 'rejected'
        entry['admin_notes'] = admin_notes
        entry['rejected_at'] = datetime.now().isoformat()
        entry['updated_at'] = datetime.now().isoformat()
        
        return cls.update(moderation_id, entry)
    
    @classmethod
    def get_stats(cls):
        """Obtener estadísticas de moderación"""
        data = cls._load_data()
        total = len(data)
        pending = len([item for item in data if item.get('status') == 'pending'])
        approved = len([item for item in data if item.get('status') == 'approved'])
        rejected = len([item for item in data if item.get('status') == 'rejected'])
        flagged = len([item for item in data if item.get('flagged', False)])
        
        return {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'flagged': flagged
        }