"""
Configurazioni globali per il progetto.
"""

import logging
from pathlib import Path

# Configurazioni per le immagini
IMAGE_SETTINGS = {
    'DPI': 300,
    'FORMAT': 'JPEG',
    'QUALITY': 85,
    'MAX_SIZE': {
        'WIDTH': 2048,
        'HEIGHT': 2048
    }
}

# Configurazioni per OpenAI Vision
VISION_SETTINGS = {
    'MODEL': 'gpt-4o-mini',
    'MAX_TOKENS': 1000,
    'TEMPERATURE': 0.3,
    'PROMPT_TEMPLATE': """Sei un assistente specializzato nell'estrazione di dati strutturati da listini prezzi.

Analizza questa immagine di un listino prezzi ed estrai i dati richiesti.
DEVI RISPONDERE SOLO ED ESCLUSIVAMENTE IN FORMATO JSON, senza alcun testo aggiuntivo.

**IMPORTANTE:** I prezzi dei prodotti seguono due possibili schemi:

1. **Prezzo Singolo:**
   * Il prodotto ha un unico prezzo unitario
   * Non ci sono quantità minime o restrizioni
   * Il prezzo viene indicato direttamente (es. 108,00)

2. **Prezzi per Quantità:**
   * Il prodotto ha prezzi variabili basati sulla quantità
   * Il primo prezzo è SEMPRE associato a una quantità minima (es. "39,00 PER Pz. 4")
   * Potrebbero seguire prezzi scontati per quantità maggiori
   * Se presente, la nota "non vendibili separatamente" indica che la quantità minima è obbligatoria

Per ogni prodotto devi restituire:
{
    "prodotti": [
        {
            "codice": "string",
            "descrizione": "string",
            "tipo_prezzo": "singolo" | "quantita",
            "prezzo_unitario": float,  // Solo se tipo_prezzo è "singolo"
            "prezzi_quantita": [       // Solo se tipo_prezzo è "quantita"
                {
                    "quantita": integer,
                    "prezzo": float,
                    "quantita_minima": boolean,
                    "non_vendibile_separatamente": boolean
                }
            ],
            "descrizione_quantita": "string"  // Es: "Confezione: Pz.4 non vendibili separatamente"
        }
    ]
}

ESEMPI:

1. Prezzo Singolo:
{
    "codice": "T50D",
    "descrizione": "Attacco definitivo per carrozzina",
    "tipo_prezzo": "singolo",
    "prezzo_unitario": 108.0
}

2. Prezzi per Quantità:
{
    "codice": "N04",
    "descrizione": "Deambulatore pieghevole in alluminio...",
    "tipo_prezzo": "quantita",
    "prezzi_quantita": [
        {
            "quantita": 4,
            "prezzo": 39.0,
            "quantita_minima": true,
            "non_vendibile_separatamente": true
        },
        {
            "quantita": 12,
            "prezzo": 37.0,
            "quantita_minima": false,
            "non_vendibile_separatamente": false
        }
    ],
    "descrizione_quantita": "Confezione: Pz.4 non vendibili separatamente"
}

ATTENZIONE:
1. Distingui chiaramente tra prezzi singoli e prezzi per quantità
2. Per i prezzi per quantità, identifica SEMPRE la quantità minima
3. Cattura TUTTE le informazioni sulle restrizioni di vendita
4. Mantieni l'ordine originale dei prezzi dal listino
5. Includi TUTTE le quantità mostrate nel listino
"""
}

# Configurazioni per il logging
LOG_SETTINGS = {
    'LEVEL': logging.DEBUG,
    'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
    'FILE': Path('logs/latest.log'),
    'MAX_BYTES': 5 * 1024 * 1024,  # 5 MB
    'BACKUP_COUNT': 3
}

# Configurazioni per l'output
OUTPUT_SETTINGS = {
    'CSV_DIR': Path('output'),
    'TEMP_DIR': Path('temp'),
    'DATE_FORMAT': '%Y%m%d_%H%M%S'
}