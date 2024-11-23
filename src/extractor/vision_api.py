# src/extractor/vision_api.py

import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import base64
from openai import OpenAI
import openai
from PIL import Image
import io
from src.config.settings import IMAGE_SETTINGS
from src.config.settings import VISION_SETTINGS
from src.utils.logger import setup_logger
from src.utils.retry_manager import with_retry, RetryError
import json
import re

# Importazione diretta delle classi di errore da openai
from openai import (
    APIError,
    APIConnectionError,
    RateLimitError
)

logger = setup_logger(__name__)

class VisionAPIError(Exception):
    """Eccezione base per errori della Vision API."""
    pass

class JSONValidator:
    """
    Validatore JSON temporaneo finché non importiamo il modulo completo.
    Questo evita errori di import circolari.
    """
    @staticmethod
    def validate_and_sanitize(data: Dict) -> Tuple[Dict, list]:
        # Implementazione base per ora
        return data, []
    
class VisionAPI:
    """Classe per l'interazione con OpenAI Vision API."""
    
    def __init__(self, api_key: str):
        """
        Inizializza il client OpenAI Vision.
        
        Args:
            api_key: Chiave API OpenAI
        """
        if not api_key:
            logger.error("API key non fornita")
            raise ValueError("È necessario fornire una API key valida")
            
        self.client = OpenAI(api_key=api_key)
        logger.debug("Client OpenAI Vision inizializzato")

    @with_retry(
        max_retries=3,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_factor=2.0,
        jitter=True
    )
    def _make_api_call(self, messages: List[Dict]) -> Dict:
        """
        Esegue la chiamata API con gestione retry.
        
        Args:
            messages: Lista di messaggi per l'API
            
        Returns:
            Dict: Risposta dell'API
            
        Raises:
            VisionAPIError: In caso di errori non recuperabili
        """
        try:
            response = self.client.chat.completions.create(
                model=VISION_SETTINGS['MODEL'],
                messages=messages,
                max_tokens=VISION_SETTINGS['MAX_TOKENS'],
                temperature=VISION_SETTINGS['TEMPERATURE']
            )
            return response
            
        except Exception as e:
            logger.error(f"Errore nella chiamata API: {str(e)}")
            raise VisionAPIError(f"Errore nella chiamata API: {str(e)}") from e

    def extract_data(self, image: Image.Image) -> List[Dict]:
        """
        Estrae dati da un'immagine usando Vision API.
        
        Args:
            image: Immagine PIL da analizzare
            
        Returns:
            Lista di dizionari contenenti i dati estratti
            
        Raises:
            VisionAPIError: In caso di errori nell'estrazione dei dati
        """
        logger.info("Inizio estrazione dati da immagine")
        
        try:
            base64_image = self._convert_to_base64(image)
            
            # Usa il prompt template senza aggiungere query
            prompt = VISION_SETTINGS['PROMPT_TEMPLATE']
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            },
                        },
                    ],
                },
            ]
            
            response = self._make_api_call(messages)
            processed_response = self._process_response(response)
            self._save_response(processed_response)
            
            return processed_response
            
        except RetryError as e:
            logger.error(f"Errore dopo tutti i tentativi di retry: {str(e)}")
            raise VisionAPIError(f"Errore nell'estrazione dei dati dopo multipli tentativi: {str(e)}") from e
        except Exception as e:
            logger.error(f"Errore nell'estrazione dei dati: {str(e)}")
            raise VisionAPIError(f"Errore nell'estrazione dei dati: {str(e)}") from e

    def _convert_to_base64(self, image: Image.Image) -> str:
        """
        Converte un'immagine PIL in stringa base64.
        
        Args:
            image: Immagine PIL da convertire
            
        Returns:
            str: Immagine codificata in base64
        """
        try:
            buffer = io.BytesIO()
            image.save(
                buffer, 
                format=IMAGE_SETTINGS['FORMAT'],
                quality=IMAGE_SETTINGS['QUALITY'],
                optimize=True
            )
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return base64_image
            
        except Exception as e:
            logger.error(f"Errore nella conversione in base64: {e}")
            raise VisionAPIError(f"Errore nella conversione dell'immagine in base64: {str(e)}")
        finally:
            if 'buffer' in locals():
                buffer.close()
    
    def _process_response(self, response) -> List[Dict]:
        """
        Processa la risposta dell'API e la converte in formato strutturato.
        """
        try:
            content = response.choices[0].message.content.strip()
            logger.debug(f"Risposta API ricevuta: {content[:200]}...")
            
            # Rimuovi i delimitatori markdown del codice JSON se presenti
            content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
            
            # Se la risposta è vuota o non valida, ritorna lista vuota
            if not content or content.isspace():
                return []
            
            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Errore nel parsing della risposta JSON: {str(e)}")
                logger.debug(f"Contenuto problematico: {content}")
                return []
            
            # Sanitizza e valida i dati
            sanitized_data, validation_errors = JSONValidator.validate_and_sanitize(data)
            
            if validation_errors:
                # Log degli errori ma continua con i dati sanitizzati
                for error in validation_errors:
                    logger.warning(f"Errore di validazione: {error}")
                    
            if "prodotti" in sanitized_data:
                return sanitized_data["prodotti"]
            else:
                logger.warning("Dati sanitizzati non contengono prodotti")
                return []
                
        except Exception as e:
            logger.error(f"Errore nel processing della risposta: {str(e)}")
            return []

    def _save_response(self, response: List[Dict]) -> None:
        """
        Salva la risposta processata in formato JSON.
        
        Args:
            response: Risposta processata da salvare
        """
        try:
            output_dir = Path("output/json")
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"response_{timestamp}.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(response, f, ensure_ascii=False, indent=4)
                
            logger.debug(f"Risposta API salvata in: {output_file}")
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio della risposta: {str(e)}")