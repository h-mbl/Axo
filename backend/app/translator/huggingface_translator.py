from .translator_base import TranslatorBase
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
import torch
import re
import logging
import gc

class HuggingFaceTranslator(TranslatorBase):
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M"):
        """
        Initialise le traducteur avec le modèle NLLB de Facebook avec des optimisations
        de mémoire et une meilleure gestion des erreurs.
        """
        self.logger = logging.getLogger(__name__)

        # Nettoyage préventif de la mémoire
        gc.collect()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

        # Configuration du device avec plus de contrôle
        self.device = self._setup_device()
        self.logger.info(f"Utilisation du périphérique: {self.device}")

        try:
            self.logger.info(f"Chargement du modèle {model_name}...")

            # Configuration des optimisations mémoire pour le pipeline
            pipeline_kwargs = {
                "model": model_name,
                "device": self.device_id,  # Utilise l'ID du device configuré
                "framework": "pt",
                "model_kwargs": {
                    "low_cpu_mem_usage": True,  # Réduit l'utilisation de la mémoire CPU
                    "torch_dtype": torch.float32  # Utilise la précision simple pour réduire la mémoire
                }
            }

            # Tentative de chargement avec gestion des erreurs
            try:
                self.translator = pipeline("translation", **pipeline_kwargs)
            except Exception as e:
                self.logger.warning(f"Échec du chargement initial: {str(e)}")
                self.logger.info("Tentative avec des paramètres de mémoire réduits...")

                # Seconde tentative avec paramètres plus conservateurs
                pipeline_kwargs["model_kwargs"].update({
                    "torch_dtype": torch.float16,  # Réduit encore la précision
                    "device_map": "auto"  # Permet une allocation automatique de la mémoire
                })
                self.translator = pipeline("translation", **pipeline_kwargs)

            # Définition des codes de langue pour NLLB
            self.lang_codes = {
                "en": "eng_Latn",
                "fr": "fra_Latn",
                "es": "spa_Latn",
                "de": "deu_Latn",
                "it": "ita_Latn",
                "pt": "por_Latn",
                "nl": "nld_Latn",
                "pl": "pol_Latn",
                "ru": "rus_Cyrl",
                "zh": "zho_Hans",
                "ja": "jpn_Jpan",
                "ko": "kor_Hang",
                "ar": "ara_Arab",
                "hi": "hin_Deva",
                "vi": "vie_Latn",
                "th": "tha_Thai",
                "tr": "tur_Latn"
            }

            self.logger.info("Modèle chargé avec succès")

        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du modèle: {str(e)}")
            raise

    def _setup_device(self) -> str:
        """
        Configure le device de manière optimisée avec gestion de la mémoire.
        """
        if torch.cuda.is_available():
            # Vérifie la mémoire GPU disponible
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            if gpu_memory < 4 * 1024 * 1024 * 1024:  # Moins de 4GB
                self.logger.warning("Mémoire GPU insuffisante, utilisation du CPU")
                self.device_id = -1
                return "cpu"
            self.device_id = 0
            return "cuda"
        self.device_id = -1
        return "cpu"

    @staticmethod
    def _preserve_special_tokens(text: str) -> tuple:
        """Préserve les tokens spéciaux comme les marqueurs d'image."""
        special_tokens = {}
        counter = 0
        modified_text = text

        for match in re.finditer(r'\[IMAGE\d+\]', text):
            token = match.group()
            placeholder = f"__SPECIAL_TOKEN_{counter}__"
            special_tokens[placeholder] = token
            modified_text = modified_text.replace(token, placeholder)
            counter += 1

        return modified_text, special_tokens

    @staticmethod
    def _restore_special_tokens(text: str, special_tokens: dict) -> str:
        """Restaure les tokens spéciaux dans le texte traduit."""
        restored_text = text
        for placeholder, original in special_tokens.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Traduit le texte avec gestion optimisée de la mémoire.
        """
        try:
            # Nettoyage préventif de la mémoire avant traduction
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # Préservation des tokens spéciaux
            modified_text, special_tokens = self._preserve_special_tokens(text)

            # Conversion des codes de langue
            src_lang = self.lang_codes.get(source_lang, source_lang)
            tgt_lang = self.lang_codes.get(target_lang, target_lang)

            # Traduction avec gestion de la taille maximale
            chunks = self._split_text(modified_text, max_length=400)
            translations = []

            for chunk in chunks:
                translation = self.translator(
                    chunk,
                    src_lang=src_lang,
                    tgt_lang=tgt_lang,
                    max_length=512
                )[0]['translation_text']
                translations.append(translation)

            # Combine les traductions
            final_translation = ' '.join(translations)

            # Restauration des tokens spéciaux
            final_translation = self._restore_special_tokens(final_translation, special_tokens)

            return final_translation

        except Exception as e:
            self.logger.error(f"Erreur lors de la traduction: {str(e)}")
            raise

    @staticmethod
    def _split_text(text: str, max_length: int = 400) -> list:
        """
        Découpe le texte en chunks plus petits pour éviter les problèmes de mémoire.
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0

        for word in words:
            if current_length + len(word) > max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += len(word) + 1  # +1 pour l'espace

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks