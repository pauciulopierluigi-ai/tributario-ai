import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Studio Tributario AI - V20", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stFileUploader section div { color: #2d3748 !important; font-weight: 600; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 20px; color: #2d3748; }
    .stButton>button { border-radius: 8px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- LISTE DATI ---
PROVINCE = ["Seleziona", "Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Seleziona", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

def call_perplexity(api_key, query_parts):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    
    # Costruzione stringa di ricerca filtrando i "Seleziona"
    final_query = "Cerca sul sito bancadatigiurisprudenza.giustiziatributaria.gov.it: "
    for k, v in query_parts.items():
        if v not in ["Seleziona", "Tutti", "Non specificato", None]:
            final_query += f"{k}: {v}. "

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto di ricerca su database tributari. Restituisci solo sentenze reali con estremi e massime. Se non trovi nulla con tutti i filtri, allarga la ricerca gradualmente."},
            {"role": "user", "content": final_query}
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e: return f"Errore: {str(e)}"

# --- PAGINE ---
def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Atto</h1>", unsafe_allow_html=True)
    if not st.session_state.get('gemini_key'):
        st.warning("Inserisci la Gemini Key nella sidebar.")
        return
    if 'f_atto' in st.session_state:
        if st.button("ESEGUI ANALISI VIZI"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), "Analizza vizi tecnici."])
            st.session_state['vizi'] = res.text
        if 'vizi' in st.session_state: st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Frazionata Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get('pplx_key'):
        st.warning("Configura Perplexity Key.")
        return

    # --- PARTE 1: RICERCA BASE ---
    with st.expander("🔵 FASE 1: Ricerca Base (Sentenze e Ordinanze)", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: s_parole = st.text_input("Parole da ricercare", value=st.session_state.get('vizi', '')[:100])
        with c2: s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
        with c3: s_anno = st.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])

    # --- PARTE 2: RICERCA AVANZATA (Condizionale) ---
    query_avanzata = {}
    if s_tipo == "Sentenza":
        with st.expander("🟡 FASE 2: Ricerca Avanzata (Filtri Dettagliati)", expanded=True):
            a1, a2 = st.columns(2)
            with a1:
                s_grado = st.selectbox("Grado autorità emittente", ["Seleziona", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale", "Intera regione"])
            with a2:
                lista_sede = PROVINCE if s_grado == "CGT primo grado/Provinciale" else (REGIONI if s_grado in ["CGT secondo grado/Regionale", "Intera regione"] else ["Seleziona"])
                s_sede = st.selectbox("Autorità emittente", lista_sede)
            
            b1, b2 = st.columns(2)
            with b1:
                s_app = st.selectbox("Appello", ["Seleziona", "Si", "No"]) if s_grado == "CGT primo grado/Provinciale" else "Seleziona"
            with b2:
                s_cass = st.selectbox("Cassazione", ["Seleziona", "Si", "No"])

            d1, d2 = st.columns(2)
            with d1:
                s_esito = st.selectbox("Esito giudizio", ["Seleziona", "Conciliazione", "Condono ed altri esiti", "Esito non definitorio", "Favorevole al contribuente", "Favorevole all'ufficio", "Giudizio intermedio", "Reclamo respinto"])
            with d2:
                s_spese = st.selectbox("Spese Giudizio", ["Seleziona", "Compensate", "A carico del contribuente", "A carico dell'ufficio"])

            query_avanzata = {"Grado": s_grado, "Sede": s_sede, "Appello": s_app, "Cassazione": s_cass, "Esito": s_esito, "Spese": s_spese}

    if st.button("AVVIA RICERCA SEQUENZIALE"):
        with st.spinner("Esecuzione ricerca a fasi..."):
            # Unione dei criteri validi
            full_query = {"Parole chiave": s_parole, "Tipo": s_tipo, "Anno": s_anno}
            full_query.update(query_avanzata)
            
            st.session_state['giur'] = call_perplexity(st.session_state['pplx_key'], full_query)

    if 'giur' in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Risultati Ottenuti</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Atto</h1>", unsafe_allow_html=True)
    if 'vizi' in st.session_state:
        if st.button("GENERA RICORSO"):
            client = genai.Client(api_key=st.session_state['gemini_key'])
            prompt = f"Scrivi ricorso FATTO/DIRITTO/PQM su vizi: {st.session_state['vizi']} e giurisprudenza: {st.session_state.get('giur','')}"
            res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=st.session_state['f_atto'], mime_type="application/pdf"), prompt])
            st.session_state['atto'] = res.text
        if 'atto' in st.session_state: st.text_area("Bozza:", value=st.session_state['atto'], height=500)

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<h2>Configurazione</h2>", unsafe_allow_html=True)
    st.session_state['gemini_key'] = st.text_input("Gemini Key", type="password")
    st.session_state['pplx_key'] = st.text_input("Perplexity Key", type="password")
    st.markdown("---")
    f_acc = st.
