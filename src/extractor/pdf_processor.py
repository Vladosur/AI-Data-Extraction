# src/extractor/pdf_processor.py

import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
from typing import List
import io
import os
import time
import hashlib
from src.config.settings import IMAGE_SETTINGS
from src.utils.logger import setup_logger
from src.utils.image_utils import optimize_image
from src.utils.pdf_validator import PDFValidator, PDFValidationError

logger = setup_logger(__name__)

class PDFProcessor:
    """Classe per la gestione e il processamento dei file PDF."""
    
    def __init__(self, temp_dir: Path):
        """
        Inizializza il processore PDF.
        
        Args:
            temp_dir (Path): Directory per i file temporanei
        """
        self.temp_dir = temp_dir
        self.validator = PDFValidator()
        self._ensure_temp_dir()

    def _ensure_temp_dir(self) -> None:
        """Crea la directory temporanea se non esiste."""
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory temporanea creata/verificata: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Errore nella creazione della directory temporanea: {e}")
            raise

    def _safe_remove(self, file_path: Path, max_attempts: int = 3) -> None:
        """
        Tenta di rimuovere un file in modo sicuro con più tentativi.
        
        Args:
            file_path: Percorso del file da rimuovere
            max_attempts: Numero massimo di tentativi
        """
        for attempt in range(max_attempts):
            try:
                if file_path.exists():
                    file_path.unlink()
                return
            except PermissionError:
                if attempt < max_attempts - 1:
                    time.sleep(0.1)  # Breve attesa tra i tentativi
                    continue
                logger.warning(f"Impossibile rimuovere il file temporaneo: {file_path}")

    def _get_pdf_hash(self, pdf_content: bytes) -> str:
        """
        Genera un hash univoco per il contenuto del PDF.
        
        Args:
            pdf_content: Contenuto binario del PDF
            
        Returns:
            str: Hash del PDF
        """
        return hashlib.md5(pdf_content).hexdigest()[:10]

    def _get_cached_images(self, pdf_hash: str) -> List[Path]:
        """
        Cerca immagini già elaborate per questo PDF.
        
        Args:
            pdf_hash: Hash del PDF
            
        Returns:
            List[Path]: Lista dei percorsi delle immagini trovate
        """
        cached_images = sorted(
            self.temp_dir.glob(f"page_{pdf_hash}_*.jpg"),
            key=lambda x: int(x.stem.split('_')[-1])
        )
        return cached_images

    def process_pdf(self, pdf_file, dpi: int = IMAGE_SETTINGS['DPI']) -> List[Path]:
        """
        Converte PDF in immagini usando PyMuPDF, con validazione e gestione errori.
        
        Args:
            pdf_file: File PDF da processare (può essere UploadedFile, Path o file object)
            dpi: Risoluzione delle immagini
            
        Returns:
            List[Path]: Lista dei percorsi delle immagini
            
        Raises:
            PDFValidationError: Se il PDF non supera la validazione
        """
        logger.info(f"Inizia processamento PDF")
        
        try:
            # Ottieni il contenuto del PDF in base al tipo di input
            if hasattr(pdf_file, 'getvalue'):
                # Se è un UploadedFile di Streamlit
                pdf_content = pdf_file.getvalue()
            elif hasattr(pdf_file, 'read'):
                # Se è un file object (BufferedReader)
                pdf_content = pdf_file.read()
            elif isinstance(pdf_file, Path):
                # Se è un oggetto Path
                pdf_content = pdf_file.read_bytes()
            else:
                raise PDFValidationError("Tipo di file non supportato")

            # Genera hash del PDF
            pdf_hash = self._get_pdf_hash(pdf_content)
            
            # Cerca immagini in cache
            cached_images = self._get_cached_images(pdf_hash)
            if cached_images:
                logger.info(f"Trovate {len(cached_images)} immagini in cache")
                return cached_images

            # Se non ci sono immagini in cache, procedi con la conversione
            temp_pdf = None
            pdf_document = None
            image_paths = []
            
            try:
                # Salva il PDF temporaneo
                temp_pdf = self.temp_dir / f"temp_{pdf_hash}.pdf"
                temp_pdf.write_bytes(pdf_content)
                
                # Validazione preliminare
                is_valid, error_message = self.validator.validate_pdf(temp_pdf)
                if not is_valid:
                    raise PDFValidationError(error_message)
                
                # Apri il PDF
                pdf_document = fitz.open(str(temp_pdf))
                
                # Controllo struttura
                is_structure_valid, structure_error = self.validator.check_pdf_structure(pdf_document)
                if not is_structure_valid:
                    raise PDFValidationError(structure_error)
                
                # Stima requisiti
                requirements = self.validator.estimate_processing_requirements(pdf_document)
                logger.info(f"Requisiti stimati: {requirements}")
                
                # Controllo memoria disponibile (esempio)
                if requirements.get('estimated_memory_mb', 0) > 1000:  # 1GB
                    logger.warning("Il PDF richiede molta memoria per l'elaborazione")
                
                # Converti le pagine con gestione errori per pagina
                for page_num in range(pdf_document.page_count):
                    try:
                        page = pdf_document[page_num]
                        zoom = dpi / 72
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat)
                        
                        # Converti in immagine PIL
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        optimized = optimize_image(img)
                        
                        # Salva con il nome basato sull'hash
                        img_path = self.temp_dir / f"page_{pdf_hash}_{page_num + 1}.jpg"
                        optimized.save(
                            img_path,
                            format=IMAGE_SETTINGS['FORMAT'],
                            quality=IMAGE_SETTINGS['QUALITY']
                        )
                        image_paths.append(img_path)
                        
                        # Libera memoria
                        del pix
                        del img
                        del optimized
                        
                    except Exception as e:
                        logger.error(f"Errore nella conversione della pagina {page_num + 1}: {e}")
                        # Continua con la prossima pagina invece di fallire completamente
                        continue
                
                if not image_paths:
                    raise PDFValidationError("Nessuna pagina è stata convertita con successo")
                
                logger.info(f"Generate {len(image_paths)} nuove immagini")
                return image_paths
                
            except PDFValidationError as e:
                logger.error(f"Errore di validazione PDF: {e}")
                # Pulizia in caso di errore
                for img_path in image_paths:
                    self._safe_remove(img_path)
                raise
                
            except Exception as e:
                logger.error(f"Errore nella conversione del PDF: {e}")
                # Pulizia in caso di errore
                for img_path in image_paths:
                    self._safe_remove(img_path)
                raise PDFValidationError(f"Errore durante l'elaborazione del PDF: {str(e)}")
                
            finally:
                if pdf_document:
                    pdf_document.close()
                if temp_pdf and temp_pdf.exists():
                    self._safe_remove(temp_pdf)
                    
        except Exception as e:
            logger.error(f"Errore generale nel processo PDF: {e}")
            raise PDFValidationError(f"Errore durante il processo PDF: {str(e)}")

    def cleanup(self, older_than_days: int = 7):
        """
        Pulisce i file temporanei più vecchi di X giorni.
        
        Args:
            older_than_days: Elimina file più vecchi di questi giorni
        """
        try:
            current_time = time.time()
            for file in self.temp_dir.glob("*"):
                # Controlla l'età del file
                file_age = current_time - file.stat().st_mtime
                if file_age > (older_than_days * 24 * 3600):
                    self._safe_remove(file)
            logger.info(f"Pulizia file più vecchi di {older_than_days} giorni completata")
        except Exception as e:
            logger.error(f"Errore durante la pulizia dei file temporanei: {e}")