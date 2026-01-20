import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - Banca Dati Ufficiale", layout="wide")

def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

def extract_text_from_pdfs(pdf_files):
    text = ""
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            for page in reader.pages:
                text += page.extract_text()
        except Exception as e:
            st.error(f"Errore nella lettura di un PDF: {e}")
    return text

st.title("⚖️ Piattaforma Tributaria - Verticale Giustizia Tributaria")
st.markdown("Ricerca giurisprudenziale focalizzata su: **bancadatigiurisprudenza.giustiziatributaria.gov.it**")

with st.sidebar:
    st.header("⚙️ Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("1. Carica Atto da Impugnare", type="pdf")
    uploaded_sentenze = st.file_uploader("2. Carica Giurisprudenza Interna", type="pdf", accept_multiple_files=True)
    st.info("La ricerca è ora limitata esclusivamente alla Banca Dati della Giustizia Tributaria.")

# Modello basato sul file 'Ricorso.pdf' fornito dall'utente
MODELLO_STUDIO = """
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [CITTA]
Oggetto: Ricorso avverso l'avviso di accertamento n. [NUMERO] per l'anno [ANNO]
Ricorrente: [DATI COMPLETI], rappresentato e difeso da [NOME DIFENSORE]
FATTO: (Analisi puntuale della vicenda e dei rilievi dell'Ufficio)
DIRITTO: (Motivi distinti da lettere a, b, c...)
P.Q.M. (Richieste di nullità, annullamento sanzioni e condanna alle spese)
Si chiede la discussione in PUBBLICA UDIENZA.
"""

# Restrizione alla sola banca dati della giustizia tributaria
BANCA_DATI_UNICA = "site:bancadatigiurisprudenza.giustiziatributaria.gov.it"

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    if uploaded_accertamento and api_key:
        client = get_gemini_client(api_key)
        acc_bytes = uploaded_accertamento.read()
        sentenze_text = extract_text_from_pdfs(uploaded_sentenze) if uploaded_sentenze else ""

        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔎 1. Analizza Vizi"):
                try:
                    with st.spinner("Analisi tecnica dell'atto..."):
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), 
                                     "Estrai i vizi tecnici e i motivi di diritto dell'accertamento allegato."]
                        )
                        st.session_state['analisi_vizi'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

        with col2:
            if st.button("📚 2. Ricerca Precedenti Tributari"):
                try:
                    with st.spinner("Ricerca su bancadatigiurisprudenza.giustiziatributaria.gov.it..."):
                        # Ricerca mirata solo sulla banca dati specifica
                        query_ricerca = f"""Utilizza solo {BANCA_DATI_UNICA}.
                        Trova sentenze delle Corti di Giustizia Tributaria relative a: {sentenze_text} e ai vizi dell'atto caricato.
                        Fornisci estremi delle sentenze e massime rilevanti."""
                        
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), query_ricerca],
                            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                        )
                        st.session_state['ricerca_legale'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

        with col3:
            if st.button("✍️ 3. Genera Atto"):
                try:
                    with st.spinner("Redazione ricorso professionale..."):
                        prompt_finale = f"""Scrivi un RICORSO seguendo il modello: {MODELLO_STUDIO}.
                        Usa i dati dell'accertamento. Integra i motivi di diritto con i precedenti trovati nella ricerca e con questi: {sentenze_text}.
                        Utilizza uno stile da avvocato tributarista, motivi contrassegnati da lettere, e citazioni giurisprudenziali precise.
                        Assicurati di includere la richiesta di Pubblica Udienza."""
                        
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_finale],
                            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                        )
                        st.session_state['atto_finale'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

    # Visualizzazione risultati
    if 'analisi_vizi' in st.session_state:
        with st.expander("🧐 Analisi Vizi", expanded=True): st.markdown(st.session_state['analisi_vizi'])
        
    if 'ricerca_legale' in st.session_state:
        with st.expander("📖 Precedenti della Giustizia Tributaria"): st.markdown(st.session_state['ricerca_legale'])

    if 'atto_finale' in st.session_state:
        st.subheader("🖋️ Anteprima Atto")
        testo_f = st.text_area("Revisiona il ricorso:", value=st.session_state['atto_finale'], height=500)
        if st.button("💾 SCARICA WORD"):
            doc = Document()
            for line in testo_f.split('\n'): doc.add_paragraph(line)
            doc.save("Ricorso_Tributario_V7.docx")
            with open("Ricorso_Tributario_V7.docx", "rb") as f:
                st.download_button("Download .docx", f, file_name="Ricorso_Tributario_V7.docx")

with tab2:
    st.subheader("📅 Scadenziario Legale")
    data_n = st.date_input("Data Notifica", datetime.now())
    scad = data_n + timedelta(days=60)
    if data_n.month <= 8 and scad.month >= 8: scad += timedelta(days=31)
    st.metric("Termine ultimo deposito ricorso", scad.strftime("%d/%m/%Y"))
