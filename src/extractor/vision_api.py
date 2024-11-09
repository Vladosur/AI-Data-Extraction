from pathlib import Path
from typing import List, Dict, Optional
import base64
from openai import OpenAI
from src.config.settings import VISION_SETTINGS
from src.utils.logger import setup_logger
import json
import re

logger = setup_logger(__name__)

class VisionAPI:
    """
    Classe per l'interazione con OpenAI Vision API.
    """
    
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

    def extract_data(self, image_path: Path, query: Optional[str] = None) -> List[Dict]:
        """
        Estrae dati da un'immagine usando Vision API.
        
        Args:
            image_path: Percorso dell'immagine da analizzare
            query: Query specifica per l'estrazione (opzionale)
            
        Returns:
            Lista di dizionari contenenti i dati estratti
        """
        logger.info(f"Inizio estrazione dati da: {image_path}")
        
        try:
            # Codifica l'immagine in base64
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepara il prompt in base alla query
            prompt = VISION_SETTINGS['PROMPT_TEMPLATE']
            if query:
                prompt += f"\n\nRichiesta specifica: {query}"
            
            # Prepara il messaggio per l'API nel formato corretto
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
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Chiamata API
            response = self.client.chat.completions.create(
                model=VISION_SETTINGS['MODEL'],
                messages=messages,
                max_tokens=VISION_SETTINGS['MAX_TOKENS'],
                temperature=VISION_SETTINGS['TEMPERATURE']
            )
            
            # Processa la risposta
            processed_response = self._process_response(response)
            
            # Salva la risposta processata in formato JSON
            output_dir = Path("output/json")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{image_path.stem}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(processed_response, f, ensure_ascii=False, indent=4)
            
            logger.debug(f"Risposta API salvata in: {output_file}")
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Errore nell'estrazione dei dati: {str(e)}")
            raise

    def _process_response(self, response) -> List[Dict]:
        """
        Processa la risposta dell'API e la converte in formato strutturato.
        """
        try:
            content = response.choices[0].message.content.strip()
            logger.debug(f"Risposta API ricevuta: {content[:200]}...")
            
            try:
                # Rimuovi i delimitatori markdown del codice JSON se presenti
                content = re.sub(r'^```json\s*|\s*```$', '', content.strip())
                
                # Se la risposta è vuota o non valida, ritorna lista vuota
                if not content or content.isspace():
                    return []
                
                data = json.loads(content)
                
                # Standardizza il formato
                if isinstance(data, dict):
                    return [data]
                elif isinstance(data, list):
                    return data
                else:
                    logger.warning(f"Formato risposta non valido: {type(data)}")
                    return []
                    
            except json.JSONDecodeError as e:
                logger.error(f"Errore nel parsing della risposta JSON: {str(e)}")
                logger.debug(f"Contenuto problematico: {content}")
                return []
            
        except Exception as e:
            logger.error(f"Errore nel processing della risposta: {str(e)}")
            return []