import streamlit as st
import os
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - V14", layout="wide")

# --- DATABASE LISTE ---
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONE PERPLEXITY ---
def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto di ricerca legale. Accedi a bancadatigiurisprudenza.giustiziatributaria.gov.it e trova sentenze reali con i parametri forniti."},
            {"role": "user", "content": query}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Errore Perplexity: {e}"

def extract_text(files):
    t = ""
    for f in files:
        r = PdfReader(f)
        for p in r.pages: t += p.extract_text()
    return t

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Configurazione")
    gemini_key = st.text_input("API Key Gemini", type="password")
    pplx_key = st.text_input("API Key Perplexity", type="password")
    
    st.header("📂 Caricamento")
    f_atto = st.file_uploader("Carica Atto (PDF)", type="pdf")
    f_giur = st.file_uploader("Sentenze interne (PDF)", type="pdf", accept_multiple_files=True)
    
    st.header("🔍 Criteri Banca Dati")
    s_parole = st.text_input("Parole da ricercare")
    s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza"])
    s_anno = st.selectbox("Anno", ["Tutti", "2025", "2024", "2023", "2022", "2021", "2020"])
    s_grado = st.selectbox("Grado autorità", ["Tutti", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale"])
    
    s_autorita, s_appello, s_cassazione = "Tutte", "No", "No"
    if s_grado == "CGT primo grado/Provinciale":
        s_autorita = st.selectbox("Provincia", PROVINCE)
        s_appello = st.radio("Appello", ["Si", "No"])
        s_cassazione = st.radio("Cassazione", ["Si", "No"])
    elif s_grado == "CGT secondo grado/Regionale":
        s_autorita = st.selectbox("Regione", REGIONI)

    s_da = st.date_input("Data da", value=None)
    s_a = st.date_input("Data a", value=None)
    s_esito = st.selectbox("Esito", ["Tutti", "Favorevole al contribuente", "Favorevole all'ufficio", "Giudizio intermedio"])

# --- MAIN ---
st.title("⚖️ Piattaforma Tributaria Professional V14")

tab1, tab2 = st.tabs(["📝 Redazione", "📅 Scadenze"])

with tab1:
    c1, c2, c3 = st.columns(3)
    
    if f_atto and gemini_key:
        client = genai.Client(api_key=gemini_key)
        # Leggiamo i bytes una sola volta per evitare errori di buffer
        atto_content = f_atto.getvalue()
        
        with c1:
            if st.button("🔎 1. Analizza Atto"):
                with st.spinner("Analisi vizi..."):
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=[types.Part.from_bytes(data=atto_content, mime_type="application/pdf"), 
                        "Analizza l'atto ed estrai i vizi tecnici di motivazione e diritto per la difesa."]
                    )
                    st.session_state['vizi'] = res.text

        with c2:
            if st.button("🌐 2. Ricerca su Banca Dati"):
                if not pplx_key: st.error("Inserisci la chiave Perplexity nella sidebar!")
                else:
                    with st.spinner("Perplexity sta interrogando il sito della Giustizia Tributaria..."):
                        query = f"""
                        Cerca nel portale https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca:
                        - Parole chiave: {s_parole if s_parole else st.session_state.get('vizi', 'vizio tributario')}
                        - Tipo: {s_tipo}, Anno: {s_anno}, Grado: {s_grado}, Sede: {s_autorita}
                        - Esito desiderato: {s_esito}, Appello: {s_appello}, Cassazione: {s_cassazione}
                        - Range date: {s_da} - {s_a}
                        Estrai almeno 3 sentenze favorevoli con estremi e principi di diritto applicabili.
                        """
                        st.session_state['giur'] = call_perplexity(pplx_key, query)

        with c3:
            if st.button("✍️ 3. Genera Ricorso"):
                with st.spinner("Generazione atto finale..."):
                    txt_interni = extract_text(f_giur) if f_giur else ""
                    prompt_ricorso = f"""
                    Redigi un RICORSO formale seguendo lo stile del Modello Studio.
                    VIZI RILEVATI: {st.session_state.get('vizi','')}
                    SENTENZE BANCA DATI: {st.session_state.get('giur','')}
                    SENTENZE INTERNE: {txt_interni}
                    Usa lettere (a, b, c) per i motivi e cita gli estremi delle sentenze trovate.
                    """
                    res = client.models.generate_content(
                        model="gemini-2.0-flash", 
                        contents=[types.Part.from_bytes(data=atto_content, mime_type="application/pdf"), prompt_ricorso]
                    )
                    st.session_state['atto'] = res.text

    # Area Risultati
    if 'vizi' in st.session_state: st.info(st.session_state['vizi'])
    if 'giur' in st.session_state: st.success(st.session_state['giur'])
    if 'atto' in st.session_state: st.text_area("Atto Finale:", value=st.session_state['atto'], height=500)
