import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - Professional v3", layout="wide")

def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)

def extract_text_from_pdfs(pdf_files):
    text = ""
    for pdf in pdf_files:
        reader = PdfReader(pdf)
        for page in reader.pages:
            text += page.extract_text()
    return text

st.title("⚖️ Piattaforma Tributaria Professional v3.0")
st.markdown("Generatore di atti basato sul Modello Standard dello Studio.")

with st.sidebar:
    st.header("⚙️ Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("1. Carica Atto da Impugnare", type="pdf")
    uploaded_sentenze = st.file_uploader("2. Carica Sentenze (Banca Dati)", type="pdf", accept_multiple_files=True)

# Testo del modello standard (estratto dal tuo PDF) per guidare l'IA
MODELLO_STUDIO = """
STRUTTURA OBBLIGATORIA (Copia questo stile):
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [Città]
Oggetto: Ricorso avverso l'avviso di accertamento n. [Numero] per l'anno [Anno]
Ricorrente: [Dati Contribuente], rappresentato e difeso dall'Avv. [Nome], con domicilio eletto presso...
Contro: Agenzia delle Entrate Direzione Provinciale di [Città]
FATTO: (Riassunto della vicenda)
DIRITTO: (Motivi contrassegnati da lettere: a, b, c...)
P.Q.M. Si chiede alla On.le Corte adita: la nullità dell'atto... la condanna alle spese...
Si chiede la discussione in pubblica udienza.
"""

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    if uploaded_accertamento and api_key:
        client = get_gemini_client(api_key)
        acc_bytes = uploaded_accertamento.read()
        sentenze_text = extract_text_from_pdfs(uploaded_sentenze) if uploaded_sentenze else ""

        if st.button("🚀 GENERA ATTO SECONDO MODELLO STUDIO"):
            with st.spinner("Redazione atto professionale in corso..."):
                prompt_atto = f"""
                Sei un Avvocato Tributarista. Devi redigere un RICORSO seguendo ESATTAMENTE lo stile e la struttura del modello qui sotto.
                
                MODELLO DA IMITARE:
                {MODELLO_STUDIO}
                
                DATI PER IL NUOVO ATTO (Dall'accertamento allegato):
                - Analizza il PDF dell'accertamento per nomi, date, cifre e motivi dell'ufficio.
                
                GIURISPRUDENZA DA INTEGRARE:
                {sentenze_text}
                
                ISTRUZIONI CRITICHE:
                1. USA LE LETTERE (a, b, c...) per i motivi di diritto.
                2. SVILUPPA I MOTIVI: Se l'ufficio non ha allegato atti richiamati, usa la giurisprudenza fornita per scrivere 3-4 paragrafi densi di riferimenti normativi (Art. 7 L. 212/2000).
                3. P.Q.M.: Usa le formule esatte del modello.
                4. NON COPIARE LA SENTENZA: Usa la sentenza solo per estrarre il 'principio di diritto' da inserire nel capitolo DIRITTO.
                """
                
                res = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_atto],
                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.session_state['atto_v3'] = res.text

    if 'atto_v3' in st.session_state:
        st.subheader("🖋️ Anteprima Atto (Modello Studio)")
        testo_revisionato = st.text_area("Modifica il testo:", value=st.session_state['atto_v3'], height=600)
        
        if st.button("📥 SCARICA WORD"):
            doc = Document()
            for p in testo_revisionato.split('\n'):
                doc.add_paragraph(p)
            doc.save("Ricorso_Studio.docx")
            with open("Ricorso_Studio.docx", "rb") as f:
                st.download_button("Download .docx", f, file_name="Ricorso_Studio.docx")

with tab2:
    st.subheader("📅 Calcolo Termini")
    data_notifica = st.date_input("Data Notifica", datetime.now())
    scadenza = data_notifica + timedelta(days=60)
    if data_notifica.month <= 8 and scadenza.month >= 8: scadenza += timedelta(days=31)
    st.metric("Scadenza Ricorso", scadenza.strftime("%d/%m/%Y"))
