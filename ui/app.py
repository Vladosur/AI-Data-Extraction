# ui/app.py

import sys
from pathlib import Path
import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import traceback

# Carica variabili d'ambiente
load_dotenv()

# Aggiungi la root del progetto al Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Importazioni dai moduli del progetto
from src.extractor.pdf_processor import PDFProcessor
from src.extractor.vision_api import VisionAPI
from src.extractor.data_processor import DataProcessor
from src.utils.logger import setup_logger
from src.utils.session_manager import SessionManager
from src.utils.pdf_validator import PDFValidationError
from ui.components.file_uploader import custom_file_uploader
from ui.components.progress import ProgressBar
from ui.components.results_viewer import display_results

# Inizializza il logger
logger = setup_logger()

def display_error_message(error: Exception, progress_bar: Optional[ProgressBar] = None):
    """
    Mostra un messaggio di errore appropriato all'utente.
    
    Args:
        error: Eccezione da mostrare
        progress_bar: ProgressBar opzionale per mostrare l'errore
    """
    error_message = str(error)
    error_details = traceback.format_exc()
    
    if isinstance(error, PDFValidationError):
        title = "Errore nella validazione del PDF"
        detail = f"Dettaglio: {error_message}"
    else:
        title = "Si è verificato un errore durante l'elaborazione"
        detail = error_details

    if progress_bar:
        progress_bar.show_error(title, detail)
    else:
        st.error(title)
        st.code(detail)
    
    logger.error(f"Errore: {error_message}\n{error_details}")

