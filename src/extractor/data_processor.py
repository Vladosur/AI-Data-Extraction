"""
Modulo per l'elaborazione dei dati estratti e la generazione di CSV.
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict
from src.utils.logger import setup_logger
from src.config.settings import VISION_SETTINGS

logger = setup_logger(__name__)

class DataProcessor:
    """
    Classe per l'elaborazione dei dati estratti dalle immagini e la generazione di file CSV.
    """
    
    def __init__(self):
        """Inizializza il processore dati."""
        logger.debug("Inizializzazione DataProcessor")
        
    def process_data(self, data: List[Dict]) -> pd.DataFrame:
        """
        Elabora i dati JSON in DataFrame con gestione dei due tipi di prezzo.
        """
        try:
            # Struttura base DataFrame
            base_columns = ['codice', 'descrizione', 'tipo_prezzo']
            df_data = []
            qty_columns = set()  # Raccoglitore per tutte le possibili quantità
            
            # Prima passata: raccogli tutte le possibili quantità
            for record in data:
                if 'prodotti' in record:
                    products = record['prodotti']
                elif isinstance(record, list):
                    products = record
                else:
                    products = [record]
                    
                for prodotto in products:
                    if prodotto.get('tipo_prezzo') == 'quantita':
                        prezzi_quantita = prodotto.get('prezzi_quantita', [])
                        for prezzo in prezzi_quantita:
                            if isinstance(prezzo, dict):
                                qty = prezzo.get('quantita')
                                if qty is not None:
                                    qty_columns.add(f"PER Pz. {qty}")
            
            # Crea lista ordinata delle colonne per quantità
            qty_columns = sorted(list(qty_columns), 
                               key=lambda x: int(x.split()[2]))  # Ordina per il numero dopo "PER Pz."
            
            # Colonne finali del DataFrame
            final_columns = (base_columns + 
                           ['prezzo_unitario', 'descrizione_quantita', 'non_vendibile_separatamente'] + 
                           qty_columns)
            
            # Seconda passata: popolamento dati
            for record in data:
                if 'prodotti' in record:
                    products = record['prodotti']
                elif isinstance(record, list):
                    products = record
                else:
                    products = [record]
                
                for prodotto in products:
                    # Dati base del prodotto
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
                    
                    # Gestione in base al tipo di prezzo
                    if prodotto['tipo_prezzo'] == 'singolo':
                        row['prezzo_unitario'] = float(prodotto.get('prezzo_unitario', 0))
                    
                    elif prodotto['tipo_prezzo'] == 'quantita':
                        prezzi_quantita = prodotto.get('prezzi_quantita', [])
                        row['descrizione_quantita'] = prodotto.get('descrizione_quantita', '')
                        
                        # Cerca se c'è almeno un prezzo non vendibile separatamente
                        non_vendibile = any(p.get('non_vendibile_separatamente', False) 
                                          for p in prezzi_quantita)
                        row['non_vendibile_separatamente'] = non_vendibile
                        
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
            numeric_columns = ['prezzo_unitario'] + qty_columns
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Conversione booleani
            df['non_vendibile_separatamente'] = df['non_vendibile_separatamente'].astype(bool)
            
            return df
            
        except Exception as e:
            logger.error(f"Errore nell'elaborazione dei dati: {str(e)}")
            raise
            
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
            