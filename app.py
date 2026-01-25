import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader

# --- CONFIGURAZIONE DESIGN V26 ---
st.set_page_config(page_title="Studio Tributario AI - V26", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    
    /* FIX COLORE TESTO FILE CARICATI - FORZATO NERO PER VISIBILITÀ */
    [data-testid="stSidebar"] .stFileUploader section div { color: #000000 !important; font-weight: 800; }
    [data-testid="stSidebar"] .stFileUploader button p { color: #000000 !important; }
    [data-testid="stSidebar"] .stFileUploader button { border: 2px solid #1a365d !important; background-color: #ffffff !important; }
    
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 2rem; color: #2d3748; }
    .stButton>button { border-radius: 10px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; width: 100%; }
    .counter-box { background-color: #eef2f7; padding: 15px; border-radius: 8px; border-left: 8px solid #c0a060; margin-bottom: 10px; color: #1a365d; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE LISTE ---
PROVINCE = ["Seleziona", "Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Seleziona", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

def call_perplexity_step(api_key, history, instruction):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    history.append({"role": "user", "content": f"{instruction}. IMPORTANTE: Leggi il numero totale di risultati accanto alla scritta 'Risultati di ricerca' e riportalo fedelmente."})
    payload = {"model": "sonar-pro", "messages": history, "temperature": 0.0}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": content})
        return content, history
    except Exception as e: return f"Errore: {str(e)}", history

# --- PAGINE ---
def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.warning("Configura Gemini Key nella sidebar.")
        return
    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI VIZI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Analizza vizi tecnici e sostanziali."])
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state: st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Sequenziale Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.warning("Configura Perplexity Key nella sidebar.")
        return
    
    st.subheader("1. Ricerca base")
    with st.container():
        st.markdown('<div class="legal-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: s_parole = st.text_input("Parole da ricercare", value="credito d'imposta")
        with c2: s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
        with c3: s_anno = st.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("2. Ricerca avanzata")
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
        with d1: s_esito = st.selectbox("Esito giudizio", ["Seleziona", "Favorevole al contribuente", "Favorevole all'ufficio", "Conciliazione", "Reclamo respinto"])
        with d2: s_spese = st.selectbox("Spese Giudizio", ["Seleziona", "Compensate", "A carico del contribuente", "A carico dell'ufficio"])
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("AVVIA RICERCA CRITERIO PER CRITERIO"):
        history = [{"role": "system", "content": "Sei un operatore esperto del portale bancadatigiurisprudenza.giustiziatributaria.gov.it. Eseguirai la ricerca criterio per criterio, premendo Ricerca dopo ogni filtro e riportando il numero totale di provvedimenti trovati senza omissioni."}]
        with st.spinner("Sincronizzazione con il database ministeriale..."):
            res, history = call_perplexity_step(st.session_state['pplx_key'], history, f"Passo 1: Inserisci parole chiave: '{s_parole}'. Premi Ricerca e dimmi il numero totale.")
            st.session_state['step1'] = res
            
            if s_tipo != "Tutti" or s_anno != "Seleziona":
                res, history = call_perplexity_step(st.session_state['pplx_key'], history, f"Passo 2: Imposta Tipo: '{s_tipo}' e Anno: '{s_anno}'. Aggiorna il contatore risultati.")
                st.session_state['step2'] = res
            
            if s_grado != "Seleziona":
                res, history = call_perplexity_step(st.session_state['pplx_key'], history, f"Passo 3: Imposta Grado: '{s_grado}', Sede: '{s_sede}', Esito: '{s_esito}'. Analizza le anteprime delle sentenze e dimmi l'utilità.")
                st.session_state['giur'] = res

    if 'step1' in st.session_state: st.markdown(f'<div class="counter-box"><b>Contatore Base:</b> {st.session_state["step1"]}</div>', unsafe_allow_html=True)
    if 'step2' in st.session_state: st.markdown(f'<div class="counter-box"><b>Contatore Filtrato:</b> {st.session_state["step2"]}</div>', unsafe_allow_html=True)
    if 'giur' in st.session_state: st.markdown(f'<div class="legal-card"><h3>Analisi Precedenti</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Atto</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA RICORSO"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            prompt = f"Scrivi ricorso FATTO/DIRITTO/PQM basandoti su vizi: {st.session_state['vizi']} e giurisprudenza trovata: {st.session_state.get('giur','')}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt])
            st.session_state['atto'] = res.text
        if 'atto' in st.session_state: st.text_area("Bozza:", value=st.session_state['atto'], height=500)

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configurazione")
    st.session_state['gemini_key'] = st.text_input("Gemini API Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity API Key", type="password")
    st.markdown("---")
    f_acc = st.file_uploader("Accertamento (PDF)", type="pdf")
    if f_acc: st.session_state['f_atto'] = f_acc.getvalue()
    f_pre = st.file_uploader("Sentenze Offline", type="pdf", accept_multiple_files=True)

pg = st.navigation([st.Page(pagina_analisi, title="1. Analisi Vizi", icon="🔎"), st.Page(pagina_ricerca, title="2. Banca Dati", icon="🌐"), st.Page(pagina_redazione, title="3. Redazione Atto", icon="✍️")])
pg.run()
