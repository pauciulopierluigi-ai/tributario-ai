import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
import time
import io
import re

# --- CONFIGURAZIONE DESIGN V21.1 ---
st.set_page_config(page_title="Studio Tributario AI - V21.1", layout="wide")
st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stFileUploader section div { color: #1a365d !important; font-weight: 600; }
    [data-testid="stSidebar"] .stFileUploader button p { color: #1a365d !important; }
    [data-testid="stSidebar"] .stFileUploader button { border: 1px solid #1a365d !important; background-color: #f0f2f6 !important; }
    [data-testid="stSidebar"] .stFileUploader label { color: white !important; }
    [data-testid="stSidebar"] .uploadedFile { color: white !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 2rem; color: #2d3748; }
    .stButton>button { border-radius: 10px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LISTE ---
PROVINCE = ["Seleziona"] + ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Seleziona"] + ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

@st.cache_data(ttl=3600)
def call_perplexity(api_key, query, system_prompt):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": query}],
        "temperature": 0.0
    }
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            if attempt == 2:
                return f"Errore tecnico: {str(e)} - Risposta completa: {response.text if 'response' in locals() else 'Nessuna risposta'}"
            time.sleep(2 ** attempt)

# --- LOGICA PAGINE ---
def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'): return st.warning("Configura Gemini Key.")
    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI VIZI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Estrai vizi tecnici dell'atto."])
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state: st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Strategica Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'): return st.warning("Configura Perplexity Key.")
    st.subheader("1. Censimento sentenze e ordinanze")
    with st.container().markdown('<div class="legal-card">', unsafe_allow_html=True):
        c1, c2, c3 = st.columns(3)
        default_parole = ""
        if 'f_atto' in st.session_state and st.session_state.get('gemini_key'):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Elenca massimo 3 parole chiave utili per ricerca giurisprudenza tributaria, separate da virgola, senza altro testo."])
            cleaned = re.sub(r'[^a-zA-Z0-9,\s]', '', res.text.strip()).replace('\n', ' ')
            default_parole = ', '.join(word.strip() for word in cleaned.split(',')[:3] if word.strip())
        s_parole = c1.text_input("Parole da ricercare", value=default_parole or st.session_state.get('vizi', '')[:100])
        s_tipo = c2.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
        s_anno = c3.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])
        if st.button("AVVIA FASE 1: CENSIMENTO", disabled=not s_parole):
            progress = st.progress(0)
            with st.spinner("Navigazione web attiva su Giustizia Tributaria..."):
                sys = """Sei un analista esperto di giurisprudenza tributaria. Devi navigare sul sito bancadatigiurisprudenza.giustiziatributaria.gov.it e fornire sempre una sintesi dei risultati trovati. NON dire mai che non puoi accedere al sito o fornire statistiche. Se non ci sono sentenze relative alle parole chiave, dillo esplicitamente e suggerisci parole chiave alternative utili. Se ci sono risultati, fornisci sintesi e conteggio stimato."""
                anno_part = f", Anno: {s_anno}" if s_anno != "Seleziona" else ""
                q = f"Esegui ricerca su bancadatigiurisprudenza.giustiziatributaria.gov.it per '{s_parole}'. Tipo: {s_tipo}{anno_part}. Fornisci sintesi dei risultati trovati."
                st.session_state['fase1_res'] = call_perplexity(st.session_state['pplx_key'], q, sys)
                progress.progress(100)
        st.markdown('</div>', unsafe_allow_html=True)
    if 'fase1_res' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Sintesi Censimento</h3>{st.session_state["fase1_res"]}</div>', unsafe_allow_html=True)
    st.subheader("2. Ricerca avanzata e Analisi di utilità")
    with st.container().markdown('<div class="legal-card">', unsafe_allow_html=True):
        a1, a2 = st.columns(2)
        s_grado = a1.selectbox("Grado autorità emittente", ["Seleziona", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale", "Intera regione"])
        lista_sede = PROVINCE if s_grado == "CGT primo grado/Provinciale" else (REGIONI if s_grado in ["CGT secondo grado/Regionale", "Intera regione"] else ["Seleziona"])
        s_sede = a2.selectbox("Autorità emittente", lista_sede)
        b1, b2 = st.columns(2)
        s_app = b1.selectbox("Appello", ["Seleziona", "Si", "No"]) if s_grado == "CGT primo grado/Provinciale" else "Seleziona"
        s_cass = b2.selectbox("Cassazione", ["Seleziona", "Si", "No"])
        d1, d2 = st.columns(2)
        s_esito = d1.selectbox("Esito giudizio", ["Seleziona", "Favorevole al contribuente", "Favorevole all'ufficio", "Tutti", "Conciliazione", "Condono"])
        s_spese = d2.selectbox("Spese Giudizio", ["Seleziona", "Compensate", "A carico del contribuente", "A carico dell'ufficio"])
        if st.button("AVVIA FASE 2: ANALISI DETTAGLIATA", disabled=s_grado == "Seleziona" or s_sede == "Seleziona"):
            progress = st.progress(0)
            with st.spinner("Analisi giuridica dei precedenti..."):
                sys_base = """Sei un Avvocato Tributarista esperto. Naviga su bancadatigiurisprudenza.giustiziatributaria.gov.it.
                Il tuo compito è trovare sentenze specifiche. Inizia sempre con un conteggio: 'Numero sentenze trovate: N'. Elenca le sentenze trovate."""
                grado_part = f", Grado {s_grado}" if s_grado != "Seleziona" else ""
                sede_part = f", Sede {s_sede}" if s_sede != "Seleziona" else ""
                app_part = f", Appello {s_app}" if s_app != "Seleziona" else ""
                cass_part = f", Cassazione {s_cass}" if s_cass != "Seleziona" else ""
                esito_part = f", Esito {s_esito}" if s_esito != "Seleziona" else ""
                spese_part = f", Spese {s_spese}" if s_spese != "Seleziona" else ""
                q_base = f"Cerca sentenze su bancadatigiurisprudenza.giustiziatributaria.gov.it con parametri: Parole '{s_parole}'{grado_part}{sede_part}{app_part}{cass_part}{esito_part}{spese_part}."
                base_res = call_perplexity(st.session_state['pplx_key'], q_base, sys_base)
                progress.progress(50)
                match = re.search(r'Numero sentenze trovate: (\d+)', base_res)
                num_sentenze = int(match.group(1)) if match else 0
                if num_sentenze > 20:
                    st.session_state['giur'] = "Trovate più di 20 sentenze. Si prega di restringere la ricerca aggiungendo più criteri (es. Esito, Spese)."
                else:
                    sys_filter = """Sei un Avvocato Tributarista esperto. Analizza i risultati forniti.
                    Spiega la loro utilità tecnica per contrastare l'avviso di accertamento. Analizza tutte le sentenze se <=20.
                    Se i criteri sono troppo stretti, suggerisci parole chiave alternative o varianti giuridiche del tema (es: R&S -> Credito Ricerca e Sviluppo)."""
                    q_filter = f"Risultati base: {base_res}. Fornisci analisi utilità e suggerimenti."
                    st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], q_filter, sys_filter)
                progress.progress(100)
        st.markdown('</div>', unsafe_allow_html=True)
    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Analisi Giuridica Sentenze</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Atto</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA RICORSO FINALE"):
            offline_text = ""
            if 'f_sentenze' in st.session_state:
                for pdf_bytes in st.session_state['f_sentenze']:
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    offline_text += " ".join(page.extract_text() for page in reader.pages if page.extract_text())
            client = genai.Client(api_key=st.session_state['gemini_key'])
            prompt = f"Redigi un ricorso su modello FATTO/DIRITTO/PQM usando vizi: {st.session_state['vizi']} e analisi sentenze: {st.session_state.get('giur','')}. Integra le sentenze offline: {offline_text}."
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt])
            st.session_state['atto'] = res.text
        if 'atto' in st.session_state: st.text_area("Bozza Generata:", value=st.session_state['atto'], height=500)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2>Configurazione</h2>", unsafe_allow_html=True)
    st.session_state['gemini_key'] = st.text_input("Gemini Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity Key", type="password")
    st.markdown("---")
    f_acc = st.file_uploader("Accertamento (PDF)", type="pdf")
    if f_acc: st.session_state['f_atto'] = f_acc.getvalue()
    f_pre = st.file_uploader("Sentenze Offline", type="pdf", accept_multiple_files=True)
    if f_pre: st.session_state['f_sentenze'] = [f.getvalue() for f in f_pre]

pg = st.navigation([st.Page(pagina_analisi, title="1. Analisi Vizi", icon="🔎"), st.Page(pagina_ricerca, title="2. Banca Dati", icon="🌐"), st.Page(pagina_redazione, title="3. Redazione Atto", icon="✍️")])
pg.run()
