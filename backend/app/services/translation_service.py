import asyncio
import logging

class TranslationService:
    def __init__(self, translators):
        self.translators = translators
        self.logger = logging.getLogger("TranslationService")

    async def translate_content(self,
                              text: str,
                              source_lang: str,
                              target_lang: str,
                              translator_type: str) -> str:
        """Traduit le contenu textuel avec le traducteur spécifié."""
        try:
            translator = self.translators.get(translator_type)
            if not translator:
                raise ValueError(f"Traducteur non supporté : {translator_type}")

            return await asyncio.to_thread(
                translator.translate,
                text,
                source_lang,
                target_lang
            )
        except Exception as e:
            self.logger.error(f"Erreur lors de la traduction: {str(e)}")
            raise