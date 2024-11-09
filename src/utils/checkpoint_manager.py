# src/utils/checkpoint_manager.py

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class CheckpointManager:
    """
    Gestisce il salvataggio e il ripristino dello stato di elaborazione.
    """
    
    def __init__(self, base_dir: Path = Path("temp/checkpoints")):
        """
        Inizializza il gestore dei checkpoint.
        
        Args:
            base_dir: Directory base per i checkpoint
        """
        self.base_dir = base_dir
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Crea le directory necessarie se non esistono."""
        (self.base_dir / "current").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "history").mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, session_id: str, state: Dict[str, Any], is_final: bool = False) -> bool:
        """
        Salva un checkpoint dello stato corrente.
        
        Args:
            session_id: Identificatore univoco della sessione
            state: Stato da salvare
            is_final: Se True, sposta il checkpoint nella cronologia
            
        Returns:
            bool: True se il salvataggio è avvenuto con successo
        """
        try:
            # Aggiungi timestamp e metadati
            checkpoint_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id,
                "state": state
            }
            
            # Determina il percorso di salvataggio
            target_dir = self.base_dir / ("history" if is_final else "current")
            checkpoint_file = target_dir / f"checkpoint_{session_id}.json"
            
            # Salva il checkpoint
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # Se è un checkpoint finale, copia anche i file associati
            if is_final and "file_paths" in state:
                self._archive_files(session_id, state["file_paths"])
            
            logger.info(f"Checkpoint salvato: {checkpoint_file}")
            return True
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio del checkpoint: {e}")
            return False
    
    def load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Carica l'ultimo checkpoint disponibile per una sessione.
        
        Args:
            session_id: Identificatore della sessione
            
        Returns:
            Optional[Dict]: Stato del checkpoint o None se non trovato
        """
        try:
            # Cerca prima nei checkpoint correnti
            checkpoint_file = self.base_dir / "current" / f"checkpoint_{session_id}.json"
            if not checkpoint_file.exists():
                # Cerca nella cronologia
                checkpoint_file = self.base_dir / "history" / f"checkpoint_{session_id}.json"
                if not checkpoint_file.exists():
                    return None
            
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            logger.info(f"Checkpoint caricato: {checkpoint_file}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Errore nel caricamento del checkpoint: {e}")
            return None
    
    def _archive_files(self, session_id: str, file_paths: list):
        """
        Archivia i file associati a una sessione.
        
        Args:
            session_id: Identificatore della sessione
            file_paths: Lista dei percorsi dei file da archiviare
        """
        try:
            archive_dir = self.base_dir / "history" / session_id / "files"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in file_paths:
                if isinstance(file_path, (str, Path)):
                    path = Path(file_path)
                    if path.exists():
                        shutil.copy2(path, archive_dir / path.name)
                        
        except Exception as e:
            logger.error(f"Errore nell'archiviazione dei file: {e}")
    
    def list_sessions(self, include_current: bool = True, include_history: bool = True) -> list:
        """
        Lista tutte le sessioni disponibili.
        
        Args:
            include_current: Includi sessioni correnti
            include_history: Includi sessioni dalla cronologia
            
        Returns:
            list: Lista delle sessioni trovate
        """
        sessions = []
        
        try:
            if include_current:
                current_files = list((self.base_dir / "current").glob("checkpoint_*.json"))
                sessions.extend([self._load_session_info(f) for f in current_files])
                
            if include_history:
                history_files = list((self.base_dir / "history").glob("checkpoint_*.json"))
                sessions.extend([self._load_session_info(f) for f in history_files])
                
            # Ordina per timestamp decrescente
            sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return sessions
            
        except Exception as e:
            logger.error(f"Errore nel listing delle sessioni: {e}")
            return []
    
    def _load_session_info(self, checkpoint_file: Path) -> dict:
        """
        Carica le informazioni base di una sessione.
        
        Args:
            checkpoint_file: Percorso del file di checkpoint
            
        Returns:
            dict: Informazioni della sessione
        """
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {
                    "session_id": data.get("session_id"),
                    "timestamp": data.get("timestamp"),
                    "is_complete": checkpoint_file.parent.name == "history",
                    "file_name": data.get("state", {}).get("original_file_name")
                }
        except Exception:
            return {
                "session_id": checkpoint_file.stem.replace("checkpoint_", ""),
                "timestamp": checkpoint_file.stat().st_mtime,
                "is_complete": checkpoint_file.parent.name == "history",
                "file_name": "Unknown"
            }
    
    def cleanup_old_sessions(self, days: int = 7):
        """
        Rimuove le sessioni più vecchie di X giorni.
        
        Args:
            days: Numero di giorni dopo i quali eliminare le sessioni
        """
        try:
            current_time = datetime.now().timestamp()
            max_age = days * 24 * 3600
            
            # Pulisci directory current
            for checkpoint_file in (self.base_dir / "current").glob("checkpoint_*.json"):
                if (current_time - checkpoint_file.stat().st_mtime) > max_age:
                    checkpoint_file.unlink()
            
            # Pulisci directory history
            for checkpoint_file in (self.base_dir / "history").glob("checkpoint_*.json"):
                if (current_time - checkpoint_file.stat().st_mtime) > max_age:
                    session_id = checkpoint_file.stem.replace("checkpoint_", "")
                    session_dir = checkpoint_file.parent / session_id
                    if session_dir.exists():
                        shutil.rmtree(session_dir)
                    checkpoint_file.unlink()
                    
            logger.info(f"Pulizia completata per sessioni più vecchie di {days} giorni")
            
        except Exception as e:
            logger.error(f"Errore durante la pulizia delle sessioni: {e}")