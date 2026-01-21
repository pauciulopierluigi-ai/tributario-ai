import streamlit as st
import os
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Studio Tributario AI", layout="wide")

# Liste per i menu a tendina
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONI ---
def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto di ricerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Fornisci sentenze reali con estremi e massime."},
            {"role": "user", "content": query}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except: return "Errore di connessione con la banca dati."

# --- PAGINE ---
def pagina_analisi():
    st.title("🔎 1. Analisi Tecnica dell'Atto")
    if 'f_atto' in st.session_state and st.session_state['f_atto'] is not None:
        if st.button("ESEGUI ANALISI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Analizza vizi tecnici."]
            )
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state:
            st.info(st.session_state['vizi'])
    else: st.warning("Carica un atto nella barra laterale.")

def pagina_ricerca():
    st.title("🌐 2. Ricerca Giurisprudenza Tributaria")
    with st.expander("Filtri Avanzati Banca Dati", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            s_parole = st.text_input("Parole chiave", value=st.session_state.get('vizi', '')[:100])
            s_grado = st.selectbox("Grado", ["CGT I Grado", "CGT II Grado"])
        with c2:
            s_esito = st.selectbox("Esito", ["Favorevole al contribuente", "Tutti"])
            s_sede = st.selectbox("Sede", PROVINCE if "I Grado" in s_grado else REGIONI)
            
    if st.button("AVVIA RICERCA"):
        q = f"Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it: {s_parole}. Grado: {s_grado}, Sede: {s_sede}, Esito: {s_esito}."
        st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], q)
        
    if 'giur' in st.session_state:
        st.success(st.session_state['giur'])

def pagina_redazione():
    st.title("✍️ 3. Redazione del Ricorso")
    if st.button("GENERA DOCUMENTO FINALE"):
        client = genai.Client(api_key=st.session_state['gemini_key'])
        prompt = f"Scrivi un ricorso basato su vizi: {st.session_state.get('vizi','')} e precedenti: {st.session_state.get('giur','')}"
        res = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt]
        )
        st.session_state['atto'] = res.text
        
    if 'atto' in st.session_state:
        st.text_area("Revisione:", value=st.session_state['atto'], height=400)

# --- SIDEBAR E NAVIGAZIONE ---
with st.sidebar:
    st.title("Configurazione")
    st.session_state['gemini_key'] = st.text_input("Gemini Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity Key", type="password")
    f_caricato = st.file_uploader("Carica Atto", type="pdf")
    if f_caricato: st.session_state['f_atto'] = f_caricato.getvalue()

pg = st.navigation([
    st.Page(pagina_analisi, title="Analisi Vizi", icon="🔎"),
    st.Page(pagina_ricerca, title="Ricerca Banca Dati", icon="🌐"),
    st.Page(pagina_redazione, title="Redazione Atto", icon="✍️")
])
pg.run()
