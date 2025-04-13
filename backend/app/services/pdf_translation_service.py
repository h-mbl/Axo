# backend/app/services/pdf_translation_service.py
from logging import Logger
from typing import Optional, Dict
from fastapi import UploadFile
import logging
import os

# Imports des composants nécessaires
from backend.app.translator.groq_translator import GroqTranslator
from backend.app.translator.huggingface_translator import HuggingFaceTranslator
from backend.app.translator.translator_base import TranslatorBase
from backend.app.extractors.image_extractor import EnhancedPDFImageExtractor
from backend.app.extractors.text_extractor import EnhancedTextExtractor
from backend.app.translator.translatorCache import TranslationCache
from backend.app.exporters.html_exporter import HTMLExporter
from backend.app.config.settings import Settings

# Imports de nos services
from .file_service import FileService
from .extraction_service import ExtractionService
from .translation_service import TranslationService
from .result_builder import ResultBuilder
from .cache_service import CacheService


class PDFTranslationService:
    """
    Service principal de traduction de PDF implémentant le pattern Singleton.
    Coordonne tous les aspects du processus de traduction, de l'extraction à la génération du résultat.
    """

    # Attributs de classe pour le pattern Singleton
    _instance: Optional['PDFTranslationService'] = None
    _initialized: bool = False

    def __new__(cls) -> 'PDFTranslationService':
        """
        Implémente le pattern Singleton pour garantir une seule instance du service.
        Ceci est important pour maintenir un état cohérent et économiser les ressources.
        """
        if cls._instance is None:
            cls._instance = super(PDFTranslationService, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Initialise le service uniquement si ce n'est pas déjà fait.
        Utilise un flag de classe pour éviter les initialisations multiples.
        """
        if not self._initialized:
            self.initialize_components()
            self.__class__._initialized = True

    def initialize_components(self) -> None:
        """
        Configure tous les composants nécessaires au service de traduction.
        Cette méthode est appelée une seule fois lors de la première initialisation.
        """
        # Configuration du logging
        self.logger = logging.getLogger("PDFTranslationService")

        # Initialisation des composants de base
        self.translation_cache = TranslationCache()
        self.html_exporter = HTMLExporter()

        # Configuration des répertoires de sortie
        from pathlib import Path
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Initialisation des extracteurs
        self.image_extractor = EnhancedPDFImageExtractor(
            output_dir=str(images_dir)
        )
        self.text_extractor = EnhancedTextExtractor()

        # Configuration des traducteurs disponibles
        self.translators = {
            "groq": GroqTranslator(api_key=Settings.GROQ_API_KEY),
            "huggingface": HuggingFaceTranslator()
        }

        # Initialisation des services spécialisés
        self.file_service = FileService()
        self.extraction_service = ExtractionService(self.text_extractor, self.image_extractor)
        self.translation_service = TranslationService(self.translators)
        self.cache_service = CacheService(self.translation_cache)
        self.result_builder = ResultBuilder(self.html_exporter)

        self.logger.info("Service de traduction PDF initialisé avec succès")

    async def process_file(self,
                          file: UploadFile,
                          page_number: int,
                          source_lang: str,
                          target_lang: str,
                          translator_type: str = "groq") -> Dict:
        """
        Orchestre le processus complet de traduction d'une page de PDF.

        Args:
            file: Le fichier PDF à traiter
            page_number: Le numéro de la page à traduire
            source_lang: La langue source du document
            target_lang: La langue cible pour la traduction
            translator_type: Le type de traducteur à utiliser (défaut: "groq")

        Returns:
            Dict: Le résultat complet de la traduction avec métadonnées

        Raises:
            Exception: Toute erreur survenue pendant le processus
        """
        temp_file = None
        try:
            # Étape 1: Sauvegarde temporaire du fichier
            temp_file = await self.file_service.save_temp_file(file)
            self.logger.info(f"Fichier temporaire créé : {temp_file}")

            # Étape 2: Extraction du contenu
            extraction_result = await self.extraction_service.extract_pdf_components(
                temp_file,
                page_number
            )

            # Étape 3: Vérification du cache
            try:
                cached_result = self.cache_service.get_cached_translation(
                    extraction_result['text_to_translate'],
                    source_lang,
                    target_lang
                )
                if cached_result:
                    self.logger.info("Traduction trouvée dans le cache")
                    return cached_result
                self.logger.info("Aucune traduction en cache trouvée")
            except Exception as cache_error:
                self.logger.warning(f"Erreur lors de la vérification du cache: {str(cache_error)}")
                cached_result = None

            # Étape 4: Traduction du contenu
            translation_result = await self.translation_service.translate_content(
                extraction_result['text_to_translate'],
                source_lang,
                target_lang,
                translator_type
            )

            # Étape 5: Construction du résultat final
            result = await self.result_builder.build_final_result(
                extraction_result,
                translation_result,
                page_number,
                source_lang,
                target_lang
            )

            # Étape 6: Mise en cache du résultat
            self.cache_service.save_translation(
                extraction_result['text_to_translate'],
                source_lang,
                target_lang,
                result
            )

            return result

        except Exception as e:
            self.logger.error(f"Erreur lors du traitement : {str(e)}")
            raise

        finally:
            # Nettoyage : suppression du fichier temporaire
            if temp_file:
                await self.file_service.cleanup_temp_file(temp_file)