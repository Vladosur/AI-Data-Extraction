"""
Test unitari per il modulo data_processor
"""

import pytest
import pandas as pd
from pathlib import Path
from src.extractor.data_processor import DataProcessor

@pytest.fixture
def data_processor():
    """Fixture che fornisce un'istanza di DataProcessor"""
    return DataProcessor()

@pytest.fixture
def sample_data():
    """Fixture che fornisce dati di esempio per i test"""
    return [
        {"codice": "001", "descrizione": "Prodotto 1", "prezzo": 10.50},
        {"codice": "002", "descrizione": "Prodotto 2", "prezzo": 15.75},
        {"codice": "001", "descrizione": "Prodotto 1", "prezzo": 10.50},  # duplicato
    ]

def test_process_data_basic(data_processor, sample_data):
    """Testa la funzionalità base di process_data"""
    df = data_processor.process_data(sample_data)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2  # verifica rimozione duplicati
    assert list(df.columns) == ["codice", "descrizione", "prezzo"]
    assert df["codice"].iloc[0] == "001"

def test_process_data_empty(data_processor):
    """Testa process_data con lista vuota"""
    df = data_processor.process_data([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0

def test_process_data_invalid_input(data_processor):
    """Testa process_data con input non valido"""
    with pytest.raises(Exception):
        data_processor.process_data(None)

def test_save_csv(data_processor, sample_data, tmp_path):
    """Testa il salvataggio del CSV"""
    df = data_processor.process_data(sample_data)
    output_path = tmp_path / "test_output.csv"
    
    data_processor.save_csv(df, output_path)
    
    assert output_path.exists()
    df_loaded = pd.read_csv(output_path)
    assert len(df_loaded) == len(df)
    assert list(df_loaded.columns) == list(df.columns)

def test_save_csv_invalid_path(data_processor, sample_data):
    """Testa il salvataggio del CSV con percorso non valido"""
    df = data_processor.process_data(sample_data)
    invalid_path = Path("/invalid/path/test.csv")
    
    with pytest.raises(Exception):
        data_processor.save_csv(df, invalid_path) 