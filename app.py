import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
import chromadb
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI", layout="wide")

# --- FUNZIONI CORE (Adattate per il Web) ---
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

def extract_text_from_pdfs(pdf_files):
    text = ""
    for pdf in pdf_files:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text()
    return text

# --- INTERFACCIA UTENTE ---
st.title("⚖️ Piattaforma Tributaria AI")
st.markdown("Analisi accertamenti, ricerca giurisprudenziale e redazione atti.")

with st.sidebar:
    st.header("Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("Carica Avviso di Accertamento", type="pdf")
    uploaded_sentenze = st.file_uploader("Carica Sentenze di Riferimento", type="pdf", accept_multiple_files=True)

tab1, tab2 = st.tabs(["📝 Redazione e Anteprima", "📅 Calendario Scadenze"])

with tab1:
    if st.button("Genera Bozza Ricorso"):
        if not api_key or not uploaded_accertamento:
            st.error("Inserisci l'API Key e carica l'avviso!")
        else:
            with st.spinner("L'IA sta lavorando..."):
                client = get_gemini_client(api_key)
                
                # Fase 1: Analisi
                acc_bytes = uploaded_accertamento.read()
                res = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), 
                             "Analizza ed estrai JSON: contribuente, anno_imposta, motivi_principali."]
                )
                dati = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
                
                # Fase 2: Redazione con Ricerca Web
                sentenze_text = extract_text_from_pdfs(uploaded_sentenze) if uploaded_sentenze else ""
                prompt_f = f"Sei un avvocato. Scrivi un ricorso per {dati['contribuente']}. Motivi: {dati['motivi_principali']}. Sentenze fornite: {sentenze_text}. Cerca online precedenti 2024-2025."
                
                ricorso = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt_f,
                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.session_state['bozza_testo'] = ricorso.text

    if 'bozza_testo' in st.session_state:
        # ANTEPRIMA E MODIFICA
        testo_finale = st.text_area("Modifica il testo prima di generare il Word:", 
                                     value=st.session_state['bozza_testo'], height=500)
        
        if st.button("Scarica Documento Word"):
            doc = Document()
            doc.add_heading("RICORSO TRIBUTARIO", 0)
            doc.add_paragraph(testo_finale)
            doc.save("Ricorso_Finale.docx")
            with open("Ricorso_Finale.docx", "rb") as f:
                st.download_button("Clicca qui per scaricare", f, file_name="Ricorso_Finale.docx")

with tab2:
    st.subheader("Calcolo Scadenze")
    data_notifica = st.date_input("Data di notifica dell'avviso", datetime.now())
    scadenza_60 = data_notifica + timedelta(days=60)
    
    col1, col2 = st.columns(2)
    col1.metric("Termine 60 giorni", scadenza_60.strftime("%d/%m/%Y"))
    
    giorni_rimanenti = (scadenza_60 - datetime.now().date()).days
    if giorni_rimanenti > 0:
        col2.warning(f"Mancano {giorni_rimanenti} giorni alla scadenza.")
    else:
        col2.error("Scadenza superata!")
