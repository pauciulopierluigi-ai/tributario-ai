import streamlit as st
import os
import json
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - Perplexity Edition", layout="wide")

# --- FUNZIONI CORE ---
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

def call_perplexity(api_key, query):
    """Funzione per interrogare Perplexity sonar per ricerca giurisprudenziale mirata"""
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro", # Modello avanzato per ricerca web
        "messages": [
            {
                "role": "system",
                "content": "Sei un assistente legale esperto in ricerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Restituisci solo sentenze reali con estremi (N., Sezione, Data) e sintesi del principio di diritto."
            },
            {"role": "user", "content": query}
        ],
        "max_tokens": 1000
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"Errore Perplexity: {response.status_code} - {response.text}"

def extract_text_from_pdfs(pdf_files):
    text = ""
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            for page in reader.pages:
                text += page.extract_text()
        except Exception as e:
            st.error(f"Errore lettura PDF: {e}")
    return text

# --- INTERFACCIA ---
st.title("⚖️ Piattaforma Tributaria Professional v10.0")
st.markdown("Ricerca intelligente su **Banca Dati Giustizia Tributaria** tramite Perplexity AI.")

with st.sidebar:
    st.header("⚙️ Configurazione API")
    gemini_key = st.text_input("API Key Gemini (Google)", type="password")
    pplx_key = st.text_input("API Key Perplexity", type="password")
    
    st.header("📄 Caricamento")
    uploaded_accertamento = st.file_uploader("Carica Atto da Impugnare", type="pdf")
    uploaded_sentenze = st.file_uploader("Carica Precedenti Interni (Opzionale)", type="pdf", accept_multiple_files=True)
    
    st.header("🎯 Filtri Ricerca Intelligente")
    grado_giudizio = st.selectbox("Grado autorità emittente", ["Tutti", "Primo Grado", "Secondo Grado"])
    esito_richiesto = st.selectbox("Esito giudizio", ["Tutti", "Favorevole al contribuente", "Parzialmente favorevole"])

MODELLO_STUDIO = """
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [CITTA]
Oggetto: Ricorso avverso l'avviso di accertamento n. [NUMERO] per l'anno [ANNO]
Ricorrente: [DATI], difeso dall'Avv. [NOME]
FATTO: (Esposizione vicenda)
DIRITTO: (Motivi a, b, c...)
P.Q.M. (Annullamento atto e spese)
Discussione in PUBBLICA UDIENZA.
"""

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    if uploaded_accertamento and gemini_key:
        client = get_gemini_client(gemini_key)
        acc_bytes = uploaded_accertamento.read()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔎 1. Analizza Vizi"):
                with st.spinner("Analisi tecnica..."):
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), 
                                 "Identifica i vizi principali dell'atto e i temi per la ricerca giurisprudenziale."]
                    )
                    st.session_state['analisi'] = res.text

        with col2:
            if st.button("🌐 2. Ricerca Perplexity"):
                if not pplx_key:
                    st.error("Inserisci la API Key di Perplexity!")
                else:
                    with st.spinner("Perplexity sta interrogando la Banca Dati Tributaria..."):
                        # Costruzione query intelligente basata sui filtri
                        temi = st.session_state.get('analisi', 'Vizi tributari')[:200]
                        query_pplx = f"""
                        Ricerca sul sito https://bancadatigiurisprudenza.giustiziatributaria.gov.it/ricerca:
                        1. Parole da ricercare: {temi}
                        2. Filtra per Grado: {grado_giudizio}
                        3. Filtra per Esito: {esito_richiesto}
                        Trova almeno 3 sentenze recenti che abbiano accolto il ricorso per motivi analoghi. 
                        Restituisci solo estremi e massime.
                        """
                        risultato_ricerca = call_perplexity(pplx_key, query_pplx)
                        st.session_state['ricerca_pplx'] = risultato_ricerca

        with col3:
            if st.button("✍️ 3. Genera Atto"):
                with st.spinner("Redazione finale..."):
                    precedenti = st.session_state.get('ricerca_pplx', "")
                    precedenti_interni = extract_text_from_pdfs(uploaded_sentenze)
                    
                    prompt = f"""Scrivi un RICORSO seguendo il modello: {MODELLO_STUDIO}.
                    Usa i dati dell'accertamento caricato.
                    Sviluppa i motivi in diritto (a, b, c) integrando questi precedenti:
                    {precedenti}
                    {precedenti_interni}
                    Cita specificamente gli estremi delle sentenze trovate per rinforzare la tesi difensiva.
                    """
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt]
                    )
                    st.session_state['atto_v10'] = res.text

    # Display dei risultati
    if 'analisi' in st.session_state:
        with st.expander("🧐 Vizi Rilevati"): st.markdown(st.session_state['analisi'])
    if 'ricerca_pplx' in st.session_state:
        with st.expander("🌐 Risultati Perplexity (Banca Dati)"): st.markdown(st.session_state['ricerca_pplx'])
    if 'atto_v10' in st.session_state:
        st.subheader("🖋️ Anteprima Ricorso")
        testo = st.text_area("Revisione:", value=st.session_state['atto_v10'], height=500)
        if st.button("💾 SCARICA WORD"):
            doc = Document()
            for l in testo.split('\n'): doc.add_paragraph(l)
            doc.save("Ricorso_V10.docx")
            with open("Ricorso_V10.docx", "rb") as f:
                st.download_button("Download", f, file_name="Ricorso_V10.docx")

with tab2:
    st.subheader("📅 Calcolo Termini")
    data_n = st.date_input("Data Notifica", datetime.now())
    scad = data_n + timedelta(days=60)
    if data_n.month <= 8 and scad.month >= 8: scad += timedelta(days=31)
    st.metric("Scadenza", scad.strftime("%d/%m/%Y"))
