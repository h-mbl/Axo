# backend/app/main.py
import os
import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pathlib import Path
import tempfile
import aiofiles

# Import du modèle principal
from backend.app.model.main import TranslationLayoutRecovery

# Création de l'application FastAPI
app = FastAPI(
    title="PDF Translation API",
    description="API pour la traduction de documents PDF avec préservation de la mise en page",
    version="1.0.0"
)

# Configuration CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permettre toutes les origines ou spécifier les vôtres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Créer le dossier de sortie s'il n'existe pas
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)
images_dir = output_dir / "images"
images_dir.mkdir(exist_ok=True)

# Point de montage pour accéder aux fichiers générés
app.mount("/output", StaticFiles(directory="output"), name="output")

# Initialisation du modèle de traduction
translation_model = TranslationLayoutRecovery()


async def save_upload_file(upload_file: UploadFile) -> str:
    """Sauvegarde le fichier uploadé et retourne son chemin"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    try:
        contents = await upload_file.read()
        with open(temp_file.name, 'wb') as f:
            f.write(contents)
    except Exception:
        return None
    finally:
        await upload_file.close()
    return temp_file.name


@app.post("/translate")
async def translate_pdf(
        file: UploadFile = File(...),
        page_number: int = Form(...),
        source_language: str = Form("English"),
        target_language: str = Form("French")
):
    """
    Endpoint pour traduire une page de PDF
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Le fichier doit être au format PDF")

    # Créer le dossier de sortie PDF s'il n'existe pas
    pdf_dir = output_dir / "PDFs"
    pdf_dir.mkdir(exist_ok=True)

    # Sauvegarder le fichier
    temp_file_path = await save_upload_file(file)
    if not temp_file_path:
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde du fichier")

    try:
        # Traduire le PDF
        translation_model.translate_pdf(
            input_path=temp_file_path,
            language=target_language.lower()[:2],  # Utiliser seulement le code de langue (fr, ja, vi)
            output_path=str(pdf_dir),
            merge=False
        )

        # Préparer la réponse
        translated_pdf_path = "output/PDFs/fitz_translated.pdf"
        return JSONResponse(content={
            "success": True,
            "message": "Traduction terminée avec succès",
            "file_path": translated_pdf_path,
            "page_number": page_number
        })
    except Exception as e:
        logging.error(f"Erreur lors de la traduction: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Nettoyer le fichier temporaire
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)