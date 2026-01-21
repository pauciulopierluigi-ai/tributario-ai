import streamlit as st
import requests
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ULTRA DESIGN & RECOVERY ---
st.set_page_config(page_title="Studio Tributario AI - Fix V18.1", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card {
        background: white; padding: 2rem; border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent);
        margin-bottom: 2rem; color: #2d3748;
    }
    .stButton>button {
        border-radius: 10px; height: 3.5em; background-color: var(--primary);
        color: white; font-weight: 700; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LISTE ---
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONI CORE (FIXED) ---
def call_perplexity(api_key, query):
    """Funzione di chiamata robusta verso Perplexity AI"""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto di diritto tributario. Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Restituisci estremi e massime."},
            {"role": "user", "content": query}
        ],
        "temperature": 0.2
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Errore tecnico nella ricerca: {str(e)}"

def extract_text_from_bytes(pdf_bytes):
    from io import BytesIO
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        return "".join([p.extract_text() for p in reader.pages])
    except: return ""

# --- LOGICA PAGINE ---

def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.warning("Inserisci la Gemini API Key nella sidebar.")
        return
    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Estrai vizi tecnici dell'atto."]
            )
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state:
            st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.warning("Configura la Perplexity API Key nella sidebar.")
        return

    with st.container():
        st.markdown('<div class="legal-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            s_parole = st.text_input("Parole chiave", value=st.session_state.get('vizi', '')[:150])
            s_tipo = st.selectbox("Tipo", ["Tutti", "Sentenza", "Ordinanza"])
            s_anno = st.selectbox("Anno", ["Tutti", "2025", "2024", "2023", "2022", "2021", "2020"])
        with c2:
            s_grado = st.selectbox("Grado", ["CGT I Grado", "CGT II Grado"])
            s_sede = st.selectbox("Sede", PROVINCE if "I Grado" in s_grado else REGIONI)
            s_esito = st.selectbox("Esito", ["Favorevole al contribuente", "Tutti"])
        with c3:
            s_app = st.radio("Appello", ["Si", "No"], horizontal=True)
            s_cass = st.radio("Cassazione", ["Si", "No"], horizontal=True)
            s_da = st.date_input("Data da", value=None)
        
        if st.button("AVVIA RICERCA"):
            with st.spinner("Interrogazione Banca Dati in corso..."):
                query = f"Trova su bancadatigiurisprudenza.giustiziatributaria.gov.it: {s_parole}. Parametri: Grado {s_grado}, Sede {s_sede}, Anno {s_anno}, Esito {s_esito}. Restituisci sentenze favorevoli con estremi."
                st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], query)
        st.markdown('</div>', unsafe_allow_html=True)

    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Risultati Trovati</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Ricorso</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA ATTO"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            txt_off = "".join([extract_text_from_bytes(b) for b in st.session_state.get('f_sentenze', [])])
            prompt = f"Redigi un ricorso su modello FATTO/DIRITTO/PQM usando vizi: {st.session_state['vizi']}, sentenze online: {st.session_state.get('giur','')}, e sentenze offline: {txt_off}."
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt]
            )
            st.session_state['atto'] = res.text
        if 'atto' in st.session_state:
            st.text_area("Bozza:", value=st.session_state['atto'], height=500)
            st.download_button("📥 SCARICA WORD", st.session_state['atto'], file_name="Ricorso.docx")

# --- SIDEBAR NAVIGAZIONE ---
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
