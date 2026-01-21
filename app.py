import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

# --- CONFIGURAZIONE ULTRA DESIGN ---
st.set_page_config(page_title="Studio Tributario AI - Ultra v18", layout="wide")

st.markdown("""
    <style>
    /* Palette Colori Studio Legale */
    :root {
        --primary-navy: #1a365d;
        --accent-gold: #c0a060;
        --bg-light: #f8fafc;
        --text-dark: #2d3748;
    }

    .main { background-color: var(--bg-light); }

    /* SIDEBAR MODERNA */
    [data-testid="stSidebar"] {
        background-color: var(--primary-navy) !important;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* Input box nella sidebar: sfondo bianco e testo nero per leggibilità */
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select {
        color: var(--text-dark) !important;
        background-color: white !important;
    }
    
    /* Box caricamento file: testo nero su sfondo chiaro */
    [data-testid="stSidebar"] .stFileUploader section div {
        color: var(--text-dark) !important;
    }

    /* CARD RISULTATI */
    .legal-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        border-top: 4px solid var(--accent-gold);
        margin-bottom: 2rem;
        color: var(--text-dark);
        line-height: 1.6;
    }

    /* PULSANTI ACTION */
    .stButton>button {
        border-radius: 10px;
        height: 3.8em;
        background-color: var(--primary-navy);
        color: white;
        font-weight: 700;
        transition: all 0.3s ease;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stButton>button:hover {
        background-color: var(--accent-gold);
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }

    /* TITOLI */
    h1, h2, h3 { 
        font-family: 'Playfair Display', serif; 
        color: var(--primary-navy); 
        letter-spacing: -0.5px;
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
        "messages": [
            {"role": "system", "content": "Sei un analista giurisprudenziale tributario. Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Fornisci sentenze favorevoli al contribuente con estremi e massime precise."},
            {"role": "user", "content": query}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except: return "Ricerca non riuscita. Verifica la connessione."

# --- LOGICA DELLE PAGINE ---

def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Profonda Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.warning("Configura la API Key di Gemini nella barra laterale.")
        return

    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI TECNICA"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Analizza l'atto ed estrai vizi di legittimità e merito."]
            )
            st.session_state['vizi'] = res.text
        
        if 'vizi' in st.session_state:
            st.markdown(f'<div class="legal-card"><h3>Rapporto Analisi Vizi</h3>{st.session_state["vizi"]}</div>', unsafe_allow_html=True)
    else: st.info("In attesa del caricamento dell'atto...")

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Strategia Giurisprudenziale</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.warning("Configura la API Key di Perplexity nella barra laterale.")
        return

    with st.container():
        st.markdown('<div class="legal-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            s_parole = st.text_input("Parole da ricercare", value=st.session_state.get('vizi', '')[:100])
            s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza"])
            s_anno = st.selectbox("Anno", ["Tutti", "2025", "2024", "2023", "2022", "2021", "2020"])
        with c2:
            s_grado = st.selectbox("Grado autorità", ["CGT primo grado/Provinciale", "CGT secondo grado/Regionale"])
            s_sede = st.selectbox("Autorità Emittente", PROVINCE if "primo" in s_grado else REGIONI)
            s_esito = st.selectbox("Esito giudizio", ["Favorevole al contribuente", "Tutti", "Favorevole all'ufficio"])
        with c3:
            s_app = st.radio("Appello", ["Si", "No"], horizontal=True)
            s_cass = st.radio("Cassazione", ["Si", "No"], horizontal=True)
            s_da = st.date_input("Data deposito da", value=None)
        
        if st.button("AVVIA RICERCA IN BANCA DATI"):
            with st.spinner("Perplexity sonar-pro sta filtrando i precedenti..."):
                query = f"Sito: bancadatigiurisprudenza.giustiziatributaria.gov.it. Ricerca: {s_parole}. Grado: {s_grado}, Sede: {s_sede}, Esito: {s_esito}, Appello: {s_app}, Cassazione: {s_cass}."
                st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], query)
        st.markdown('</div>', unsafe_allow_html=True)

    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Precedenti Individuati</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Atto su Modello Studio</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA BOZZA RICORSO PROFESSIONALE"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            txt_off = "".join([extract_text_from_bytes(b) for b in st.session_state.get('f_sentenze', [])])
            prompt = f"Scrivi un ricorso professionale (Modello FATTO/DIRITTO/PQM) basato su vizi: {st.session_state['vizi']}, sentenze online: {st.session_state.get('giur','')}, e sentenze offline: {txt_off}."
            res = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt]
            )
            st.session_state['atto'] = res.text
        
        if 'atto' in st.session_state:
            st.markdown('<div class="legal-card">', unsafe_allow_html=True)
            st.text_area("Revisione Testuale:", value=st.session_state['atto'], height=600)
            st.markdown('</div>', unsafe_allow_html=True)
            st.download_button("📥 DOWNLOAD ATTO FORMATO WORD", st.session_state['atto'], file_name="Ricorso_Studio.docx")
    else: st.warning("Eseguire l'analisi dei vizi nella Dashboard 1 prima di procedere.")

# --- SIDEBAR NAVIGAZIONE ---
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>Studio Tributario</h2>", unsafe_allow_html=True)
    st.session_state['gemini_key'] = st.text_input("Gemini API Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity API Key", type="password")
    st.markdown("---")
    f_acc = st.file_uploader("Accertamento (PDF)", type="pdf")
    if f_acc: st.session_state['f_atto'] = f_acc.getvalue()
    
    f_pre = st.file_uploader("Sentenze Offline", type="pdf", accept_multiple_files=True)
    if f_pre: st.session_state['f_sentenze'] = [f.getvalue() for f in f_pre]

# --- NAVIGAZIONE PAGINE ---
pg = st.navigation([
    st.Page(pagina_analisi, title="Analisi Vizi", icon="🔎"),
    st.Page(pagina_ricerca, title="Banca Dati", icon="🌐"),
    st.Page(pagina_redazione, title="Redazione Atto", icon="✍️")
])
pg.run()
