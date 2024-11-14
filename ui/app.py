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
        
        # Sezione Sessioni con layout migliorato
        st.subheader("📁 Sessioni Salvate")
        sessions = SessionManager.list_available_sessions()
        
        if sessions:
            # Container per lo stile delle sessioni
            session_container = st.container()
            with session_container:
                for session in sessions:
                    with st.container():
                        # Card stile per ogni sessione
                        st.markdown("""
                            <div style='
                                border: 1px solid #e6e6e6;
                                border-radius: 5px;
                                padding: 10px;
                                margin: 5px 0;
                                background-color: white;
                            '>
                        """, unsafe_allow_html=True)
                        
                        # Informazioni sessione
                        st.markdown(f"""
                            <h4 style='margin: 0;'>{session['file_name']}</h4>
                            <small style='color: #666;'>
                                📅 {datetime.strptime(session['timestamp'], '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')}
                            </small>
                            <p style='margin: 5px 0;'>🔍 {session['query']}</p>
                            <p style='margin: 0;'>📊 {session['rows_count']} risultati</p>
                        """, unsafe_allow_html=True)
                        
                        # Pulsanti azione
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            if st.button("📥 Carica", key=f"load_{session['timestamp']}"):
                                # Carica sessione
                                SessionManager.load_specific_session(session['timestamp'])
                                # st.rerun()
                        with col2:
                            if st.button("🗑️", key=f"delete_{session['timestamp']}"):
                                # Elimina sessione
                                SessionManager.delete_session(session['timestamp'])
                                # st.rerun()
                                
                        st.markdown("</div>", unsafe_allow_html=True)
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
            st.markdown(f"""
                ### 📄 Sessione Corrente
                **File:** {st.session_state.uploaded_file}<br>
                **Query:** {st.session_state.last_query}<br>
                **Data:** {datetime.strptime(st.session_state.processing_timestamp, '%Y%m%d_%H%M%S').strftime('%d/%m/%Y %H:%M')}
            """, unsafe_allow_html=True)
        with col2:
            if st.button("🆕 Nuova Elaborazione", type="primary"):
                st.session_state.clear()
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Mostra risultati
        display_results(st.session_state.results_df)

    # Interfaccia per nuova elaborazione
    if st.session_state.results_df is None:
        # Usa il componente custom file uploader
        uploaded_file = custom_file_uploader()

        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            # Input per query specifica
            query = st.text_input(
                "Inserisci la tua domanda sul contenuto del listino",
                placeholder="es: forniscimi i dati della K901-2R POLTRONA LIFT RELAX A 2 MOTORI"
            )
            st.session_state.last_query = query

            # Pulsante elaborazione
            if st.button("Esegui ricerca", type="primary"):
                # Inizializza la barra di progresso
                progress_bar = ProgressBar(total_steps=100, description="Elaborazione in corso...")
                
                try:
                    # Salva il file caricato
                    temp_path = SessionManager.save_file_to_temp(uploaded_file)
                    
                    # Inizializza i processori
                    processor = PDFProcessor(Path("temp"))
                    vision_api = VisionAPI(api_key)
                    
                    try:
                        # Converti PDF in immagini
                        progress_bar.update(10, "Validazione e conversione PDF in immagini...")
                        
                        # Leggi il file PDF come binary
                        with open(temp_path, 'rb') as pdf_file:
                            image_paths = processor.process_pdf(pdf_file)
                        
                        # Estrai dati
                        progress_bar.update(30, "Analizzando le pagine...")
                        results = []
                        total_pages = len(image_paths)
                        
                        for i, img_path in enumerate(image_paths, 1):
                            try:
                                result = vision_api.extract_data(img_path, query)
                                results.extend(result)
                                progress_bar.update(
                                    30 + (i * 60 // total_pages),
                                    f"Analizzata pagina {i}/{total_pages}"
                                )
                            except Exception as e:
                                progress_bar.update(
                                    30 + (i * 60 // total_pages),
                                    f"⚠️ Errore nell'analisi della pagina {i}: {str(e)}",
                                    is_warning=True
                                )
                        
                        # Processa e mostra risultati
                        if results:
                            progress_bar.update(90, "Elaborazione risultati...")
                            data_processor = DataProcessor()
                            df = data_processor.process_data(results)
                            
                            # Salva risultati in sessione e su disco
                            SessionManager.save_results(df)
                            
                            # Mostra i risultati
                            progress_bar.complete(True)
                            display_results(df)
                            
                        else:
                            progress_bar.complete(False, "Nessun risultato trovato")
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