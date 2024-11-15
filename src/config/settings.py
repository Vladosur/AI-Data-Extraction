"""
Configurazioni globali per il progetto.
"""

import logging
from pathlib import Path

# Configurazioni per le immagini
# IMAGE_SETTINGS = {
#     'DPI': 200,  # Ridotto ma ancora buono per il testo
#     'FORMAT': 'JPEG',
#     'QUALITY': 85,
#     'MAX_SIZE': {
#         'WIDTH': 1024,   # Ridotto per rispettare i limiti
#         'HEIGHT': 1024   # Ridotto per rispettare i limiti
#     },
# }
IMAGE_SETTINGS = {
    'DPI': 200,  
    'FORMAT': 'JPEG',
    'QUALITY': 85,
    'MAX_SIZE': {
        'WIDTH': 750,     # Massimizziamo il lato corto rimanendo sotto 768px
        'HEIGHT': 1060    # Manteniamo la proporzione A4 (~1.414)
    }
}

# Configurazioni per OpenAI Vision
VISION_SETTINGS = {
    'MODEL': 'gpt-4o-mini',
    'IMAGE_DETAIL': 'high',
    'MAX_TOKENS': 1000,
    'TEMPERATURE': 0,
    'PROMPT_TEMPLATE': """Sei un assistente specializzato nell'estrazione di dati strutturati da listini prezzi.

Analizza questa immagine di un listino prezzi ed estrai i dati richiesti.
DEVI RISPONDERE SOLO ED ESCLUSIVAMENTE IN FORMATO JSON, senza alcun testo aggiuntivo.

**ATTENZIONE: ASPETTO CRITICO**
Quando un prodotto presenta più misure/varianti con lo stesso prezzo, DEVI CREARE UN RECORD SEPARATO PER OGNI VARIANTE.
Esempio: Se vedi:
"COD. RC330-40 Misura 40 cm
 COD. RC330-46 Misura 46 cm
 COD. RC330-48 Misura 48 cm
 € 148,00 cad."
Devi creare TRE record separati, uno per ogni codice e misura, tutti con lo stesso prezzo.

**IMPORTANTE:** I prezzi dei prodotti seguono due possibili schemi:

1. **Prezzo Singolo:**
   * Il prodotto ha un unico prezzo unitario
   * Non ci sono quantità minime o restrizioni
   * Il prezzo viene indicato direttamente (es. 108,00)
   * IMPORTANTE: Se lo stesso prezzo si applica a più varianti/misure, crea un record per OGNI variante

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

ESEMPI CORRETTI di output per prodotti con varianti:

{
    "prodotti": [
        {
            "codice": "RC330-40",
            "descrizione": "Sedia comoda reclinabile, 4 ruote da 20 cm - Misura 40 cm",
            "tipo_prezzo": "singolo",
            "prezzo_unitario": 148.0
        },
        {
            "codice": "RC330-46",
            "descrizione": "Sedia comoda reclinabile, 4 ruote da 20 cm - Misura 46 cm",
            "tipo_prezzo": "singolo",
            "prezzo_unitario": 148.0
        },
        {
            "codice": "RC330-48",
            "descrizione": "Sedia comoda reclinabile, 4 ruote da 20 cm - Misura 48 cm",
            "tipo_prezzo": "singolo",
            "prezzo_unitario": 148.0
        }
    ]
}

RICORDA: NON OMETTERE MAI nessuna variante dimensionale. Se vedi più codici con misure diverse ma stesso prezzo, devi creare un record separato per OGNUNO di essi."""
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