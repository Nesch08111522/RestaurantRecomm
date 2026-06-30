import json
import os
from config import Config

class JSONModel:
    """
    Clase base para modelos que utilizan persistencia en JSON.
    Paradigma: Orientado a Objetos.
    """
    file_path = None

    @classmethod
    def _load_data(cls):
        if not os.path.exists(cls.file_path):
            return []
        with open(cls.file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    @classmethod
    def _save_data(cls, data):
        with open(cls.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @classmethod
    def all(cls):
        return cls._load_data()

    @classmethod
    def get_by_id(cls, item_id):
        data = cls._load_data()
        return next((item for item in data if item.get('id') == item_id), None)

    @classmethod
    def create(cls, new_data):
        data = cls._load_data()
        if not new_data.get('id'):
            new_data['id'] = max([item.get('id', 0) for item in data] + [0]) + 1
        data.append(new_data)
        cls._save_data(data)
        return new_data

    @classmethod
    def update(cls, item_id, updated_data):
        data = cls._load_data()
        for i, item in enumerate(data):
            if item.get('id') == item_id:
                data[i].update(updated_data)
                cls._save_data(data)
                return data[i]
        return None

    @classmethod
    def delete(cls, item_id):
        data = cls._load_data()
        new_data = [item for item in data if item.get('id') != item_id]
        if len(new_data) < len(data):
            cls._save_data(new_data)
            return True
        return False
