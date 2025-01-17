import json
from pathlib import Path
import hashlib


class TranslationCache:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _generate_cache_key(self, text, source_lang, target_lang):
        """Génère une clé unique pour le cache basée sur le texte et les langues"""
        content = f"{text}{source_lang}{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached_translation(self, text, source_lang, target_lang):
        """Récupère une traduction du cache si elle existe"""
        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            with cache_file.open('r', encoding='utf-8') as f:
                print("Utilisation du cache pour la traduction")
                return json.load(f)
        return None

    def save_translation(self, text, source_lang, target_lang, translation_result):
        """Sauvegarde une traduction dans le cache"""
        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        with cache_file.open('w', encoding='utf-8') as f:
            json.dump(translation_result, f, ensure_ascii=False, indent=2)
        print("Traduction sauvegardée dans le cache")