import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader

# --- CONFIGURAZIONE DESIGN V21 ---
st.set_page_config(page_title="Studio Tributario AI - V21", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* --- FIX DEFINITIVO VISIBILITÀ BOX CARICAMENTO (TESTO BLU SCURO) --- */
    [data-testid="stSidebar"] .stFileUploader section div { color: #1a365d !important; font-weight: 600; }
    [data-testid="stSidebar"] .stFileUploader button p { color: #1a365d !important; }
    [data-testid="stSidebar"] .stFileUploader button { border: 1px solid #1a365d !important; background-color: #f0f2f6 !important; }
    
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 2rem; color: #2d3748; }
    .stButton>button { border-radius: 10px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE LISTE ---
PROVINCE = ["Seleziona", "Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Seleziona", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

def call_perplexity(api_key, query, system_prompt):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e: return f"Errore tecnico: {str(e)}"

# --- LOGICA PAGINE ---

def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.warning("Configura Gemini Key.")
        return
    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI VIZI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Estrai vizi tecnici dell'atto."])
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state: st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Strategica Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.warning("Configura Perplexity Key.")
        return

    # --- FASE 1: CENSIMENTO BASE ---
    st.subheader("1. Censimento sentenze e ordinanze")
    with st.container():
        st.markdown('<div class="legal-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: s_parole = st.text_input("Parole da ricercare", value=st.session_state.get('vizi', '')[:100])
        with c2: s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
        with c3: s_anno = st.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])
        
        if st.button("AVVIA FASE 1: CENSIMENTO NUMERICO"):
            with st.spinner("Censimento in corso su Giustizia Tributaria..."):
                sys = "Sei un analista numerico. Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Il tuo compito è solo dire QUANTE sentenze esistono per i criteri dati, divise per anno e regione/provincia. Non analizzare il contenuto ancora."
                q = f"Sito bancadatigiurisprudenza.giustiziatributaria.gov.it. Query: {s_parole}. Tipo: {s_tipo}. Anno: {s_anno}. Fornisci un riepilogo statistico (quante trovate)."
                st.session_state['fase1_res'] = call_perplexity(st.session_state['pplx_key'], q, sys)
        st.markdown('</div>', unsafe_allow_html=True)

    if 'fase1_res' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Sintesi Censimento</h3>{st.session_state["fase1_res"]}</div>', unsafe_allow_html=True)
        
        # --- FASE 2: RICERCA AVANZATA E ANALISI ---
        st.subheader("2. Ricerca avanzata e Analisi di utilità")
        with st.container():
            st.markdown('<div class="legal-card">', unsafe_allow_html=True)
            a1, a2 = st.columns(2)
            with a1: s_grado = st.selectbox("Grado autorità emittente", ["Seleziona", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale", "Intera regione"])
            with a2:
                lista_sede = PROVINCE if s_grado == "CGT primo grado/Provinciale" else (REGIONI if s_grado in ["CGT secondo grado/Regionale", "Intera regione"] else ["Seleziona"])
                s_sede = st.selectbox("Autorità emittente", lista_sede)
            
            b1, b2 = st.columns(2)
            with b1: s_app = st.selectbox("Appello", ["Seleziona", "Si", "No"]) if s_grado == "CGT primo grado/Provinciale" else "Seleziona"
            with b2: s_cass = st.selectbox("Cassazione", ["Seleziona", "Si", "No"])

            d1, d2 = st.columns(2)
            with d1: s_esito = st.selectbox("Esito giudizio", ["Seleziona", "Favorevole al contribuente", "Favorevole all'ufficio", "Tutti", "Conciliazione", "Condono"])
            with d2: s_spese = st.selectbox("Spese Giudizio", ["Seleziona", "Compensate", "A carico del contribuente", "A carico dell'ufficio"])
            
            if st.button("AVVIA FASE 2: ANALISI DETTAGLIATA"):
                with st.spinner("Analisi giuridica dei precedenti in corso..."):
                    sys = "Sei un esperto avvocato tributarista. Naviga su bancadatigiurisprudenza.giustiziatributaria.gov.it. Estrai le sentenze migliori dai criteri e spiega perché sono utili o inutili per il caso di accertamento dell'utente."
                    q = f"Sito bancadatigiurisprudenza.giustiziatributaria.gov.it. Cerca sentenze con: Parole {s_parole}, Grado {s_grado}, Sede {s_sede}, Esito {s_esito}. Analizza il merito e l'utilità tecnica."
                    st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], q, sys)
            st.markdown('</div>', unsafe_allow_html=True)

    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Analisi Giuridica Sentenze</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Atto</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA RICORSO FINALE"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            prompt = f"Redigi un ricorso su modello FATTO/DIRITTO/PQM usando vizi: {st.session_state['vizi']} e analisi sentenze: {st.session_state.get('giur','')}. Integra anche sentenze offline se caricate."
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
