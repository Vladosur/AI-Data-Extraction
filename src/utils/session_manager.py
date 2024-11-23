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
        if 'processing_timestamp' not in st.session_state:
            st.session_state.processing_timestamp = None
        if 'processing_state' not in st.session_state:
            st.session_state.processing_state = None
        if 'session_metadata' not in st.session_state:
            st.session_state.session_metadata = {}
        if 'export_history' not in st.session_state:
            st.session_state.export_history = []
        if 'is_new_session' not in st.session_state:
            st.session_state.is_new_session = True

    @classmethod
    def update_session_metadata(cls, metadata_update: Dict[str, Any]):
        """
        Aggiorna i metadati della sessione.
        
        Args:
            metadata_update: Dizionario con i nuovi metadati da aggiungere/aggiornare
        """
        try:
            if 'session_metadata' not in st.session_state:
                st.session_state.session_metadata = {}
                
            st.session_state.session_metadata.update(metadata_update)
            
            # Aggiorna anche il timestamp di processing se presente nei metadati
            if 'timestamp' in metadata_update:
                st.session_state.processing_timestamp = metadata_update['timestamp']
                
            # Salva checkpoint con i metadati aggiornati
            cls._save_processing_checkpoint({
                'stage': 'metadata_update',
                'metadata': st.session_state.session_metadata,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.debug(f"Metadati sessione aggiornati: {metadata_update}")
            
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento dei metadati: {e}")
            raise
        
    @classmethod
    def add_export_record(cls, export_info: Dict[str, Any]):
        """
        Aggiunge un record di esportazione alla cronologia.
        
        Args:
            export_info: Informazioni sull'esportazione (formato, nome file, timestamp, etc.)
        """
        try:
            if 'export_history' not in st.session_state:
                st.session_state.export_history = []
                
            st.session_state.export_history.append(export_info)
            
            # Aggiorna i metadati della sessione
            metadata_update = {
                'last_export': export_info,
                'export_count': len(st.session_state.export_history),
                'timestamp': export_info['timestamp']
            }
            
            cls.update_session_metadata(metadata_update)
            
            # Salva lo stato aggiornato
            cls._save_processing_checkpoint({
                'stage': 'export',
                'export_info': export_info,
                'metadata': st.session_state.session_metadata
            })
            
            logger.info(f"Record esportazione aggiunto: {export_info}")
            
        except Exception as e:
            logger.error(f"Errore nell'aggiunta del record di esportazione: {e}")
            raise
        
    @classmethod
    def get_session_info(cls) -> Dict[str, Any]:
        """
        Recupera le informazioni complete della sessione corrente.
        
        Returns:
            Dict[str, Any]: Informazioni della sessione
        """
        try:
            return {
                'session_id': st.session_state.get('session_id'),
                'file_name': st.session_state.get('uploaded_file'),
                'processing_timestamp': st.session_state.get('processing_timestamp'),
                'metadata': st.session_state.get('session_metadata', {}),
                'export_history': st.session_state.get('export_history', []),
                'has_results': st.session_state.get('results_df') is not None,
                'rows_count': len(st.session_state.results_df) if st.session_state.get('results_df') is not None else 0
            }
        except Exception as e:
            logger.error(f"Errore nel recupero delle informazioni della sessione: {e}")
            return {}
        
    @classmethod
    def save_file_to_temp(cls, uploaded_file) -> Path:
        """
        Salva il file caricato nella directory temporanea.
        """
        try:
            temp_dir = Path("temp/uploads")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Genera nome file unico
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_path = temp_dir / f"{timestamp}_{uploaded_file.name}"
            
            # Salva il file
            temp_path.write_bytes(uploaded_file.getvalue())
            
            # Crea checkpoint iniziale con metadati estesi
            initial_metadata = {
                'stage': 'upload',
                'file_path': str(temp_path),
                'original_file_name': uploaded_file.name,
                'file_size': uploaded_file.size,
                'timestamp': timestamp,
                'upload_time': datetime.now().isoformat()
            }
            
            # Aggiorna i metadati della sessione
            cls.update_session_metadata(initial_metadata)
            
            # Salva checkpoint
            cls._save_processing_checkpoint(initial_metadata)
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio del file: {e}")
            raise

    @classmethod
    def save_results(cls, df: pd.DataFrame):
        """
        Salva i risultati nel session state e su disco.
        
        Args:
            df: DataFrame con i risultati
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
                'file_name': filename,
                'rows_count': len(df),
                'columns': list(df.columns),
                'last_operation': 'save_results',
                'has_exports': bool(st.session_state.get('export_history', []))
            }
            
            # Aggiorna i metadati della sessione
            cls.update_session_metadata(metadata)
            
            metadata_path = save_dir / f"metadata_{timestamp}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
                
            # Salva checkpoint finale
            cls._save_processing_checkpoint({
                'stage': 'complete',
                'timestamp': timestamp,
                'metadata': metadata,
                'results_path': str(results_path),
                'metadata_path': str(metadata_path)
            }, is_final=True)
            
            logger.info(f"Risultati salvati con successo. Timestamp: {timestamp}")
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio dei risultati: {e}")
            raise

    @classmethod
    def load_last_session(cls) -> bool:
        """Carica l'ultima sessione salvata."""
        try:
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
            timestamp = latest_result.stem.split('_')[1]
            
            return cls.load_specific_session(timestamp)
                
        except Exception as e:
            logger.error(f"Errore nel caricamento dell'ultima sessione: {e}")
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
                
                # Aggiorna stato sessione con tutti i metadati
                st.session_state.processing_timestamp = metadata.get('timestamp')
                st.session_state.uploaded_file = metadata.get('file_name')
                st.session_state.session_metadata = metadata
                st.session_state.export_history = metadata.get('export_history', [])
                
                # Aggiorna il processing state se presente
                if 'processing_state' in metadata:
                    st.session_state.processing_state = metadata['processing_state']
                
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
            files_to_delete = [
                results_dir / f"results_{timestamp}.csv",
                results_dir / f"metadata_{timestamp}.json"
            ]
            
            # Cerca anche eventuali file temporanei associati
            temp_dir = Path("temp/current")
            if temp_dir.exists():
                temp_pattern = f"*_{timestamp}_*"
                files_to_delete.extend(temp_dir.glob(temp_pattern))
            
            deleted = False
            for file in files_to_delete:
                if file.exists():
                    file.unlink()
                    deleted = True
                    
            if deleted:
                logger.info(f"Sessione {timestamp} eliminata con successo")
                
                # Se la sessione corrente è quella eliminata, pulisci lo stato
                if st.session_state.get('processing_timestamp') == timestamp:
                    cls._clear_current_session()
                    
            return deleted
                
        except Exception as e:
            logger.error(f"Errore nell'eliminazione della sessione {timestamp}: {e}")
            return False
    
    @classmethod
    def _clear_current_session(cls):
        """Pulisce lo stato della sessione corrente."""
        try:
            # Pulisci tutti i campi della sessione
            st.session_state.results_df = None
            st.session_state.uploaded_file = None
            st.session_state.processing_timestamp = None
            st.session_state.processing_state = None
            st.session_state.session_metadata = {}
            st.session_state.export_history = []
            # Mantieni session_id ma marca come nuova sessione
            st.session_state.is_new_session = True
            
            logger.info("Sessione corrente pulita")
        except Exception as e:
            logger.error(f"Errore durante la pulizia della sessione: {e}")
            raise

    @classmethod
    def update_processing_state(cls, state: Dict[str, Any], current_page: int):
        """
        Aggiorna lo stato di elaborazione corrente.
        """
        try:
            st.session_state.processing_state = state
            st.session_state.current_page = current_page
            
            # Aggiorna i metadati con lo stato di processing
            metadata_update = {
                'processing_state': state,
                'current_page': current_page,
                'last_update': datetime.now().isoformat()
            }
            cls.update_session_metadata(metadata_update)
            
            # Salva checkpoint
            cls._save_processing_checkpoint({
                'stage': 'processing',
                'state': state,
                'current_page': current_page,
                'metadata': st.session_state.session_metadata
            })
            
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento dello stato di processing: {e}")
            raise

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
        """Lista tutte le sessioni disponibili."""
        sessions = []
        results_dir = Path("temp/results")
        
        if not results_dir.exists():
            return sessions
                
        for metadata_file in results_dir.glob("metadata_*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    
                # Aggiungi informazioni estese
                session_info = {
                    'timestamp': metadata.get('timestamp'),
                    'file_name': metadata.get('file_name'),
                    'rows_count': metadata.get('rows_count', 0),
                    'has_exports': metadata.get('has_exports', False),
                    'export_count': len(metadata.get('export_history', [])),
                    'last_operation': metadata.get('last_operation'),
                    'last_export': metadata.get('last_export')
                }
                sessions.append(session_info)
                    
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
        """
        return (st.session_state.processing_state is not None and 
                st.session_state.processing_state.get('stage') == 'processing' and
                st.session_state.session_metadata.get('last_operation') != 'complete')