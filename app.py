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
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONI CORE ---
def extract_text_from_bytes(pdf_bytes):
    from io import BytesIO
    reader = PdfReader(BytesIO(pdf_bytes))
    return "".join([p.extract_text() for p in reader.pages])

def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "system", "content": "Sei un esperto legale. Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it."}, {"role": "user", "content": query}]
    }
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except: return "Errore di ricerca."

# --- PAGINE ---
def pagina_analisi():
    st.markdown('<h1>🔎 Analisi Tecnica dell\'Atto</h1>', unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.error("⚠️ Inserisci la Gemini API Key nella barra laterale.")
        return
    if 'f_atto' in st.session_state:
        if st.button("AVVIA ANALISI VIZI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Analizza vizi tecnici."])
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state:
            st.markdown(f'<div class="legal-card"><h3>Vizi Rilevati</h3>{st.session_state["vizi"]}</div>', unsafe_allow_html=True)
    else: st.warning("Carica un atto nella barra laterale.")

def pagina_ricerca():
    st.markdown('<h1>🌐 Ricerca Avanzata Banca Dati</h1>', unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.error("⚠️ Inserisci la Perplexity API Key.")
        return
    with st.form("search_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            s_parole = st.text_input("Parole da ricercare", value=st.session_state.get('vizi', '')[:100])
            s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza"])
            s_anno = st.selectbox("Anno", ["Tutti", "2025", "2024", "2023", "2022", "2021", "2020"])
        with c2:
            s_grado = st.selectbox("Grado autorità emittente", ["CGT primo grado/Provinciale", "CGT secondo grado/Regionale"])
            s_sede = st.selectbox("Autorità emittente", PROVINCE if "primo" in s_grado else REGIONI)
            s_esito = st.selectbox("Esito giudizio", ["Favorevole al contribuente", "Favorevole all'ufficio", "Tutti"])
        with c3:
            s_app = st.radio("Appello", ["Si", "No"], horizontal=True)
            s_cass = st.radio("Cassazione", ["Si", "No"], horizontal=True)
            s_da = st.date_input("Data deposito da", value=None)
        
        if st.form_submit_button("RICERCA IN BANCA DATI"):
            with st.spinner("Ricerca in corso..."):
                q = f"Sito: bancadatigiurisprudenza.giustiziatributaria.gov.it. Ricerca: {s_parole}. Grado: {s_grado}, Sede: {s_sede}, Esito: {s_esito}, Appello: {s_app}, Cassazione: {s_cass}."
                st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], q)

    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Risultati</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown('<h1>✍️ Redazione Atto di Ricorso</h1>', unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA BOZZA FINALE"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            txt_offline = "".join([extract_text_from_bytes(b) for b in st.session_state.get('f_sentenze', [])])
            prompt = f"Scrivi un ricorso professionale basato su vizi: {st.session_state['vizi']}, sentenze online: {st.session_state.get('giur','')}, e sentenze offline: {txt_offline}."
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt])
            st.session_state['atto'] = res.text
        if 'atto' in st.session_state:
            st.text_area("Bozza:", value=st.session_state['atto'], height=500)
    else: st.warning("Esegui prima l'analisi dei vizi.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h1>Studio Legale AI</h1>", unsafe_allow_html=True)
    st.session_state['gemini_key'] = st.text_input("Gemini API Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity API Key", type="password")
    st.markdown("---")
    f_acc = st.file_uploader("1. Carica Avviso Accertamento", type="pdf")
    if f_acc: st.session_state['f_atto'] = f_acc.getvalue()
    f_pre = st.file_uploader("2. Carica Sentenze Offline", type="pdf", accept_multiple_files=True)
    if f_pre: st.session_state['f_sentenze'] = [f.getvalue() for f in f_pre]

# --- NAVIGAZIONE ---
pg = st.navigation([
    st.Page(pagina_analisi, title="Analisi Vizi", icon="🔎"),
    st.Page(pagina_ricerca, title="Ricerca Banca Dati", icon="🌐"),
    st.Page(pagina_redazione, title="Redazione Atto", icon="✍️")
])
pg.run()
