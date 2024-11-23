# ui/components/results_viewer.py

import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from src.utils.logger import setup_logger
from src.utils.session_manager import SessionManager
import io

logger = setup_logger(__name__)

def _handle_export(df: pd.DataFrame, file_format: str, file_name: str) -> None:
    """
    Gestisce l'esportazione e aggiorna lo stato della sessione.
    
    Args:
        df: DataFrame da esportare
        file_format: Formato di esportazione ('csv' o 'excel')
        file_name: Nome del file esportato
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_info = {
            'timestamp': timestamp,
            'format': file_format,
            'file_name': file_name,
            'rows_count': len(df)
        }
        
        # Aggiorna la sessione tramite SessionManager invece che direttamente
        st.session_state.processing_timestamp = timestamp
        SessionManager.add_export_record(export_info)
        st.experimental_rerun()
        
        logger.info(f"Esportazione completata: {file_name} ({file_format})")
        
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento dello stato: {e}")
        raise

def display_results(df: pd.DataFrame, show_stats: bool = True):
    """
    Visualizza i risultati in una tabella interattiva con opzioni di download.
    """
    try:
        st.subheader("Risultati Estratti")
        
        if df.empty:
            st.warning("Nessun risultato trovato.")
            return
            
        if show_stats:
            # Statistiche base
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Totale Righe", len(df))
            with col2:
                st.metric("Colonne", len(df.columns))
            with col3:
                st.metric("Prodotti Unici", df['codice'].nunique())
        
        # Filtri
        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("🔍 Cerca", placeholder="Filtra per codice o descrizione...")
        with col2:
            sort_by = st.selectbox("Ordina per", df.columns)
            
        # Applica filtri
        if search:
            mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
            df_filtered = df[mask]
        else:
            df_filtered = df
        
        df_filtered = df_filtered.sort_values(sort_by)
        
        # Mostra tabella
        st.dataframe(
            df_filtered,
            use_container_width=True,
            hide_index=True
        )
        
        # Opzioni di download
        col1, col2 = st.columns(2)
        
        # Download CSV
        with col1:
            csv_data = df.to_csv(index=False).encode('utf-8')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"listino_prezzi_{timestamp}.csv"
            
            if st.download_button(
                "📥 Scarica CSV",
                csv_data,
                csv_filename,
                mime='text/csv'
            ):
                _handle_export(df, 'csv', csv_filename)
        
        # Download Excel
        with col2:
            output = io.BytesIO()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            excel_filename = f"listino_prezzi_{timestamp}.xlsx"
            
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Listino', index=False)
                
            excel_data = output.getvalue()
            
            if st.download_button(
                "📊 Scarica Excel",
                excel_data,
                excel_filename,
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ):
                _handle_export(df, 'excel', excel_filename)
                
    except Exception as e:
        logger.error(f"Errore nella visualizzazione dei risultati: {e}")
        st.error("Si è verificato un errore nella visualizzazione dei risultati")
