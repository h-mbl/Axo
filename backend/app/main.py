from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import fitz
from transformers import MarianMTModel, MarianTokenizer
import torch
import logging
from typing import Optional
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionnaire des modèles de traduction disponibles
TRANSLATION_MODELS = {
    "fr-en": "Helsinki-NLP/opus-mt-fr-en",
    "en-fr": "Helsinki-NLP/opus-mt-en-fr",
    # Ajoutez d'autres paires de langues selon vos besoins
}


class TranslationModel:
    def __init__(self, model_name: str):
        try:
            logger.info(f"Chargement du modèle {model_name}")
            self.tokenizer = MarianTokenizer.from_pretrained(model_name)
            self.model = MarianMTModel.from_pretrained(model_name)
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
            logger.info("Modèle chargé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {str(e)}")
            raise

    def translate(self, text: str) -> str:
        try:
            # Tokenization
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            if torch.cuda.is_available():
                inputs = {k: v.to('cuda') for k, v in inputs.items()}

            # Traduction
            outputs = self.model.generate(**inputs)

            # Décodage
            translated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated_text
        except Exception as e:
            logger.error(f"Erreur lors de la traduction: {str(e)}")
            raise


# Dictionnaire pour stocker les instances des modèles
translation_models = {}


def get_translation_model(source_lang: str, target_lang: str) -> TranslationModel:
    model_key = f"{source_lang}-{target_lang}"
    if model_key not in TRANSLATION_MODELS:
        raise HTTPException(status_code=400, detail="Paire de langues non supportée")

    if model_key not in translation_models:
        try:
            translation_models[model_key] = TranslationModel(TRANSLATION_MODELS[model_key])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors du chargement du modèle: {str(e)}")

    return translation_models[model_key]


@app.post("/translate")
async def translate_pdf_page(
        file: UploadFile,
        page_number: int = Form(...),
        source_language: str = Form(...),
        target_language: str = Form(...),
):
    try:
        # Vérification du numéro de page
        if page_number < 1:
            raise HTTPException(status_code=400, detail="Le numéro de page doit être positif")

        # Lecture du fichier PDF
        pdf_content = await file.read()
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

        # Vérification du numéro de page par rapport au nombre total de pages
        if page_number > pdf_document.page_count:
            raise HTTPException(
                status_code=400,
                detail=f"Le numéro de page demandé ({page_number}) dépasse le nombre total de pages ({pdf_document.page_count})"
            )

        # Extraction du texte
        page = pdf_document[page_number - 1]
        text = page.get_text()

        if not text.strip():
            return {
                "success": True,
                "translated_text": "",
                "message": "Aucun texte à traduire sur cette page"
            }

        # Obtention du modèle de traduction
        translation_model = get_translation_model(source_language, target_language)

        # Traduction
        translated_text = translation_model.translate(text)

        return {
            "success": True,
            "translated_text": translated_text,
            "page_number": page_number
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erreur lors de la traduction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'pdf_document' in locals():
            pdf_document.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)