import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ESTETICA AVANZATA ---
st.set_page_config(page_title="Studio Tributario AI", layout="wide")

st.markdown("""
    <style>
    /* Sfondo Generale */
    .main { background-color: #f4f7f9; }
    
    /* SIDEBAR: SFONDO BLU E TUTTO IL TESTO BIANCO */
    [data-testid="stSidebar"] {
        background-color: #1a365d !important;
    }
    
    /* Forza il bianco su: Testi, Titoli, Label, Input help e il Menu di Navigazione */
    [data-testid="stSidebar"] *, 
    [data-testid="stSidebarContent"] *,
    [data-testid="stSidebarNav"] * {
        color: white !important;
    }

    /* Fix specifico per i nomi delle pagine nel menu di navigazione */
    [data-testid="stSidebarNavItems"] span {
        color: white !important;
    }

    /* Pannelli Risultati (Cards) */
    .legal-card {
        background-color: white;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-top: 5px solid #c0a060;
        margin-bottom: 25px;
        color: #2d3748;
    }

    /* Pulsanti */
    .stButton>button {
        border-radius: 8px;
        height: 3.5em;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LISTE ---
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "
