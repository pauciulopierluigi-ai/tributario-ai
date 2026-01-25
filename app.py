import streamlit as st
import requests

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Studio Tributario AI - V24", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    /* FIX VISIBILITÀ NOMI FILE (BLU NOTTE) */
    [data-testid="stSidebar"] .stFileUploader section div { color: #0c1a30 !important; font-weight: 700; }
    [data-testid="stSidebar"] .stFileUploader button p { color: #0c1a30 !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 2rem; color: #2d3748; }
    .stButton>button { border-radius: 10px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; width: 100%; }
    .counter-box { background-color: #f1f3f9; padding: 15px; border-radius: 8px; border-left: 8px solid var(--primary); margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- LISTE ---
PROVINCE = ["Seleziona", "Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Seleziona", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

def call_perplexity_step(api_key, conversation_history, user_instruction):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    
    conversation_history.append({"role": "user", "content": user_instruction})
    
    payload = {
        "model": "sonar-pro",
        "messages": conversation_history,
        "temperature": 0.0
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        conversation_history.append({"role": "assistant", "content": content})
        return content, conversation_history
    except Exception as e:
        return f"Errore: {str(e)}", conversation_history

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Configurazione")
    pplx_key = st.text_input("Perplexity API Key", type="password")
    st.markdown("---")
    st.file_uploader("Accertamento (PDF)", type="pdf")
    st.file_uploader("Sentenze Offline", type="pdf", accept_multiple_files=True)

# --- INTERFACCIA ---
st.title("🌐 Ricerca Sequenziale Criterio per Criterio")

# BLOCCO 1: PARAMETRI BASE
st.subheader("1. Ricerca base")
with st.container():
    st.markdown('<div class="legal-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: s_parole = st.text_input("Parole da ricercare", value="incompetenza territoriale")
    with c2: s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
    with c3: s_anno = st.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])
    st.markdown('</div>', unsafe_allow_html=True)

# BLOCCO 2: AVANZATA
if s_tipo == "Sentenza":
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

# LOGICA ESECUZIONE SEQUENZIALE
if st.button("AVVIA RICERCA SEQUENZIALE"):
    if not pplx_key:
        st.error("Inserisci la chiave API.")
    else:
        history = [{"role": "system", "content": "Sei un operatore esperto del sito bancadatigiurisprudenza.giustiziatributaria.gov.it. Eseguirai la ricerca criterio per criterio. Per ogni filtro inserito, riporterai il numero esatto di provvedimenti trovati (es. 'Risultati di ricerca (10.002)'). Poi analizzerai le anteprime delle sentenze per verificarne l'utilità."}]
        
        # Passo 1: Parole Chiave
        with st.spinner("Passo 1: Inserimento parole chiave..."):
            instr = f"Vai sul sito e inserisci '{s_parole}' nel campo parole chiave. Premi ricerca e dimmi ESATTAMENTE quanti provvedimenti ci sono."
            res, history = call_perplexity_step(pplx_key, history, instr)
            st.markdown(f'<div class="counter-box"><b>Passo 1:</b> {res}</div>', unsafe_allow_html=True)

        # Passo 2: Tipo Provvedimento
        if s_tipo != "Tutti":
            with st.spinner(f"Passo 2: Filtro {s_tipo}..."):
                instr = f"Ora seleziona Tipo provvedimento: '{s_tipo}' e aggiorna la ricerca. Dimmi il nuovo numero totale di risultati."
                res, history = call_perplexity_step(pplx_key, history, instr)
                st.markdown(f'<div class="counter-box"><b>Passo 2:</b> {res}</div>', unsafe_allow_html=True)

        # Passo 3: Anno
        if s_anno != "Seleziona":
            with st.spinner(f"Passo 3: Filtro Anno {s_anno}..."):
                instr = f"Aggiungi il filtro Anno: '{s_anno}' e aggiorna. Quanti provvedimenti risultano ora?"
                res, history = call_perplexity_step(pplx_key, history, instr)
                st.markdown(f'<div class="counter-box"><b>Passo 3:</b> {res}</div>', unsafe_allow_html=True)

        # Passo 4: Filtri Avanzati e Analisi Anteprime
        if s_tipo == "Sentenza" and s_grado != "Seleziona":
            with st.spinner("Passo 4: Filtri avanzati e analisi anteprime..."):
                instr = f"Filtra per Grado: '{s_grado}', Sede: '{s_sede}' ed Esito: '{s_esito}'. Apri le anteprime delle sentenze trovate, analizzale e dimmi quali sono utili al caso."
                res, history = call_perplexity_step(pplx_key, history, instr)
                st.markdown(f'<div class="legal-card"><h3>Analisi Giuridica (Basata su Anteprime)</h3>{res}</div>', unsafe_allow_html=True)
