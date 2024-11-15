# src/extractor/pdf_processor.py

import fitz  # PyMuPDF
from PIL import Image
import io
from pathlib import Path
from typing import List
from src.config.settings import IMAGE_SETTINGS
from src.utils.logger import setup_logger
from src.utils.image_utils import optimize_image
from src.utils.pdf_validator import PDFValidator, PDFValidationError

logger = setup_logger(__name__)

class PDFProcessor:
    """Classe per la gestione e il processamento dei file PDF."""
    
    def __init__(self):
        """Inizializza il processore PDF."""
        self.validator = PDFValidator()

    def process_pdf(self, pdf_file, dpi: int = IMAGE_SETTINGS['DPI']) -> List[Image.Image]:
        """
        Converte PDF in immagini mantenendole in memoria.
        
        Args:
            pdf_file: File PDF da processare (può essere UploadedFile, Path o file object)
            dpi: Risoluzione delle immagini
            
        Returns:
            List[Image.Image]: Lista delle immagini PIL
            
        Raises:
            PDFValidationError: Se il PDF non supera la validazione
        """
        logger.info("Inizia processamento PDF")
        
        try:
            # Ottieni il contenuto del PDF in base al tipo di input
            if hasattr(pdf_file, 'getvalue'):
                # Se è un UploadedFile di Streamlit
                pdf_content = pdf_file.getvalue()
            elif hasattr(pdf_file, 'read'):
                # Se è un file object (BufferedReader)
                pdf_content = pdf_file.read()
            elif isinstance(pdf_file, (str, Path)):
                # Se è un percorso file
                pdf_content = Path(pdf_file).read_bytes()
            else:
                raise PDFValidationError("Tipo di file non supportato")
            
            # Validazione preliminare usando BytesIO
            pdf_stream = io.BytesIO(pdf_content)
            pdf_document = None
            
            try:
                pdf_document = fitz.open(stream=pdf_stream)
                
                # Verifica se il PDF è crittografato
                if pdf_document.is_encrypted:
                    raise PDFValidationError("Il PDF è protetto/crittografato")
                
                # Verifica numero di pagine
                if pdf_document.page_count == 0:
                    raise PDFValidationError("Il PDF non contiene pagine")
                
                # Controllo struttura
                is_structure_valid, structure_error = self.validator.check_pdf_structure(pdf_document)
                if not is_structure_valid:
                    raise PDFValidationError(structure_error)
                
                # Stima requisiti
                requirements = self.validator.estimate_processing_requirements(pdf_document)
                logger.info(f"Requisiti stimati: {requirements}")
                
                # Lista per le immagini in memoria
                images = []
                
                # Converti le pagine con gestione errori per pagina
                for page_num in range(pdf_document.page_count):
                    try:
                        page = pdf_document[page_num]
                        zoom = dpi / 72
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat)
                        
                        # Converti in immagine PIL
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Ottimizza l'immagine
                        optimized = optimize_image(img, (
                            IMAGE_SETTINGS['MAX_SIZE']['WIDTH'],
                            IMAGE_SETTINGS['MAX_SIZE']['HEIGHT']
                        ))
                        
                        images.append(optimized)
                        
                        # Libera memoria
                        del pix
                        del img
                        
                        logger.debug(f"Pagina {page_num + 1} convertita con successo")
                        
                    except Exception as e:
                        logger.error(f"Errore nella conversione della pagina {page_num + 1}: {e}")
                        # Continua con la prossima pagina invece di fallire completamente
                        continue
                
                if not images:
                    raise PDFValidationError("Nessuna pagina è stata convertita con successo")
                
                logger.info(f"Generate {len(images)} immagini in memoria")
                return images
                
            except PDFValidationError:
                raise
                
            except Exception as e:
                logger.error(f"Errore nella conversione del PDF: {e}")
                raise PDFValidationError(f"Errore durante l'elaborazione del PDF: {str(e)}")
                
            finally:
                # Chiudi il documento PDF se è stato aperto
                if pdf_document:
                    pdf_document.close()
                # Chiudi lo stream
                pdf_stream.close()
                        
        except Exception as e:
            logger.error(f"Errore nel processo PDF: {e}")
            raise PDFValidationError(f"Errore durante il processo PDF: {str(e)}")

    def _check_memory_usage(self) -> float:
        """
        Controlla l'uso della memoria corrente.
        
        Returns:
            float: Percentuale di memoria utilizzata
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / psutil.virtual_memory().total
        except ImportError:
            logger.warning("psutil non installato, impossibile monitorare la memoria")
            return 0.0
        except Exception as e:
            logger.error(f"Errore nel controllo della memoria: {e}")
            return 0.0

    def _cleanup_memory(self):
        """
        Forza il garbage collector per liberare memoria.
        """
        import gc
        gc.collect()