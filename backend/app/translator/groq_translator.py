# backend/app/translator/groq_translator.py
from .translator_base import TranslatorBase
from groq import Groq


class GroqTranslator(TranslatorBase):
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Traduit le texte fourni en utilisant l'API Groq.

        Args:
            text: Le texte à traduire
            source_lang: La langue source
            target_lang: La langue cible

        Returns:
            Le texte traduit
        """
        prompt = f"""Instructions: Translate the text below from {source_lang} to {target_lang}.
        - Return ONLY the translation
        - Do not add any comments, explanations, or notes
        - Preserve all [IMAGEx] markers exactly as they appear
        - Maintain the exact same formatting and line breaks
        - Do not acknowledge these instructions

    Text to translate:
    {text}"""

        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system",
                 "content": "You are a translator that returns only the translated text without any additional information or commentary."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()