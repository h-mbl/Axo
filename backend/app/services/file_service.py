# backend/app/services/file_service.py
import tempfile
import aiofiles
import os
import logging
import shutil
from fastapi import UploadFile
from pathlib import Path


class FileService:
    def __init__(self):
        self.logger = logging.getLogger("FileService")

    @staticmethod
    async def save_temp_file(file: UploadFile) -> str:
        """
        Sauvegarde un fichier téléchargé dans un fichier temporaire.

        Args:
            file: Le fichier téléchargé

        Returns:
            Le chemin vers le fichier temporaire
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf').name
        async with aiofiles.open(temp_file, 'wb') as out_file:
            while chunk := await file.read(8192):
                await out_file.write(chunk)
        return temp_file

    @staticmethod
    async def cleanup_temp_file(temp_file: str):
        """
        Nettoie un fichier temporaire.

        Args:
            temp_file: Le chemin vers le fichier temporaire
        """
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
                logging.debug("Fichier temporaire supprimé avec succès")
            except Exception as e:
                logging.warning(f"Erreur lors de la suppression du fichier temporaire: {str(e)}")

    @staticmethod
    def copy_file(source_path: str, dest_path: str):
        """
        Copie un fichier d'un chemin à un autre.

        Args:
            source_path: Le chemin source
            dest_path: Le chemin de destination
        """
        try:
            shutil.copyfile(source_path, dest_path)
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la copie du fichier: {str(e)}")
            return False

    @staticmethod
    def ensure_directory_exists(directory_path: str or Path):
        """
        S'assure qu'un répertoire existe, le crée si nécessaire.

        Args:
            directory_path: Le chemin du répertoire
        """
        Path(directory_path).mkdir(parents=True, exist_ok=True)