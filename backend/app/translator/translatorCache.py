import json
from pathlib import Path
import hashlib

class TranslationCache:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    @staticmethod
    def _generate_cache_key(text, source_lang = "English", target_lang = "French"):
        """Génère une clé unique pour le cache basée sur le texte et les langues"""
        content = f"{text}{source_lang}{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached_translation(self, text, source_lang = "English", target_lang = "French"):
        """Récupère une traduction du cache si elle existe"""
        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            with cache_file.open('r', encoding='utf-8') as f:
                print("Utilisation du cache pour la traduction")
                return json.load(f)
        return None

    def save_translation(self, text, source_lang, target_lang, translation_result):
        """
        Sauvegarde une traduction dans le cache avec gestion des objets personnalisés.

        Args:
            text: Texte source à traduire
            source_lang: Langue source
            target_lang: Langue cible
            translation_result: Résultat de la traduction à mettre en cache
        """
        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Fonction pour convertir les objets ExtractedImage en dictionnaires
        def serialize_translation_result(obj):
            if hasattr(obj, '__dict__'):
                # Si c'est un objet ExtractedImage, on le convertit en dictionnaire
                return {
                    'type': 'ExtractedImage',
                    'path': str(obj.path) if hasattr(obj, 'path') else None,
                    'bbox': list(map(float, obj.bbox)) if hasattr(obj, 'bbox') else None,
                    'size': list(map(float, obj.size)) if hasattr(obj, 'size') else None,
                    'caption': str(obj.caption) if hasattr(obj, 'caption') else None,
                    'context_text': str(obj.context_text) if hasattr(obj, 'context_text') else None,
                    'page_number': int(obj.page_number) if hasattr(obj, 'page_number') else None,
                    'marker': str(obj.marker) if hasattr(obj, 'marker') else None
                }
            # Pour les types de base, on les retourne tels quels
            return obj

        try:
            # Conversion du résultat en structure JSON-compatible
            serializable_result = json.loads(
                json.dumps(translation_result, default=serialize_translation_result)
            )

            # Sauvegarde dans le fichier cache
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(serializable_result, f, ensure_ascii=False, indent=2)

            print("Traduction sauvegardée dans le cache avec succès")

        except Exception as e:
            print(f"Erreur lors de la sauvegarde dans le cache: {str(e)}")
            # On lève à nouveau l'exception pour la gestion d'erreur en amont
            raise