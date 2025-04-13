# backend/app/main.py
import logging
import multiprocessing
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import de nos configurations et services
from backend.app.config.settings import Settings
from backend.app.services.pdf_translation_service import PDFTranslationService
from backend.app.models.translation_model import TranslationLayoutRecovery

# Création de l'application FastAPI avec une description claire
app = FastAPI(
    title="PDF Translation API avec Layout Recovery",
    description="API de traduction de documents PDF avec préservation de la mise en page",
    version="1.0.0"
)

# Configuration du point de montage pour les fichiers statiques
# Ceci permet d'accéder aux fichiers générés (HTML, images) via l'API
app.mount("/output", StaticFiles(directory=str(Settings.OUTPUT_DIR)), name="output")

# Configuration CORS pour permettre les requêtes depuis notre frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du service de traduction
# On utilise une seule instance grâce au pattern Singleton
translation_service = PDFTranslationService()

# Middleware pour vérifier la taille des fichiers uploadés
@app.middleware("http")
async def size_limit_middleware(request, call_next):
    """
    Vérifie que la taille du fichier uploadé ne dépasse pas la limite configurée.
    Rejette la requête si le fichier est trop volumineux.
    """
    content_length = request.headers.get('content-length')
    if content_length and int(content_length) > Settings.MAX_UPLOAD_SIZE:
        return JSONResponse(
            status_code=413,
            content={
                "detail": f"Fichier trop volumineux. Limite: {Settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            }
        )
    return await call_next(request)


# Point d'entrée principal pour la traduction
@app.post("/translate")
async def translate_pdf_page(
        file: UploadFile = File(...),
        page_number: int = Form(...),
        source_language: str = Form("en"),
        target_language: str = Form("fr"),
        translator_type: str = Form("groq")
):
    """
    Endpoint principal pour la traduction d'une page de PDF.

    Args:
        file: Le fichier PDF à traduire
        page_number: Le numéro de la page à traduire
        source_language: La langue source du document
        target_language: La langue cible pour la traduction
        translator_type: Le type de traducteur à utiliser

    Returns:
        JSONResponse contenant les résultats de la traduction
    """
    try:
        # Validation du type de fichier
        if not file.content_type == "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Le fichier doit être au format PDF"
            )

        # Validation de la langue cible
        a = False
        if target_language not in Settings.SUPPORTED_LANGUAGES.values() and a == True:
            supported_langs = ", ".join(Settings.SUPPORTED_LANGUAGES.values())
            raise HTTPException(
                status_code=400,
                detail=f"Langue cible non supportée. Langues supportées: {supported_langs}"
            )

        # Traitement de la traduction via notre service
        result = await translation_service.process_file(
            file=file,
            page_number=page_number,
            source_lang=source_language,
            target_lang=target_language,
            translator_type=translator_type
        )

        return JSONResponse(content=result)

    except Exception as e:
        logging.error(f"Erreur lors de la traduction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint de monitoring pour vérifier l'état du service
@app.get("/health")
async def health_check():
    """
    Vérifie l'état de santé de l'API.
    Utilisé pour le monitoring et les health checks.
    """
    return {
        "status": "healthy",
        "service": "PDF Translation API",
        "version": "1.0.0",
        "supported_languages": Settings.SUPPORTED_LANGUAGES
    }


# Point d'entrée du programme
if __name__ == "__main__":
    # Configuration nécessaire pour Windows
    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn', force=True)

    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log')
        ]
    )

    # Démarrage du serveur avec la configuration de Settings
    uvicorn.run(
        "main:app",
        host=Settings.API_HOST,
        port=Settings.API_PORT,
        reload=Settings.DEBUG,
        workers=Settings.WORKERS,
        timeout_keep_alive=Settings.TIMEOUT_KEEP_ALIVE,
    )