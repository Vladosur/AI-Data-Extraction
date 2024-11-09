"""
Package per l'estrazione e l'elaborazione dei dati da PDF.
"""

from .pdf_processor import PDFProcessor
from .vision_api import VisionAPI
from .data_processor import DataProcessor

__all__ = ['PDFProcessor', 'VisionAPI', 'DataProcessor']

# Versione del package
__version__ = '0.1.0'