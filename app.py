import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario Professional v4", layout="wide")

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

st.title("⚖️ Piattaforma Tributaria Professional v4.0")
st.markdown("Redazione atti secondo lo stile consolidato dello Studio.")

with st.sidebar:
    st.header("⚙️ Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("1. Carica Atto da Impugnare", type="pdf")
    uploaded_sentenze = st.file_uploader("2. Carica Giurisprudenza (Banca Dati)", type="pdf", accept_multiple_files=True)
    st.info("Nota: Questa versione forza l'IA a citare i precedenti senza copiarli.")

# Definizione del modello basato sul PDF 'Ricorso.pdf' dell'utente
MODELLO_STUDIO = """
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [CITTA]
Oggetto: Ricorso avverso l'avviso di accertamento n. [NUMERO] per l'anno [ANNO]
Ricorrente: [DATI ANAGRAFICI COMPLETI], rappresentato e difeso da [NOME DIFENSORE]
Contro: Agenzia delle Entrate - Direzione Provinciale di [CITTA]
FATTO:
(Riassumere qui la contabilità periodica, l'accertamento induttivo e i rilievi dell'Ufficio)
DIRITTO:
a) Errata indicazione della competenza territoriale (se applicabile);
b) Violazione e falsa applicazione dell'art. 7 Legge 212/2000 (Statuto del Contribuente) per difetto di motivazione e allegazione;
c) Illegittimità delle sanzioni irrogate (indicare i punti specifici);
d) [Ulteriori motivi tecnici basati sui file caricati].
P.Q.M.
Si chiede alla On.le Corte adita:
- La nullità degli avvisi di accertamento impugnati;
- L'annullamento delle sanzioni;
- La condanna dell'Agenzia alle spese di giudizio.
Si chiede la discussione in PUBBLICA UDIENZA.
"""

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    if uploaded_accertamento and api_key:
        if st.button("🚀 GENERA ATTO PROFESSIONALE"):
            try:
                with st.spinner("L'IA sta elaborando l'atto secondo il modello dello studio..."):
                    client = get_gemini_client(api_key)
                    acc_bytes = uploaded_accertamento.read()
                    sentenze_text = extract_text_from_pdfs(uploaded_sentenze) if uploaded_sentenze else ""

                    prompt_professionale = f"""
                    Sei un Avvocato Tributarista esperto. Devi redigere un RICORSO formale seguendo ESATTAMENTE lo stile del modello fornito.
                    
                    SCHEMA DA IMITARE:
                    {MODELLO_STUDIO}
                    
                    DATI DEL CASO ATTUALE:
                    - Analizza il PDF caricato per estrarre il nome del ricorrente, l'avviso di accertamento e i motivi dell'Agenzia.
                    
                    GIURISPRUDENZA DA CITARE (NON COPIARE):
                    {sentenze_text}
                    
                    REGOLE TASSATIVE:
                    1. SVILUPPA I MOTIVI IN DIRITTO: Non fare elenchi puntati. Ogni motivo deve essere un paragrafo argomentato.
                    2. CITA I PRECEDENTI: Usa la giurisprudenza fornita (es. Sentenza CGT Campania 16/2024) per rafforzare i motivi a), b) o c).
                    3. NON FARE COPIA-INCOLLA: Se il testo somiglia troppo a una sentenza caricata, riscrivilo in forma di atto difensivo.
                    4. LINGUAGGIO: Usa termini tecnici come 'inderogabilità della competenza', 'motivazione per relationem', 'onere della prova'.
                    """
                    
                    # Generazione contenuto
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[
                            types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), 
                            prompt_professionale
                        ],
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    st.session_state['atto_professionale'] = res.text
            except Exception as e:
                st.error(f"Si è verificato un errore durante la generazione: {e}")

    if 'atto_professionale' in st.session_state:
        st.subheader("🖋️ Anteprima Atto (Revisionato)")
        testo_revisionato = st.text_area("Revisiona il testo qui sotto:", value=st.session_state['atto_professionale'], height=600)
        
        if st.button("💾 ESPORTA WORD"):
            doc = Document()
            for line in testo_revisionato.split('\n'):
                doc.add_paragraph(line)
            doc.save("Ricorso_Studio_V4.docx")
            with open("Ricorso_Studio_V4.docx", "rb") as f:
                st.download_button("Scarica .docx", f, file_name="Ricorso_Studio_V4.docx")

with tab2:
    st.subheader("📅 Calcolo Termini Tributari")
    data_notifica = st.date_input("Data Notifica dell'Atto", datetime.now())
    scadenza = data_notifica + timedelta(days=60)
    # Calcolo sospensione feriale
    if data_notifica.month <= 8 and scadenza.month >= 8:
        scadenza += timedelta(days=31)
    st.metric("Termine ultimo (incl. Sosp. Feriale)", scadenza.strftime("%d/%m/%Y"))
