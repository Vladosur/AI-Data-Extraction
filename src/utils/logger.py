import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from src.config.settings import LOG_SETTINGS

def setup_logger(name: str = "pdf_extractor") -> logging.Logger:
    """
    Configura e restituisce un logger con rotazione dei file.
    
    Args:
        name: Nome del logger
        
    Returns:
        Logger configurato
    """
    # Crea la directory dei log se non esiste
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configura il logger
    logger = logging.getLogger(name)
    logger.setLevel(LOG_SETTINGS['LEVEL'])
    
    # Formattazione
    formatter = logging.Formatter(
        fmt=LOG_SETTINGS['FORMAT'],
        datefmt=LOG_SETTINGS['DATE_FORMAT']
    )
    
    # Handler per il file con rotazione
    file_handler = RotatingFileHandler(
        LOG_SETTINGS['FILE'],
        maxBytes=LOG_SETTINGS['MAX_BYTES'],
        backupCount=LOG_SETTINGS['BACKUP_COUNT']
    )
    file_handler.setFormatter(formatter)
    
    # Handler per la console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Aggiungi gli handler
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("Logger inizializzato")
    return logger  
