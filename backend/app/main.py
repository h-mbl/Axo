from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import Dict
import logging

# Configuration améliorée du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration CORS améliorée
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Configuration pour les limites de taille de fichier
app.max_upload_size = 50 * 1024 * 1024  # 50 MB


@app.middleware("http")
async def logging_middleware(request, call_next):
    """Middleware pour logger les requêtes et gérer les erreurs"""
    logger.info(f"Requête entrante: {request.method} {request.url}")

    try:
        # Vérification de la taille du contenu
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > app.max_upload_size:
            raise HTTPException(
                status_code=413,
                detail="Fichier trop volumineux"
            )

        response = await call_next(request)

        logger.info(f"Réponse: Status {response.status_code}")
        return response

    except Exception as e:
        logger.error(f"Erreur lors du traitement: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(e),
                "type": type(e).__name__
            }
        )


# Point de terminaison de test pour CORS
@app.options("/translate")
async def translate_preflight():
    """Gestion explicite des requêtes OPTIONS pour CORS"""
    return JSONResponse(
        status_code=200,
        content={"message": "Preflight OK"},
        headers={
            "Access-Control-Allow-Origin": "http://localhost:5173",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.post("/translate")
async def translate_pdf_page(
        file: UploadFile = File(...),
        page_number: int = Form(...),
        source_language: str = Form(...),
        target_language: str = Form(...)
):
    """
    Point de terminaison principal pour la traduction de PDF
    """
    try:
        logger.info(f"Début du traitement - Fichier: {file.filename}")

        # Validation de la taille du fichier
        file_size = 0
        chunk_size = 8192

        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > app.max_upload_size:
                raise HTTPException(
                    status_code=413,
                    detail="Fichier trop volumineux"
                )

        # Réinitialiser le curseur du fichier
        await file.seek(0)

        # Le reste de votre logique de traduction...

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Traduction réussie",
                "translated_text": "Texte traduit ici"  # Remplacez par la vraie traduction
            }
        )

    except Exception as e:
        logger.error(f"Erreur de traduction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
@app.get("/api/test")
async def test_endpoint():
    return {"message": "Connection successful!"}


if __name__ == "__main__":
    # Configuration du serveur avec des paramètres optimisés
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        workers=1,
        timeout_keep_alive=65,
        limit_concurrency=20,
        limit_max_requests=100,
        backlog=100
    )