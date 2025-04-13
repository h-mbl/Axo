# backend/app/translator/translatorCache.py
import json
from pathlib import Path
import hashlib
import logging


class TranslationCache:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("TranslationCache")

    @staticmethod
    def _generate_cache_key(text, source_lang="English", target_lang="French"):
        """Génère une clé unique pour le cache basée sur le texte et les langues"""
        content = f"{text}{source_lang}{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()

    def get_cached_translation(self, text, source_lang="English", target_lang="French"):
        """Récupère une traduction du cache si elle existe"""
        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                with cache_file.open('r', encoding='utf-8') as f:
                    self.logger.info("Utilisation du cache pour la traduction")
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erreur lors de la lecture du cache: {str(e)}")
                return None
        return None

    def save_translation(self, text, source_lang, target_lang, translation_result):
        """
        Sauvegarde une traduction dans le cache.

        Args:
            text: Texte source à traduire
            source_lang: Langue source
            target_lang: Langue cible
            translation_result: Résultat de la traduction à mettre en cache
        """
        cache_key = self._generate_cache_key(text, source_lang, target_lang)
        cache_file = self.cache_dir / f"{cache_key}.json"

        # Fonction pour traiter les objets personnalisés
        def serialize_translation_result(obj):
            if hasattr(obj, '__dict__'):
                # Convertir en dictionnaire pour la sérialisation
                result = {}
                for key, value in obj.__dict__.items():
                    if not key.startswith('_'):  # Ignorer les attributs privés
                        if isinstance(value, (int, float, str, bool, list, dict)):
                            result[key] = value
                        elif value is None:
                            result[key] = None
                        else:
                            # Pour les types plus complexes, convertir en string
                            result[key] = str(value)
                return result
            return obj

        try:
            # Conversion du résultat en structure JSON-compatible
            serializable_result = json.loads(
                json.dumps(translation_result, default=serialize_translation_result)
            )

            # Sauvegarde dans le fichier cache
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(serializable_result, f, ensure_ascii=False, indent=2)

            self.logger.info("Traduction sauvegardée dans le cache avec succès")

        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde dans le cache: {str(e)}")
            # On ne relève pas l'exception pour ne pas interrompre le flux principal