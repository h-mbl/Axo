import tempfile
import aiofiles
import os
import logging
from fastapi import UploadFile

class FileService:
    def __init__(self):
        self.logger = logging.getLogger("FileService")
    @staticmethod
    async def save_temp_file(file: UploadFile) -> str:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        async with aiofiles.open(temp_file, 'wb') as out_file:
            while chunk := await file.read(8192):
                await out_file.write(chunk)
        return temp_file

    @staticmethod
    async def cleanup_temp_file(temp_file: str):
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                logging.debug("Fichier temporaire supprimé avec succès")
            except Exception as e:
                logging.warning(f"Erreur lors de la suppression du fichier temporaire: {str(e)}")