# ui/components/progress.py

import streamlit as st
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class ProgressBar:
    """Classe per gestire una barra di progresso con messaggi di stato."""
    
    def __init__(self, total_steps: int, description: str = "Elaborazione in corso..."):
        """
        Inizializza la barra di progresso.
        
        Args:
            total_steps: Numero totale di step
            description: Descrizione dell'operazione
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.status = st.status(description)
        self.progress = self.status.progress(0)
        self.error_container = None
        logger.debug(f"ProgressBar inizializzata con {total_steps} steps")
        
    def update(self, step: int, message: Optional[str] = None, is_warning: bool = False):
        """
        Aggiorna la barra di progresso.
        
        Args:
            step: Step corrente (0-100)
            message: Messaggio opzionale da mostrare
            is_warning: Se True, mostra il messaggio come warning
        """
        # Assicuriamoci che lo step sia tra 0 e 100
        self.current_step = max(0, min(step, 100))
        progress_value = self.current_step / 100  # Invece di self.total_steps
        
        # Aggiorna la progress bar
        self.progress.progress(progress_value)
        
        if message:
            if is_warning:
                self.status.warning(message)
            else:
                self.status.write(message)
            logger.debug(f"Progress {progress_value*100:.0f}%: {message}")
    
    def complete(self, success: bool = True, message: Optional[str] = None):
        """
        Completa la barra di progresso.
        
        Args:
            success: True se l'operazione è stata completata con successo
            message: Messaggio opzionale da mostrare
        """
        if success:
            # Forza al 100% prima di completare
            self.progress.progress(1.0)
            status_message = message or "✅ Elaborazione completata!"
            self.status.update(label=status_message, state="complete")
        else:
            status_message = message or "❌ Errore nell'elaborazione!"
            self.status.update(label=status_message, state="error")
                
    def show_error(self, error_message: str, error_details: Optional[str] = None):
        """
        Mostra un errore nella barra di progresso.
        
        Args:
            error_message: Messaggio di errore principale
            error_details: Dettagli aggiuntivi dell'errore
        """
        self.status.error(error_message)
        if error_details:
            st.code(error_details)
  