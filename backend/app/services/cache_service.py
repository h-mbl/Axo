# backend/app/services/cache_service.py
import hashlib
from typing import Dict, Optional

from backend.app.translator.translatorCache import TranslationCache


class CacheService:
    def __init__(self, translation_cache: TranslationCache):
        self.translation_cache = translation_cache

    @staticmethod
    def generate_cache_key(text: str, source_lang: str, target_lang: str) -> str:
        """Génère une clé de cache unique et reproductible pour la traduction."""
        # Utilisation de hashlib pour générer une clé plus robuste
        combined = f"{text}_{source_lang}_{target_lang}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get_cached_translation(self, text: str, source_lang: str, target_lang: str) -> Optional[Dict]:
        """Récupère une traduction en cache si elle existe."""
        return self.translation_cache.get_cached_translation(text, source_lang, target_lang)

    def save_translation(self, text: str, source_lang: str, target_lang: str, result: Dict):
        """Sauvegarde une traduction dans le cache."""
        self.translation_cache.save_translation(text, source_lang, target_lang, result)