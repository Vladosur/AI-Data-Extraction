# src/utils/json_validator.py

from typing import Dict, Optional, Tuple, Any
from jsonschema import validate, ValidationError, Draft7Validator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class JSONValidationError(Exception):
    """Eccezione sollevata per errori di validazione JSON."""
    pass

class JSONValidator:
    """Classe per la validazione dei dati JSON secondo lo schema definito."""
    
    # Schema per i dati dei prodotti
    PRODUCT_SCHEMA = {
        "type": "object",
        "properties": {
            "prodotti": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "codice": {"type": "string"},
                        "descrizione": {"type": "string"},
                        "tipo_prezzo": {"enum": ["singolo", "quantita"]},
                        "prezzo_unitario": {
                            "type": ["number", "null"],
                            "minimum": 0
                        },
                        "prezzi_quantita": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "quantita": {
                                        "type": "integer",
                                        "minimum": 1
                                    },
                                    "prezzo": {
                                        "type": "number",
                                        "minimum": 0
                                    },
                                    "quantita_minima": {"type": "boolean"},
                                    "non_vendibile_separatamente": {"type": "boolean"}
                                },
                                "required": ["quantita", "prezzo"],
                                "additionalProperties": False
                            }
                        },
                        "descrizione_quantita": {"type": "string"}
                    },
                    "required": ["codice", "descrizione", "tipo_prezzo"],
                    "additionalProperties": False,
                    "allOf": [
                        {
                            "if": {
                                "properties": {"tipo_prezzo": {"const": "singolo"}},
                                "required": ["tipo_prezzo"]
                            },
                            "then": {
                                "required": ["prezzo_unitario"],
                                "not": {"required": ["prezzi_quantita"]}
                            }
                        },
                        {
                            "if": {
                                "properties": {"tipo_prezzo": {"const": "quantita"}},
                                "required": ["tipo_prezzo"]
                            },
                            "then": {
                                "required": ["prezzi_quantita"],
                                "not": {"required": ["prezzo_unitario"]}
                            }
                        }
                    ]
                }
            }
        },
        "required": ["prodotti"],
        "additionalProperties": False
    }

    @classmethod
    def validate_product_data(cls, data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Valida i dati dei prodotti secondo lo schema definito.
        
        Args:
            data: Dizionario contenente i dati da validare
            
        Returns:
            Tuple[bool, Optional[str]]: (validazione_ok, messaggio_errore)
        """
        try:
            validate(instance=data, schema=cls.PRODUCT_SCHEMA)
            return True, None
        except ValidationError as e:
            error_path = " -> ".join(str(p) for p in e.path)
            error_message = f"Errore di validazione in {error_path}: {e.message}"
            logger.error(error_message)
            return False, error_message

    @classmethod
    def get_validation_errors(cls, data: Dict) -> list:
        """
        Ottiene tutti gli errori di validazione presenti nei dati.
        
        Args:
            data: Dizionario contenente i dati da validare
            
        Returns:
            list: Lista degli errori di validazione
        """
        validator = Draft7Validator(cls.PRODUCT_SCHEMA)
        errors = []
        for error in validator.iter_errors(data):
            error_path = " -> ".join(str(p) for p in error.path)
            errors.append(f"{error_path}: {error.message}")
        return errors

    @classmethod
    def sanitize_product_data(cls, data: Dict) -> Dict:
        """
        Sanitizza i dati dei prodotti rimuovendo campi non validi.
        
        Args:
            data: Dizionario contenente i dati da sanitizzare
            
        Returns:
            Dict: Dati sanitizzati
        """
        if not isinstance(data, dict) or "prodotti" not in data:
            return {"prodotti": []}
            
        sanitized_data = {"prodotti": []}
        
        for prodotto in data.get("prodotti", []):
            if not isinstance(prodotto, dict):
                continue
                
            sanitized_product = {
                "codice": str(prodotto.get("codice", "")),
                "descrizione": str(prodotto.get("descrizione", "")),
                "tipo_prezzo": prodotto.get("tipo_prezzo", "singolo")
            }
            
            if sanitized_product["tipo_prezzo"] == "singolo":
                prezzo = prodotto.get("prezzo_unitario")
                if isinstance(prezzo, (int, float)) and prezzo >= 0:
                    sanitized_product["prezzo_unitario"] = float(prezzo)
                else:
                    sanitized_product["prezzo_unitario"] = None
                    
            elif sanitized_product["tipo_prezzo"] == "quantita":
                prezzi_quantita = []
                for prezzo in prodotto.get("prezzi_quantita", []):
                    if isinstance(prezzo, dict):
                        quantita = prezzo.get("quantita")
                        prezzo_val = prezzo.get("prezzo")
                        
                        if isinstance(quantita, int) and quantita > 0 and \
                           isinstance(prezzo_val, (int, float)) and prezzo_val >= 0:
                            prezzi_quantita.append({
                                "quantita": quantita,
                                "prezzo": float(prezzo_val),
                                "quantita_minima": bool(prezzo.get("quantita_minima", False)),
                                "non_vendibile_separatamente": bool(prezzo.get("non_vendibile_separatamente", False))
                            })
                            
                sanitized_product["prezzi_quantita"] = prezzi_quantita
                if "descrizione_quantita" in prodotto:
                    sanitized_product["descrizione_quantita"] = str(prodotto["descrizione_quantita"])
                    
            sanitized_data["prodotti"].append(sanitized_product)
            
        return sanitized_data
        
    @classmethod
    def validate_and_sanitize(cls, data: Dict) -> Tuple[Dict, list]:
        """
        Valida e sanitizza i dati dei prodotti.
        
        Args:
            data: Dizionario contenente i dati da processare
            
        Returns:
            Tuple[Dict, list]: (dati_sanitizzati, lista_errori)
        """
        # Prima sanitizza
        sanitized_data = cls.sanitize_product_data(data)
        
        # Poi valida
        errors = cls.get_validation_errors(sanitized_data)
        
        return sanitized_data, errors