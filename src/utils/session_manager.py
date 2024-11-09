# src/utils/session_manager.py

import streamlit as st
import pandas as pd
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from .checkpoint_manager import CheckpointManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class SessionManager:
    """
    Gestisce la persistenza dei dati di sessione in Streamlit.
    """
    
    _checkpoint_manager = CheckpointManager()
    
    @classmethod
    def initialize_session(cls):
        """Inizializza le variabili di sessione se non esistono."""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        if 'uploaded_file' not in st.session_state:
            st.session_state.uploaded_file = None
        if 'results_df' not in st.session_state:
            st.session_state.results_df = None
        if 'last_query' not in st.session_state:
            st.session_state.last_query = ""
        if 'processing_timestamp' not in st.session_state:
            st.session_state.processing_timestamp = None
        if 'processing_state' not in st.session_state:
            st.session_state.processing_state = None
        if 'current_page' not in st.session_state:
            st.session_state.current_page = 0

    @classmethod
    def save_file_to_temp(cls, uploaded_file) -> Path:
        """
        Salva il file caricato nella directory temporanea.
        
        Args:
            uploaded_file: File caricato attraverso Streamlit
            
        Returns:
            Path: Percorso del file salvato
        """
        temp_dir = Path("temp/uploads")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Genera nome file unico
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_path = temp_dir / f"{timestamp}_{uploaded_file.name}"
        
        # Salva il file
        temp_path.write_bytes(uploaded_file.getvalue())
        
        # Crea checkpoint iniziale
        cls._save_processing_checkpoint({
            'stage': 'upload',
            'file_path': str(temp_path),
            'original_file_name': uploaded_file.name,
            'file_size': uploaded_file.size
        })
        
        return temp_path

    @classmethod
    def save_results(cls, df: pd.DataFrame):
        """
        Salva i risultati nel session state e su disco.
        """
        try:
            st.session_state.results_df = df
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.processing_timestamp = timestamp
            
            # Salva su disco
            save_dir = Path("temp/results")
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Salva CSV e metadati
            results_path = save_dir / f"results_{timestamp}.csv"
            df.to_csv(results_path, index=False)
            
            # Ottieni il nome del file in modo corretto
            filename = (st.session_state.uploaded_file.name 
                    if hasattr(st.session_state.uploaded_file, 'name') 
                    else str(st.session_state.uploaded_file))
            
            # Prepara metadati
            metadata = {
                'timestamp': timestamp,
                'query': st.session_state.last_query,
                'file_name': filename,
                'rows_count': len(df),
                'columns': list(df.columns)
            }
            
            metadata_path = save_dir / f"metadata_{timestamp}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
                
            # Salva checkpoint finale con riferimenti ai file salvati
            cls._save_processing_checkpoint({
                'stage': 'complete',
                'timestamp': timestamp,
                'file_name': filename,
                'query': st.session_state.last_query,
                'results_path': str(results_path),
                'metadata_path': str(metadata_path),
                'rows_count': len(df)
            }, is_final=True)
            
            logger.info(f"Risultati salvati con successo. Timestamp: {timestamp}")
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio dei risultati: {e}")
            raise

    @classmethod
    def load_last_session(cls) -> bool:
        """
        Carica l'ultima sessione salvata.
        """
        try:
            # Prima cerca nella directory results
            results_dir = Path("temp/results")
            if not results_dir.exists():
                return False
                
            # Trova l'ultimo file di risultati basato sul timestamp
            result_files = sorted(
                results_dir.glob("results_*.csv"), 
                key=lambda x: x.stem.split('_')[1],
                reverse=True
            )
            
            if not result_files:
                return False
                
            latest_result = result_files[0]
            metadata_file = results_dir / f"metadata_{latest_result.stem.split('_')[1]}.json"
            
            if latest_result.exists() and metadata_file.exists():
                # Carica risultati
                st.session_state.results_df = pd.read_csv(latest_result)
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Ripristina stato
                st.session_state.last_query = metadata.get('query', '')
                st.session_state.processing_timestamp = metadata.get('timestamp')
                st.session_state.uploaded_file = metadata.get('file_name')
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Errore nel caricamento della sessione: {e}")
            return False
    
    @classmethod
    def load_specific_session(cls, timestamp: str) -> bool:
        """
        Carica una sessione specifica dal timestamp.
        """
        try:
            results_dir = Path("temp/results")
            results_file = results_dir / f"results_{timestamp}.csv"
            metadata_file = results_dir / f"metadata_{timestamp}.json"
            
            if results_file.exists() and metadata_file.exists():
                # Carica risultati
                st.session_state.results_df = pd.read_csv(results_file)
                
                # Carica metadata
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Aggiorna stato sessione
                st.session_state.last_query = metadata.get('query', '')
                st.session_state.processing_timestamp = metadata.get('timestamp')
                st.session_state.uploaded_file = metadata.get('file_name')
                
                logger.info(f"Sessione {timestamp} caricata con successo")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Errore nel caricamento della sessione {timestamp}: {e}")
            return False

    @classmethod
    def delete_session(cls, timestamp: str) -> bool:
        """
        Elimina una sessione specifica.
        """
        try:
            results_dir = Path("temp/results")
            results_file = results_dir / f"results_{timestamp}.csv"
            metadata_file = results_dir / f"metadata_{timestamp}.json"
            
            if results_file.exists():
                results_file.unlink()
            if metadata_file.exists():
                metadata_file.unlink()
                
            logger.info(f"Sessione {timestamp} eliminata con successo")
            return True
            
        except Exception as e:
            logger.error(f"Errore nell'eliminazione della sessione {timestamp}: {e}")
            return False

    @classmethod
    def update_processing_state(cls, state: Dict[str, Any], current_page: int):
        """
        Aggiorna lo stato di elaborazione corrente.
        
        Args:
            state: Nuovo stato di elaborazione
            current_page: Pagina corrente in elaborazione
        """
        st.session_state.processing_state = state
        st.session_state.current_page = current_page
        
        # Salva checkpoint
        cls._save_processing_checkpoint({
            'stage': 'processing',
            'state': state,
            'current_page': current_page
        })

    @classmethod
    def _save_processing_checkpoint(cls, state: Dict[str, Any], is_final: bool = False):
        """
        Salva un checkpoint dello stato di elaborazione.
        
        Args:
            state: Stato da salvare
            is_final: Se True, segna il checkpoint come finale
        """
        try:
            cls._checkpoint_manager.save_checkpoint(
                st.session_state.session_id,
                state,
                is_final
            )
        except Exception as e:
            logger.error(f"Errore nel salvataggio del checkpoint: {e}")

    @classmethod
    def list_available_sessions(cls):
        """
        Lista tutte le sessioni disponibili.
        """
        sessions = []
        results_dir = Path("temp/results")
        
        if not results_dir.exists():
            return sessions
            
        for metadata_file in results_dir.glob("metadata_*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                sessions.append({
                    'timestamp': metadata.get('timestamp'),
                    'file_name': metadata.get('file_name'),
                    'query': metadata.get('query'),
                    'rows_count': metadata.get('rows_count')
                })
            except Exception as e:
                logger.error(f"Errore nel caricamento della sessione {metadata_file}: {e}")
                
        return sorted(sessions, key=lambda x: x['timestamp'], reverse=True)

    @classmethod
    def cleanup_old_sessions(cls, days: int = 7):
        """
        Pulisce le sessioni più vecchie di X giorni.
        
        Args:
            days: Elimina sessioni più vecchie di questi giorni
        """
        try:
            cls._checkpoint_manager.cleanup_old_sessions(days)
            
            # Pulizia directory temporanee
            temp_dirs = [Path("temp/uploads"), Path("temp/results")]
            current_time = datetime.now().timestamp()
            
            for temp_dir in temp_dirs:
                if not temp_dir.exists():
                    continue
                    
                for file in temp_dir.glob("*"):
                    if (current_time - file.stat().st_mtime) > (days * 24 * 3600):
                        if file.is_file():
                            file.unlink()
                        elif file.is_dir():
                            shutil.rmtree(file)
                            
        except Exception as e:
            logger.error(f"Errore nella pulizia delle sessioni: {e}")

    @classmethod
    def can_resume_processing(cls) -> bool:
        """
        Verifica se è possibile riprendere un'elaborazione interrotta.
        
        Returns:
            bool: True se c'è un'elaborazione da riprendere
        """
        return (st.session_state.processing_state is not None and 
                st.session_state.processing_state.get('stage') == 'processing')