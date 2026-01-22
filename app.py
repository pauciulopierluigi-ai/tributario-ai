import streamlit as st
import requests
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ULTRA DESIGN ---
st.set_page_config(page_title="Studio Tributario AI - V19", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stFileUploader section div { color: #1e40af !important; font-weight: 600; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 2rem; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 2rem; color: #2d3748; }
    .stButton>button { border-radius: 10px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LISTE ---
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savora", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un agente di ricerca web specializzato in diritto tributario. Devi navigare esclusivamente sul sito bancadatigiurisprudenza.giustiziatributaria.gov.it per trovare sentenze reali. Non rispondere mai che non puoi accedere al sito, usa il tuo modulo di ricerca online per estrarre estremi e massime."},
            {"role": "user", "content": query}
        ]
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=40)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e: return f"Errore tecnico: {str(e)}"

# --- PAGINE ---
def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.warning("Inserisci la Gemini API Key.")
        return
    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), 
                "Analizza l'atto, estrai vizi tecnici e suggerisci 3 brevi stringhe di parole chiave per la ricerca di sentenze simili."]
            )
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state:
            st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.warning("Inserisci la Perplexity API Key.")
        return

    with st.container():
        st.markdown('<div class="legal-card">', unsafe_allow_html=True)
        
        # Suggerimenti parole chiave se disponibili
        if 'vizi' in st.session_state:
            st.info("💡 Suggerimento basato sull'analisi: usa termini come 'difetto di motivazione', 'mancata allegazione' o i vizi estratti.")

        c1, c2, c3 = st.columns(3)
        with c1:
            s_parole = st.text_input("Parole chiave", value=st.session_state.get('search_keywords', ''))
            s_tipo = st.selectbox("Tipo", ["Tutti", "Sentenza", "Ordinanza"])
            s_anno = st.selectbox("Anno", ["Tutti", "2025", "2024", "2023", "2022", "2021", "2020"])
        with c2:
            s_grado = st.selectbox("Grado autorità emittente", ["Non specificato", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale", "Intera regione"])
            
            # Logica condizionale Sede
            lista_sede = ["Tutte"]
            if s_grado == "CGT primo grado/Provinciale": lista_sede = PROVINCE
            elif s_grado in ["CGT secondo grado/Regionale", "Intera regione"]: lista_sede = REGIONI
            
            s_sede = st.selectbox("Sede", lista_sede)
            s_esito = st.selectbox("Esito", ["Favorevole al contribuente", "Favorevole all'ufficio", "Tutti"])
        with c3:
            s_app = st.radio("Appello", ["Non specificato", "Si", "No"], horizontal=True)
            s_cass = st.radio("Cassazione", ["Non specificato", "Si", "No"], horizontal=True)
            s_da = st.date_input("Data da", value=None)
        
        if st.button("AVVIA RICERCA"):
            with st.spinner("Accesso in corso alla Banca Dati Giustizia Tributaria..."):
                query = f"Ricerca sul sito bancadatigiurisprudenza.giustiziatributaria.gov.it: '{s_parole}'. Filtri: Grado: {s_grado}, Sede: {s_sede}, Anno: {s_anno}, Esito: {s_esito}, Appello: {s_app}, Cassazione: {s_cass}. Estrai sentenze favorevoli con data e numero."
                st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], query)
        st.markdown('</div>', unsafe_allow_html=True)

    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Sentenze Individuate</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Ricorso</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA ATTO"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            prompt = f"Redigi un ricorso su modello FATTO/DIRITTO/PQM usando vizi: {st.session_state['vizi']} e sentenze: {st.session_state.get('giur','')}. Cita gli estremi delle sentenze."
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt])
            st.session_state['atto'] = res.text
        if 'atto' in st.session_state:
            st.text_area("Bozza:", value=st.session_state['atto'], height=500)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>Configurazione</h2>", unsafe_allow_html=True)
    st.session_state['gemini_key'] = st.text_input("Gemini API Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity API Key", type="password")
    st.markdown("---")
    f_acc = st.file_uploader("Accertamento (PDF)", type="pdf")
    if f_acc: st.session_state['f_atto'] = f_acc.getvalue()
    f_pre = st.file_uploader("Sentenze Offline", type="pdf", accept_multiple_files=True)
    if f_pre: st.session_state['f_sentenze'] = [f.getvalue() for f in f_pre]

pg = st.navigation([
    st.Page(pagina_analisi, title="1. Analisi Vizi", icon="🔎"),
    st.Page(pagina_ricerca, title="2. Banca Dati", icon="🌐"),
    st.Page(pagina_redazione, title="3. Redazione Atto", icon="✍️")
])
pg.run()
