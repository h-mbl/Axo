from .translator_base import TranslatorBase
from groq import Groq
import os


class GroqTranslator(TranslatorBase):
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        prompt = f"""Translate the following text from {source_lang} to {target_lang}. 
        Preserve all [IMAGEx] markers exactly as they appear:

        {text}"""

        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content.strip()
