import streamlit as st
import os
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

# --- CONFIGURAZIONE GENERALE ---
st.set_page_config(page_title="Studio Tributario AI - MultiPage", layout="wide")

# --- DATABASE LISTE ---
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONI UTILI ---
def extract_text(files):
    t = ""
    for f in files:
        r = PdfReader(f)
        for p in r.pages: t += p.extract_text()
    return t

def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto legale. Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Restituisci sentenze con estremi e massime."},
            {"role": "user", "content": query}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except: return "Errore nella ricerca."

# --- PAGINE ---

def pagina_analisi():
    st.title("🔎 Dashboard 1: Analisi Vizi")
    if f_atto and gemini_key:
        client = genai.Client(api_key=gemini_key)
        if st.button("ESEGUI ANALISI TECNICA"):
            with st.spinner("Analisi in corso..."):
                res = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=[types.Part.from_bytes(data=f_atto.getvalue(), mime_type="application/pdf"), "Analizza vizi tecnici."]
                )
                st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state:
            st.markdown(f'<div style="background: white; padding: 25px; border-radius: 10px; border-left: 5px solid #d4af37; box-shadow: 0 4px 6px rgba(0,0,0,0.1); color: black;">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)
    else:
        st.warning("Carica un atto e inserisci la Gemini Key nella sidebar.")

def pagina_ricerca():
    st.title("🌐 Dashboard 2: Ricerca Banca Dati")
    with st.container():
        st.subheader
