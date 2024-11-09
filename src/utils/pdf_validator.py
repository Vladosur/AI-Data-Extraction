# src/utils/pdf_validator.py

import fitz  # PyMuPDF
from pathlib import Path
from typing import Tuple, Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class PDFValidationError(Exception):
    """Eccezione personalizzata per errori di validazione PDF."""
    pass

class PDFValidator:
    """Classe per la validazione approfondita dei file PDF."""
    
    @staticmethod
    def validate_pdf(file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Esegue una validazione approfondita del file PDF.
        
        Args:
            file_path: Percorso del file PDF
            
        Returns:
            Tuple[bool, Optional[str]]: (validazione_ok, messaggio_errore)
        """
        try:
            # Verifica esistenza file
            if not file_path.exists():
                return False, "File non trovato"
            
            # Verifica se il file è vuoto
            if file_path.stat().st_size == 0:
                return False, "Il file PDF è vuoto"
            
            # Apertura e validazione con PyMuPDF
            pdf_document = None
            try:
                pdf_document = fitz.open(str(file_path))
                
                # Verifica se il PDF è crittografato
                if pdf_document.is_encrypted:
                    return False, "Il PDF è protetto/crittografato"
                
                # Verifica numero di pagine
                if pdf_document.page_count == 0:
                    return False, "Il PDF non contiene pagine"
                
                # Verifica corruzione pagine
                for page_num in range(pdf_document.page_count):
                    try:
                        page = pdf_document[page_num]
                        # Tenta di accedere ai contenuti della pagina
                        _ = page.get_text()
                    except Exception as e:
                        return False, f"La pagina {page_num + 1} è corrotta o non accessibile"
                
                return True, None
                
            except fitz.fitz.FileDataError:
                return False, "Il file non è un PDF valido o è corrotto"
            except Exception as e:
                return False, f"Errore durante la validazione del PDF: {str(e)}"
            finally:
                if pdf_document:
                    pdf_document.close()
                    
        except Exception as e:
            logger.error(f"Errore durante la validazione del PDF: {e}")
            return False, "Errore imprevisto durante la validazione del PDF"
    
    @staticmethod
    def check_pdf_structure(pdf_document) -> Tuple[bool, Optional[str]]:
        """
        Verifica la struttura interna del PDF.
        
        Args:
            pdf_document: Documento PDF aperto con PyMuPDF
            
        Returns:
            Tuple[bool, Optional[str]]: (struttura_ok, messaggio_errore)
        """
        try:
            # Verifica metadati
            if not pdf_document.metadata:
                logger.warning("PDF senza metadati")
            
            # Verifica struttura pagine
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                
                # Verifica dimensioni pagina
                if page.rect.width <= 0 or page.rect.height <= 0:
                    return False, f"Dimensioni non valide alla pagina {page_num + 1}"
                
                # Verifica contenuto
                if len(page.get_text().strip()) == 0 and len(page.get_images()) == 0:
                    logger.warning(f"Pagina {page_num + 1} potrebbe essere vuota")
            
            return True, None
            
        except Exception as e:
            logger.error(f"Errore durante il controllo della struttura PDF: {e}")
            return False, f"Errore nella struttura del PDF: {str(e)}"
    
    @staticmethod
    def estimate_processing_requirements(pdf_document) -> dict:
        """
        Stima i requisiti di elaborazione del PDF.
        
        Args:
            pdf_document: Documento PDF aperto con PyMuPDF
            
        Returns:
            dict: Dizionario con stime di memoria e tempo
        """
        try:
            total_pages = pdf_document.page_count
            total_images = sum(len(page.get_images()) for page in pdf_document)
            avg_page_size = sum(page.rect.width * page.rect.height for page in pdf_document) / total_pages
            
            # Stima memoria richiesta (molto approssimativa)
            est_memory_mb = (avg_page_size * total_pages * 4) / (1024 * 1024)  # 4 byte per pixel
            
            # Stima tempo di elaborazione (molto approssimativa)
            est_time_seconds = total_pages * 2 + total_images * 0.5  # 2 sec per pagina + 0.5 sec per immagine
            
            return {
                'total_pages': total_pages,
                'total_images': total_images,
                'estimated_memory_mb': round(est_memory_mb, 2),
                'estimated_time_seconds': round(est_time_seconds, 2)
            }
            
        except Exception as e:
            logger.error(f"Errore durante la stima dei requisiti: {e}")
            return {
                'error': str(e)
            }