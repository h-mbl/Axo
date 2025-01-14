from .translator_base import TranslatorBase
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
import torch
import re
import logging


class HuggingFaceTranslator(TranslatorBase):
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M"):
        """
        Initialise le traducteur avec le modèle NLLB de Facebook, qui est plus
        robuste et mieux maintenu que le modèle Helsinki-NLP.
        """
        self.logger = logging.getLogger(__name__)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"Utilisation du périphérique: {self.device}")

        try:
            self.logger.info(f"Chargement du modèle {model_name}...")

            # Utilisation de pipeline pour une initialisation plus simple et robuste
            self.translator = pipeline(
                "translation",
                model=model_name,
                device=0 if self.device == "cuda" else -1,
                framework="pt"
            )

            # Définition des codes de langue pour NLLB
            self.lang_codes = {
                "en": "eng_Latn",
                "fr": "fra_Latn",
                # Ajoutez d'autres langues si nécessaire
            }

            self.logger.info("Modèle chargé avec succès")

        except Exception as e:
            self.logger.error(f"Erreur lors du chargement du modèle: {str(e)}")
            raise

    def _preserve_special_tokens(self, text: str) -> tuple:
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

    def _restore_special_tokens(self, text: str, special_tokens: dict) -> str:
        """Restaure les tokens spéciaux dans le texte traduit."""
        restored_text = text
        for placeholder, original in special_tokens.items():
            restored_text = restored_text.replace(placeholder, original)
        return restored_text

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Traduit le texte tout en préservant les marqueurs spéciaux.
        """
        try:
            # Préservation des tokens spéciaux
            modified_text, special_tokens = self._preserve_special_tokens(text)

            # Conversion des codes de langue
            src_lang = self.lang_codes.get(source_lang, source_lang)
            tgt_lang = self.lang_codes.get(target_lang, target_lang)

            # Traduction du texte
            translation = self.translator(
                modified_text,
                src_lang=src_lang,
                tgt_lang=tgt_lang,
                max_length=512
            )[0]['translation_text']

            # Restauration des tokens spéciaux
            final_translation = self._restore_special_tokens(translation, special_tokens)

            return final_translation

        except Exception as e:
            self.logger.error(f"Erreur lors de la traduction: {str(e)}")
            raise