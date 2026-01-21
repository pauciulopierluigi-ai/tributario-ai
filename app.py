import streamlit as st
import os
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - Ultra Search V11", layout="wide")

# --- FUNZIONI DI RICERCA ---

def call_perplexity(api_key, query):
    """Interroga Perplexity per simulare la ricerca sulla Banca Dati Tributaria"""
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system", 
                "content": "Sei un assistente legale esperto. Il tuo compito è cercare sentenze esclusivamente sul sito https://bancadatigiurisprudenza.giustiziatributaria.gov.it/. Restituisci estremi (n. sentenza, sezione, data) e la massima."
            },
            {"role": "user", "content": query}
        ]
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Errore nella ricerca Perplexity: {e}"

def extract_text_from_pdfs(pdf_files):
    text = ""
    for pdf in pdf_files:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text()
    return text

# --- INTERFACCIA UTENTE ---

st.title("⚖️ Piattaforma Tributaria Professional v11.0")
st.markdown("Integrazione Perplexity per ricerca su Banca Dati Giustizia Tributaria.")

with st.sidebar:
    st.header("⚙️ Configurazione Chiavi")
    gemini_key = st.text_input("1. API Key Gemini (Google)", type="password")
    pplx_key = st.text_input("2. API Key Perplexity", type="password")
    
    st.header("📄 Caricamento")
    uploaded_accertamento = st.file_uploader("Carica Atto (PDF)", type="pdf")
    uploaded_sentenze = st.file_uploader("Carica Sentenze Interne (PDF)", type="pdf", accept_multiple_files=True)
    
    st.header("🎯 Filtri Ricerca")
    grado_giudizio = st.selectbox("Grado autorità emittente", ["Tutti", "Primo Grado (CGT I)", "Secondo Grado (CGT II)"])
    esito_richiesto = st.selectbox("Esito giudizio", ["Tutti", "Favorevole al contribuente", "Parzialmente favorevole"])

MODELLO_STUDIO = """
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [CITTA]
Oggetto: Ricorso avverso l'avviso di accertamento n. [NUMERO] per l'anno [ANNO]
FATTO: (Analisi vicenda)
DIRITTO: (Motivi a, b, c...)
P.Q.M. (Richieste e Pubblica Udienza)
"""

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    if uploaded_accertamento and gemini_key:
        client = genai.Client(api_key=gemini_key)
        acc_bytes = uploaded_accertamento.read()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔎 1. Analizza Atto"):
                with st.spinner("Analisi in corso..."):
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), 
                                 "Estrai i vizi principali dell'atto per la ricerca giurisprudenziale."]
                    )
                    st.session_state['analisi'] = res.text

        with col2:
            if st.button("🌐 2. Ricerca Precedenti"):
                if not pplx_key:
                    st.warning("Inserisci la chiave Perplexity a sinistra!")
                else:
                    with st.spinner("Perplexity sta cercando sulla Banca Dati..."):
                        tema = st.session_state.get('analisi', 'Vizi motivazione tributaria')
                        query_intelligente = f"""
                        Cerca nel portale https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca:
                        - Parole da ricercare: {tema[:150]}
                        - Grado autorità: {grado_giudizio}
                        - Esito: {esito_richiesto}
                        Trova 3 sentenze favorevoli al contribuente. Fornisci estremi e massime.
                        """
                        st.session_state['ricerca_pplx'] = call_perplexity(pplx_key, query_intelligente)

        with col3:
            if st.button("✍️ 3. Genera Atto"):
                with st.spinner("Generazione ricorso..."):
                    precedenti = st.session_state.get('ricerca_pplx', "")
                    prompt = f"Scrivi un ricorso basato sul modello {MODELLO_STUDIO} usando l'atto caricato e questi precedenti: {precedenti}"
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt]
                    )
                    st.session_state['atto_finale'] = res.text

    # Risultati
    if 'analisi' in st.session_state:
        st.info(st.session_state['analisi'])
    if 'ricerca_pplx' in st.session_state:
        st.success(st.session_state['ricerca_pplx'])
    if 'atto_finale' in st.session_state:
        st.text_area("Bozza:", value=st.session_state['atto_finale'], height=400)
