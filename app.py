import streamlit as st
import os
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - V12", layout="wide")

# --- DATABASE LISTE ---
PROVINCE = ["AG", "AL", "AN", "AO", "AQ", "AR", "AP", "AT", "AV", "BA", "BT", "BL", "BN", "BG", "BI", "BO", "BZ", "BS", "BR", "CA", "CL", "CB", "CE", "CH", "CO", "CS", "CR", "KR", "CN", "EN", "FM", "FE", "FI", "FG", "FC", "GE", "GO", "GR", "IM", "IS", "SP", "LT", "LE", "LC", "LI", "LO", "LU", "MC", "MN", "MS", "MT", "ME", "MI", "MO", "MB", "NA", "NO", "NU", "OR", "PD", "PA", "PR", "PV", "PG", "PU", "PE", "PC", "PI", "PT", "PN", "PZ", "PO", "RG", "RA", "RC", "RE", "RI", "RN", "RM", "RO", "SA", "SS", "SV", "SI", "SR", "SO", "TA", "TE", "TR", "TO", "TP", "TN", "TV", "TS", "UD", "VA", "VE", "VB", "VC", "VR", "VV", "VI", "VT"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONI CORE ---
def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto di ricerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Restituisci sentenze reali con estremi e massime."},
            {"role": "user", "content": query}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Errore ricerca: {e}"

def extract_text_from_pdfs(pdf_files):
    text = ""
    for pdf in pdf_files:
        reader = PdfReader(pdf)
        for page in reader.pages: text += page.extract_text()
    return text

# --- SIDEBAR: CRITERI DI RICERCA BANCA DATI ---
with st.sidebar:
    st.header("🔑 API Keys")
    gemini_key = st.text_input("Gemini API Key", type="password")
    pplx_key = st.text_input("Perplexity API Key", type="password")
    
    st.header("📂 File")
    uploaded_accertamento = st.file_uploader("Carica Accertamento", type="pdf")
    uploaded_sentenze = st.file_uploader("Carica Sentenze Interne", type="pdf", accept_multiple_files=True)
    
    st.header("🔍 Criteri Ricerca Banca Dati")
    parole_ricerca = st.text_input("Parole da ricercare", placeholder="es. omessa allegazione atto prodromico")
    
    tipo_provv = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
    num_provv = st.text_input("Numero di provvedimento")
    anno_provv = st.selectbox("Anno", ["Tutti", "2020", "2021", "2022", "2023", "2024", "2025"])
    
    grado = st.selectbox("Grado autorità emittente", ["Tutti", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale", "Intera regione"])
    
    # Logica Condizionale Autorità
    autorita = "Tutte"
    appello = "No"
    cassazione = "No"
    
    if grado == "CGT primo grado/Provinciale":
        autorita = st.selectbox("Autorità emittente (Provincia)", PROVINCE)
        appello = st.radio("Appello", ["Si", "No"])
        cassazione = st.radio("Cassazione", ["Si", "No"])
    elif grado in ["CGT secondo grado/Regionale", "Intera regione"]:
        autorita = st.selectbox("Autorità emittente (Regione)", REGIONI)

    data_da = st.date_input("Data deposito da", value=None)
    data_a = st.date_input("Data deposito fino a", value=None)
    
    esito = st.selectbox("Esito giudizio", [
        "Tutti", "Favorevole al contribuente", "Favorevole all'ufficio", 
        "Giudizio intermedio", "Conciliazione", "Condono ed altri esiti", 
        "Esito non definitorio", "Reclamo respinto"
    ])

# --- LOGICA APPLICAZIONE ---
st.title("⚖️ Piattaforma Tributaria Professional V12")

tab1, tab2 = st.tabs(["📝 Redazione", "📅 Scadenze"])

with tab1:
    if uploaded_accertamento and gemini_key:
        client = genai.Client(api_key=gemini_key)
        acc_bytes = uploaded_accertamento.read()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔎 1. Analizza Vizi"):
                with st.spinner("Analisi..."):
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), "Estrai vizi tecnici."]
                    )
                    st.session_state['vizi'] = res.text

        with c2:
            if st.button("🌐 2. Ricerca Perplexity"):
                if not pplx_key: st.error("Inserisci API Perplexity")
                else:
                    with st.spinner("Ricerca avanzata in corso..."):
                        tema = parole_ricerca if parole_ricerca else st.session_state.get('vizi', 'Vizio motivazione')
                        query_f = f"""
                        Esegui una ricerca mirata sul portale bancadatigiurisprudenza.giustiziatributaria.gov.it con questi parametri:
                        - Parole chiave: {tema}
                        - Tipo: {tipo_provv}
                        - Anno: {anno_provv}
                        - Numero: {num_provv}
                        - Grado Autorità: {grado}
                        - Sede: {autorita}
                        - Esito desiderato: {esito}
                        - Appello/Cassazione: {appello}/{cassazione}
                        - Date: dal {data_da} al {data_a}
                        Restituisci almeno 3 sentenze con estremi e massime.
                        """
                        st.session_state['giur'] = call_perplexity(pplx_key, query_f)

        with c3:
            if st.button("✍️ 3. Genera Ricorso"):
                with st.spinner("Generazione..."):
                    giur_ext = extract_text_from_pdfs(uploaded_sentenze)
                    prompt = f"Scrivi un ricorso professionale citando i precedenti trovati: {st.session_state.get('giur', '')} e {giur_ext}"
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt]
                    )
                    st.session_state['atto'] = res.text

    # Anteprime
    if 'vizi' in st.session_state: st.info(st.session_state['vizi'])
    if 'giur' in st.session_state: st.success(st.session_state['giur'])
    if 'atto' in st.session_state: st.text_area("Ricorso:", value=st.session_state['atto'], height=400)
