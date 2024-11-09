# ui/components/file_uploader.py

import streamlit as st
from pathlib import Path
from typing import Optional
from src.utils.logger import setup_logger
from src.utils.file_validator import FileValidator

logger = setup_logger(__name__)

def custom_file_uploader() -> Optional[st.runtime.uploaded_file_manager.UploadedFile]:
    """
    Componente personalizzato per il caricamento dei file PDF.
    
    Returns:
        UploadedFile o None se nessun file è stato caricato
    """
    uploaded_file = st.file_uploader(
        "Carica il documento PDF",
        type="pdf",
        help=f"Limite {FileValidator.MAX_FILE_SIZE/1024/1024:.1f}MB per file • Solo PDF",
        accept_multiple_files=False,
        key="pdf_uploader"
    )
    
    if uploaded_file:
        # Validazione file
        is_valid, error_message = FileValidator.validate_file(uploaded_file)
        if not is_valid:
            st.error(f"⚠️ {error_message}")
            return None
            
        # Sanitizzazione nome file
        safe_name = FileValidator.sanitize_filename(uploaded_file.name)
        if safe_name != uploaded_file.name:
            logger.info(f"Nome file sanitizzato da '{uploaded_file.name}' a '{safe_name}'")
            
        # Log del caricamento
        logger.info(f"File caricato: {safe_name} ({uploaded_file.size/1024/1024:.1f} MB)")
        
        # Mostra info file
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"File caricato: {safe_name}")
        with col2:
            st.info(f"Dimensione: {uploaded_file.size/1024/1024:.1f} MB")
            
        return uploaded_file
    
    return None