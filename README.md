## DataProcessor

Il componente `DataProcessor` si occupa dell'elaborazione dei dati estratti dalle immagini e della loro conversione in formato CSV.

### Funzionalità principali:

- Parsing dei dati JSON estratti dalle immagini
- Rimozione duplicati
- Ordinamento dei dati
- Esportazione in formato CSV

### Utilizzo:

```python
from src.extractor.data_processor import DataProcessor

# Inizializza il processore
processor = DataProcessor()

# Elabora i dati
df = processor.process_data(data)

# Salva in CSV
processor.save_csv(df, "output.csv")
```

### Note tecniche:

- Utilizza pandas per la manipolazione dei dati
- Implementa logging per tracciare le operazioni
- Gestisce automaticamente la creazione delle directory di output
- Supporta la rimozione automatica dei duplicati 