def display_session_header():
    """
    Mostra l'header con le informazioni della sessione corrente.
    """
    session_info = SessionManager.get_session_info()
    
    if not session_info.get('has_results'):
        return
        
    st.markdown("""
        <div style='
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        '>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Info base
        st.markdown(f"""
            ### 📄 Sessione Corrente
            **File:** {session_info['file_name']}<br>
            **Data:** {datetime.strptime(session_info['processing_timestamp'], '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')}<br>
            **Righe elaborate:** {session_info['rows_count']}
        """, unsafe_allow_html=True)
        
        # Info esportazioni
        if session_info.get('export_history'):
            last_export = session_info['metadata'].get('last_export', {})
            if last_export:
                st.markdown(f"""
                    **Ultima esportazione:** {last_export.get('format', '').upper()} - {
                        datetime.strptime(last_export.get('timestamp', ''), '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')
                    }
                """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🆕 Nuova Elaborazione", type="primary"):
            SessionManager._clear_current_session()
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    st.set_page_config(
        page_title="PDF Listino Prezzi Extractor",
        page_icon="📄",
        layout="wide"
    )

    # Inizializza sessione
    SessionManager.initialize_session()
    
    # Carica ultima sessione all'avvio
    if st.session_state.results_df is None:
        SessionManager.load_last_session()

    # Carica CSS personalizzato
    with open('ui/styles/main.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    st.title("Estrazione Dati da Listino Prezzi")

    # Verifica API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        st.error("⚠️ API key non trovata nel file .env")
        st.stop()

    # Sidebar migliorata
    with st.sidebar:
        st.header("🔧 Configurazioni")
        
        # Sezione Sessioni con layout e funzionalità migliorate
        st.subheader("📁 Sessioni Salvate")
        sessions = SessionManager.list_available_sessions()
        
        if sessions:
            # Filtri e ordinamento
            col1, col2 = st.columns(2)
            with col1:
                search = st.text_input("🔍 Cerca", placeholder="Nome file...")
            with col2:
                sort_by = st.selectbox(
                    "Ordina per",
                    ["Data ↓", "Data ↑", "Nome", "Risultati"],
                    key="sort_sessions"
                )
            
            # Applica filtri e ordinamento
            if search:
                sessions = [s for s in sessions if search.lower() in s['file_name'].lower()]
                
            sessions = sorted(sessions, key=lambda x: {
                "Data ↓": lambda s: s['timestamp'],
                "Data ↑": lambda s: s['timestamp'],
                "Nome": lambda s: s['file_name'].lower(),
                "Risultati": lambda s: s['rows_count']
            }[sort_by](x), reverse=sort_by == "Data ↓")
            
            # Paginazione
            ITEMS_PER_PAGE = 5
            total_pages = len(sessions) // ITEMS_PER_PAGE + (1 if len(sessions) % ITEMS_PER_PAGE > 0 else 0)
            
            if 'current_page' not in st.session_state:
                st.session_state.current_page = 0
                
            start_idx = st.session_state.current_page * ITEMS_PER_PAGE
            end_idx = min(start_idx + ITEMS_PER_PAGE, len(sessions))
            
            # Visualizza sessioni paginate
            session_container = st.container()
            with session_container:
                for session in sessions[start_idx:end_idx]:
                    with st.container():
                        st.markdown(f"""
                            <div style='
                                border: 1px solid #e6e6e6;
                                border-radius: 5px;
                                padding: 10px;
                                margin: 5px 0;
                                background-color: white;
                            '>
                                <h4 style='margin: 0;'>{session['file_name']}</h4>
                                <small style='color: #666;'>
                                    📅 {datetime.strptime(session['timestamp'], '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')}
                                </small>
                                <p style='margin: 5px 0;'>📊 {session['rows_count']} risultati</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            if st.button("📥 Carica", key=f"load_{session['timestamp']}"):
                                SessionManager.load_specific_session(session['timestamp'])
                                st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"delete_{session['timestamp']}"):
                                SessionManager.delete_session(session['timestamp'])
                                st.rerun()
                
                # Controlli paginazione
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.session_state.current_page > 0:
                            if st.button("⬅️"):
                                st.session_state.current_page -= 1
                                st.rerun()
                    with col2:
                        st.write(f"Pagina {st.session_state.current_page + 1} di {total_pages}")
                    with col3:
                        if st.session_state.current_page < total_pages - 1:
                            if st.button("➡️"):
                                st.session_state.current_page += 1
                                st.rerun()
        else:
            st.info("🔍 Nessuna sessione salvata")
        
        # Separatore
        st.divider()
        
        # Opzioni aggiuntive
        with st.expander("⚙️ Opzioni Avanzate"):
            show_logs = st.checkbox("📝 Mostra Log", value=False)
            if st.button("🧹 Pulisci Sessioni Vecchie", type="secondary"):
                SessionManager.cleanup_old_sessions()
                st.success("✅ Pulizia completata")
                # st.rerun()

    # Area principale dei risultati
    if st.session_state.results_df is not None:
        # Header con info sessione corrente
        st.markdown("""
            <div style='
                background-color: #f0f2f6;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            '>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        with col1:
            export_info = st.session_state.get('session_metadata', {}).get('last_export', {})
            export_count = len(st.session_state.get('export_history', []))
            
            # Info base più info esportazione
            st.markdown(f"""
                ### 📄 Sessione Corrente
                **File:** {st.session_state.uploaded_file}<br>
                **Data:** {datetime.strptime(st.session_state.processing_timestamp, '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')}<br>
                **Righe elaborate:** {len(st.session_state.results_df)}
                {f"<br>**Ultima esportazione:** {export_info.get('format', '').upper()} - {datetime.strptime(export_info.get('timestamp', ''), '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')}" if export_info else ''}
                {f"<br>**Totale esportazioni:** {export_count}" if export_count > 0 else ''}
            """, unsafe_allow_html=True)
                
        with col2:
            if st.button("🆕 Nuova Elaborazione", type="primary"):
                SessionManager._clear_current_session()
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Mostra risultati
        display_results(st.session_state.results_df)

    # Interfaccia per nuova elaborazione
    if st.session_state.results_df is None:
        uploaded_file = custom_file_uploader()

        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file

        # Nel blocco di elaborazione principale:
        if st.button("Avvia Estrazione", type="primary"):
            progress_bar = ProgressBar(total_steps=100, description="Elaborazione in corso...")
            
            try:
                # Salva il file caricato
                progress_bar.update(5, "Preparazione file...")
                temp_path = SessionManager.save_file_to_temp(uploaded_file)
                
                # Inizializza i processori
                processor = PDFProcessor()  
                vision_api = VisionAPI(api_key)
                
                try:
                    # Converti PDF in immagini
                    progress_bar.update(10, "Validazione e conversione PDF in immagini...")
                    images = processor.process_pdf(uploaded_file)
                    
                    # Calcoli accurati per il progresso
                    total_pages = len(images)
                    analysis_portion = 60  # 60% dedicato all'analisi delle pagine
                    page_weight = analysis_portion / total_pages
                    base_progress = 30  # 30% per la preparazione iniziale
                    
                    progress_bar.update(30, f"Inizio analisi di {total_pages} pagine...")
                    results = []
                    
                    for i, image in enumerate(images, 1):
                        try:
                            result = vision_api.extract_data(image)
                            results.extend(result)
                            
                            # Calcola il progresso attuale
                            current_progress = base_progress + (i * page_weight)
                            progress_bar.update(
                                int(current_progress),
                                f"Analizzata pagina {i}/{total_pages}"
                            )
                        except Exception as e:
                            progress_bar.update(
                                int(base_progress + (i * page_weight)),
                                f"⚠️ Errore nell'analisi della pagina {i}: {str(e)}",
                                is_warning=True
                            )
                    
                    if results:
                        progress_bar.update(90, "Elaborazione risultati...")
                        data_processor = DataProcessor()
                        df = data_processor.process_data(results)
                        
                        progress_bar.update(95, "Salvataggio risultati...")
                        SessionManager.save_results(df)
                        
                        # Assicura il 100% prima del completamento
                        progress_bar.update(100, "Completamento elaborazione...")
                        progress_bar.complete(True, "✅ Elaborazione completata con successo!")
                        st.rerun()
                    else:
                        progress_bar.complete(False, "⚠️ Nessun risultato trovato")
                        st.warning("⚠️ Nessun risultato trovato")
                        
                except PDFValidationError as e:
                    display_error_message(e, progress_bar)
                except Exception as e:
                    display_error_message(e, progress_bar)

            except Exception as e:
                display_error_message(e)

        # Area log
        if show_logs:
            with st.expander("Log", expanded=True):
                try:
                    log_content = Path("logs/latest.log").read_text()
                    st.code(log_content)
                except Exception as e:
                    st.warning("⚠️ Impossibile leggere il file di log")
                    logger.error(f"Errore lettura log: {str(e)}")

if __name__ == "__main__":
    main()