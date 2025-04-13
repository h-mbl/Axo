# backend/app/translator/huggingface_translator.py
from .translator_base import TranslatorBase
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
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

            # Chargement du modèle et du tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                low_cpu_mem_usage=True,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            ).to(self.device)

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
            src_lang = self.lang_codes.get(source_lang.lower(), "eng_Latn")
            tgt_lang = self.lang_codes.get(target_lang.lower(), target_lang)

            # Traduction avec gestion de la taille maximale
            chunks = self._split_text(modified_text, max_length=400)
            translations = []

            for chunk in chunks:
                # Préparation des entrées pour le modèle
                inputs = self.tokenizer(
                    chunk,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)

                # Génération de la traduction
                with torch.no_grad():
                    translated_ids = self.model.generate(
                        **inputs,
                        forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_lang],
                        max_length=512
                    )

                # Décodage de la sortie
                translation = self.tokenizer.batch_decode(
                    translated_ids,
                    skip_special_tokens=True
                )[0]
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