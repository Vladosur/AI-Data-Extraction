# src/utils/retry_manager.py

import time
from typing import TypeVar, Callable, Any, Optional, Tuple
from functools import wraps
from src.utils.logger import setup_logger
import openai
from openai import (
    APIError,
    APIConnectionError,
    RateLimitError
)

logger = setup_logger(__name__)

T = TypeVar('T')

class RetryError(Exception):
    """Eccezione sollevata quando tutti i tentativi di retry falliscono."""
    def __init__(self, message: str, last_error: Optional[Exception] = None):
        self.message = message
        self.last_error = last_error
        super().__init__(self.message)

class RetryManager:
    """Gestore delle politiche di retry per le chiamate API."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        """
        Inizializza il gestore dei retry.
        
        Args:
            max_retries: Numero massimo di tentativi
            initial_delay: Ritardo iniziale in secondi
            max_delay: Ritardo massimo in secondi
            backoff_factor: Fattore di incremento del ritardo
            jitter: Se True, aggiunge una componente casuale al ritardo
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        
    def calculate_delay(self, attempt: int) -> float:
        """
        Calcola il ritardo per il tentativo corrente.
        
        Args:
            attempt: Numero del tentativo corrente
            
        Returns:
            float: Ritardo in secondi
        """
        delay = min(
            self.initial_delay * (self.backoff_factor ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Aggiunge una componente casuale ±20%
            import random
            jitter_range = delay * 0.2
            delay += random.uniform(-jitter_range, jitter_range)
            
        return max(0, delay)  # Assicura che il delay non sia negativo
        
    def should_retry(self, error: Exception) -> bool:
        """
        Determina se un errore dovrebbe causare un retry.
        
        Args:
            error: Eccezione da valutare
            
        Returns:
            bool: True se si dovrebbe ritentare
        """
        # Lista di errori che giustificano un retry
        RETRIABLE_ERRORS = (
            APIError,           # Errori API generici
            APIConnectionError, # Errori di connessione
            RateLimitError,    # Rate limiting
            TimeoutError,      # Timeout
            ConnectionError,    # Errori di rete
        )
        
        return isinstance(error, RETRIABLE_ERRORS)
        
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> Tuple[Optional[T], Optional[Exception]]:
        """
        Esegue una funzione con politica di retry.
        
        Args:
            func: Funzione da eseguire
            *args: Argomenti posizionali per la funzione
            **kwargs: Argomenti nominali per la funzione
            
        Returns:
            Tuple[Optional[T], Optional[Exception]]: Risultato e eventuale errore
            
        Raises:
            RetryError: Se tutti i tentativi falliscono
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Tentativo {attempt + 1} completato con successo")
                return result, None
                
            except Exception as e:
                last_error = e
                
                if not self.should_retry(e):
                    logger.error(f"Errore non recuperabile al tentativo {attempt + 1}: {str(e)}")
                    raise RetryError(
                        f"Errore non recuperabile: {str(e)}",
                        last_error=e
                    )
                
                if attempt < self.max_retries - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Tentativo {attempt + 1} fallito con errore: {str(e)}. "
                        f"Nuovo tentativo tra {delay:.2f} secondi"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Tutti i tentativi falliti. Ultimo errore: {str(e)}"
                    )
                    
        raise RetryError(
            f"Esauriti tutti i {self.max_retries} tentativi",
            last_error=last_error
        )

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Decorator per applicare la politica di retry a una funzione.
    
    Args:
        max_retries: Numero massimo di tentativi
        initial_delay: Ritardo iniziale in secondi
        max_delay: Ritardo massimo in secondi
        backoff_factor: Fattore di incremento del ritardo
        jitter: Se True, aggiunge una componente casuale al ritardo
        
    Returns:
        Callable: Funzione decorata con politica di retry
    """
    retry_manager = RetryManager(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_factor=backoff_factor,
        jitter=jitter
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            result, error = retry_manager.execute_with_retry(func, *args, **kwargs)
            if error is not None:
                raise error
            return result
        return wrapper
    return decorator