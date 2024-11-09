import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from src.utils.logger import setup_logger
import io

logger = setup_logger(__name__)

def display_results(df: pd.DataFrame, show_stats: bool = True):
    """
    Visualizza i risultati in una tabella interattiva con opzioni di download.
    
    Args:
        df: DataFrame con i risultati
        show_stats: Se True, mostra statistiche base
    """
    try:
        st.subheader("Risultati Estratti")
        
        if df.empty:
            st.warning("Nessun risultato trovato.")
        else:
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
            if not df.empty:
                col1, col2 = st.columns(2)
                with col1:
                    search = st.text_input("🔍 Cerca", placeholder="Filtra per codice o descrizione...")
                with col2:
                    sort_by = st.selectbox("Ordina per", df.columns)
                    
                # Applica filtri
                if search:
                    mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                    df = df[mask]
                
                df = df.sort_values(sort_by)
            
            # Mostra tabella
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )
            
            # Opzioni di download
            col1, col2 = st.columns(2)
            
            # Download CSV
            with col1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Scarica CSV",
                    csv_data,
                    f"listino_prezzi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime='text/csv'
                )
            
            # Download Excel
            with col2:
                # Crea un buffer in memoria per il file Excel
                output = io.BytesIO()
                # Crea il file Excel
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Listino', index=False)
                # Prepara il file per il download
                excel_data = output.getvalue()
                st.download_button(
                    "📊 Scarica Excel",
                    excel_data,
                    f"listino_prezzi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
    except Exception as e:
        logger.error(f"Errore nella visualizzazione dei risultati: {e}")
        st.error("Si è verificato un errore nella visualizzazione dei risultati")
