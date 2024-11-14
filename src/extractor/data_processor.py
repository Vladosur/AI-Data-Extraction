"""
Modulo per l'elaborazione dei dati estratti e la generazione di CSV.
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict
from src.utils.logger import setup_logger
from src.config.settings import VISION_SETTINGS
from src.utils.json_validator import JSONValidator, JSONValidationError

logger = setup_logger(__name__)

class DataProcessorError(Exception):
    """Eccezione base per errori del DataProcessor."""
    pass

class DataProcessor:
    """
    Classe per l'elaborazione dei dati estratti dalle immagini e la generazione di file CSV.
    """
    
    def __init__(self):
        """Inizializza il processore dati."""
        logger.debug("Inizializzazione DataProcessor")
    
    def _validate_input_data(self, data: List[Dict]) -> List[Dict]:
        """
        Valida e sanitizza i dati di input.
        
        Args:
            data: Lista di dizionari con i dati dei prodotti
            
        Returns:
            List[Dict]: Dati validati e sanitizzati
            
        Raises:
            DataProcessorError: Se i dati non sono validi e non possono essere corretti
        """
        try:
            # Prepara i dati nel formato atteso dal validatore
            input_data = {"prodotti": data}
            
            # Valida e sanitizza
            sanitized_data, validation_errors = JSONValidator.validate_and_sanitize(input_data)
            
            if validation_errors:
                # Log degli errori di validazione
                for error in validation_errors:
                    logger.warning(f"Errore di validazione: {error}")
                    
            return sanitized_data.get("prodotti", [])
            
        except Exception as e:
            logger.error(f"Errore nella validazione dei dati: {str(e)}")
            raise DataProcessorError(f"Errore nella validazione dei dati: {str(e)}")
            
    def process_data(self, data: List[Dict]) -> pd.DataFrame:
        """
        Elabora i dati JSON in DataFrame con gestione dei due tipi di prezzo.
        
        Args:
            data: Lista di dizionari con i dati dei prodotti
            
        Returns:
            pd.DataFrame: DataFrame con i dati elaborati
            
        Raises:
            DataProcessorError: Se si verificano errori durante l'elaborazione
        """
        try:
            # Valida e sanitizza i dati di input
            validated_data = self._validate_input_data(data)
            
            if not validated_data:
                logger.warning("Nessun dato valido da processare")
                return pd.DataFrame()
            
            # Struttura base DataFrame
            base_columns = ['codice', 'descrizione', 'tipo_prezzo']
            df_data = []
            qty_columns = set()
            
            # Prima passata: raccogli tutte le possibili quantità
            for prodotto in validated_data:
                if prodotto.get('tipo_prezzo') == 'quantita':
                    prezzi_quantita = prodotto.get('prezzi_quantita', [])
                    for prezzo in prezzi_quantita:
                        qty = prezzo.get('quantita')
                        if qty is not None:
                            qty_columns.add(f"PER Pz. {qty}")
            
            # Crea lista ordinata delle colonne per quantità
            qty_columns = sorted(list(qty_columns), 
                               key=lambda x: int(x.split()[2]))
            
            # Colonne finali del DataFrame
            final_columns = (base_columns + 
                           ['prezzo_unitario', 'descrizione_quantita', 'non_vendibile_separatamente'] + 
                           list(qty_columns))
            
            # Seconda passata: popolamento dati
            for prodotto in validated_data:
                row = {
                    'codice': prodotto.get('codice', ''),
                    'descrizione': prodotto.get('descrizione', ''),
                    'tipo_prezzo': prodotto.get('tipo_prezzo', ''),
                    'prezzo_unitario': None,
                    'descrizione_quantita': '',
                    'non_vendibile_separatamente': False
                }
                
                # Inizializza tutte le colonne quantità a None
                for col in qty_columns:
                    row[col] = None
                
                if prodotto['tipo_prezzo'] == 'singolo':
                    row['prezzo_unitario'] = float(prodotto.get('prezzo_unitario', 0))
                
                elif prodotto['tipo_prezzo'] == 'quantita':
                    prezzi_quantita = prodotto.get('prezzi_quantita', [])
                    row['descrizione_quantita'] = prodotto.get('descrizione_quantita', '')
                    
                    # Cerca se c'è almeno un prezzo non vendibile separatamente
                    row['non_vendibile_separatamente'] = any(
                        p.get('non_vendibile_separatamente', False) 
                        for p in prezzi_quantita
                    )
                    
                    # Popola i prezzi per quantità
                    for prezzo in prezzi_quantita:
                        qty = prezzo.get('quantita')
                        if qty is not None:
                            col_name = f"PER Pz. {qty}"
                            row[col_name] = float(prezzo.get('prezzo', 0))
                
                df_data.append(row)
            
            # Crea il DataFrame
            df = pd.DataFrame(df_data, columns=final_columns)
            
            # Conversione tipi
            numeric_columns = ['prezzo_unitario'] + list(qty_columns)
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Conversione booleani
            df['non_vendibile_separatamente'] = df['non_vendibile_separatamente'].astype(bool)
            
            return df
            
        except Exception as e:
            logger.error(f"Errore nell'elaborazione dei dati: {str(e)}")
            raise DataProcessorError(f"Errore nell'elaborazione dei dati: {str(e)}")
            
    def save_csv(self, df: pd.DataFrame, output_path: Path) -> None:
        """
        Salva il DataFrame in formato CSV.
        
        Args:
            df: DataFrame da salvare
            output_path: Percorso del file di output
        """
        try:
            # Assicurati che la directory di output esista
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salva il CSV
            df.to_csv(output_path, index=False)
            logger.info(f"File CSV salvato in: {output_path}")
            
        except Exception as e:
            logger.error(f"Errore durante il salvataggio del CSV: {str(e)}")
            raise
            