from PIL import Image
from typing import Tuple, Optional
from src.config.settings import IMAGE_SETTINGS
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def validate_image(image: Image.Image) -> bool:
    """
    Valida formato e dimensioni dell'immagine.
    
    Args:
        image: Immagine PIL da validare
        
    Returns:
        bool: True se l'immagine è valida, False altrimenti
    """
    try:
        # Verifica formato
        if image.format not in ['JPEG', 'PNG']:
            logger.warning(f"Formato immagine non supportato: {image.format}")
            return False
            
        # Verifica dimensioni minime
        min_size = (100, 100)  # dimensioni minime ragionevoli
        if image.size[0] < min_size[0] or image.size[1] < min_size[1]:
            logger.warning(f"Immagine troppo piccola: {image.size}")
            return False
            
        # Verifica modalità colore
        if image.mode not in ['RGB', 'RGBA']:
            logger.warning(f"Modalità colore non supportata: {image.mode}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Errore durante la validazione dell'immagine: {e}")
        return False

def optimize_image(
    image: Image.Image,
    max_size: Optional[Tuple[int, int]] = None
) -> Image.Image:
    """
    Ottimizza l'immagine per l'invio all'API.
    
    Args:
        image: Immagine PIL da ottimizzare
        max_size: Dimensioni massime (width, height). Se None, usa IMAGE_SETTINGS
        
    Returns:
        Image.Image: Immagine ottimizzata
    """
    try:
        # Usa le dimensioni massime dalle impostazioni se non specificate
        if max_size is None:
            max_size = (
                IMAGE_SETTINGS['MAX_SIZE']['WIDTH'],
                IMAGE_SETTINGS['MAX_SIZE']['HEIGHT']
            )
        
        # Crea una copia dell'immagine
        img = image.copy()
        
        # Converti in RGB se necessario
        if img.mode == 'RGBA':
            logger.debug("Conversione da RGBA a RGB")
            img = img.convert('RGB')
        
        # Ridimensiona se necessario
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            logger.debug(f"Ridimensionamento da {img.size} a max {max_size}")
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        return img
        
    except Exception as e:
        logger.error(f"Errore durante l'ottimizzazione dell'immagine: {e}")
        raise

def get_image_info(image: Image.Image) -> dict:
    """
    Restituisce informazioni sull'immagine.
    
    Args:
        image: Immagine PIL
        
    Returns:
        dict: Dizionario con le informazioni sull'immagine
    """
    return {
        'format': image.format,
        'size': image.size,
        'mode': image.mode,
        'dpi': image.info.get('dpi', 'N/A')
    }
