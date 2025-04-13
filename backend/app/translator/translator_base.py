# backend/app/translator/translator_base.py
from abc import ABC, abstractmethod


class TranslatorBase(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Traduit le texte fourni de la langue source vers la langue cible.

        Args:
            text: Le texte à traduire
            source_lang: La langue source
            target_lang: La langue cible

        Returns:
            Le texte traduit
        """
        pass