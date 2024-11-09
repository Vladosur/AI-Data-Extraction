# src/utils/file_validator.py

import os
import re
from pathlib import Path
from typing import Optional, Tuple
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class FileValidator:
    """Classe per la validazione e sanitizzazione dei file."""
    
    # Limiti predefiniti
    MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS = {'.pdf'}
    FILENAME_MAX_LENGTH = 255
    
    @classmethod
    def validate_file(cls, file) -> Tuple[bool, Optional[str]]:
        """
        Valida un file controllando dimensione ed estensione.
        
        Args:
            file: File da validare (oggetto UploadedFile di Streamlit)
            
        Returns:
            Tuple[bool, Optional[str]]: (validazione_ok, messaggio_errore)
        """
        try:
            # Controllo dimensione
            if file.size > cls.MAX_FILE_SIZE:
                return False, f"Il file supera la dimensione massima consentita ({cls.MAX_FILE_SIZE/1024/1024:.1f}MB)"
            
            # Controllo estensione
            file_ext = Path(file.name).suffix.lower()
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                return False, f"Estensione file non consentita. Estensioni permesse: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            
            # Controllo lunghezza nome file
            if len(file.name) > cls.FILENAME_MAX_LENGTH:
                return False, f"Nome file troppo lungo (max {cls.FILENAME_MAX_LENGTH} caratteri)"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Errore durante la validazione del file: {e}")
            return False, "Errore durante la validazione del file"
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitizza il nome del file rimuovendo caratteri non sicuri.
        
        Args:
            filename: Nome del file da sanitizzare
            
        Returns:
            str: Nome file sanitizzato
        """
        try:
            # Separa nome ed estensione
            name, ext = os.path.splitext(filename)
            
            # Rimuovi caratteri non sicuri dal nome
            safe_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', name)
            
            # Rimuovi underscore multipli
            safe_name = re.sub(r'_+', '_', safe_name)
            
            # Rimuovi underscore iniziali e finali
            safe_name = safe_name.strip('_')
            
            # Se il nome è vuoto dopo la sanitizzazione, usa un default
            if not safe_name:
                safe_name = "file"
            
            # Ricomponi il nome con l'estensione originale
            return f"{safe_name}{ext.lower()}"
            
        except Exception as e:
            logger.error(f"Errore durante la sanitizzazione del nome file: {e}")
            return "file.pdf"
    
    @classmethod
    def get_safe_filepath(cls, base_dir: Path, filename: str) -> Path:
        """
        Genera un percorso file sicuro e univoco.
        
        Args:
            base_dir: Directory base
            filename: Nome del file originale
            
        Returns:
            Path: Percorso file sicuro e univoco
        """
        try:
            # Sanitizza il nome file
            safe_name = cls.sanitize_filename(filename)
            
            # Genera percorso base
            filepath = base_dir / safe_name
            
            # Se il file esiste, aggiungi un numero progressivo
            counter = 1
            while filepath.exists():
                name, ext = os.path.splitext(safe_name)
                filepath = base_dir / f"{name}_{counter}{ext}"
                counter += 1
            
            return filepath
            
        except Exception as e:
            logger.error(f"Errore durante la generazione del percorso file: {e}")
            return base_dir / "file.pdf"