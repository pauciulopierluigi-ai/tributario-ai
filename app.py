import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario Professional v5", layout="wide")

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

st.title("⚖️ Piattaforma Tributaria Professional v5.0")
st.markdown("Analisi vizi, ricerca giurisprudenziale e redazione secondo il modello dello Studio.")

with st.sidebar:
    st.header("⚙️ Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("1. Carica Atto da Impugnare", type="pdf")
    uploaded_sentenze = st.file_uploader("2. Carica Giurisprudenza (Banca Dati)", type="pdf", accept_multiple_files=True)
    st.info("Piano Pay-as-you-go attivo: Nessun limite di generazione.")

# Modello basato sul file 'Ricorso.pdf'
MODELLO_STUDIO = """
STRUTTURA DA IMITARE:
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [CITTA]
Oggetto: Ricorso avverso l'avviso di accertamento n. [NUMERO] per l'anno [ANNO]
Ricorrente: [DATI COMPLETI], rappresentato e difeso da [NOME DIFENSORE]
FATTO: (Analisi puntuale della vicenda e dei rilievi dell'Ufficio)
DIRITTO: (Motivi distinti da lettere a, b, c...)
P.Q.M. (Richieste di nullità e condanna alle spese)
Si chiede la discussione in PUBBLICA UDIENZA.
"""

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    if uploaded_accertamento and api_key:
        client = get_gemini_client(api_key)
        acc_bytes = uploaded_accertamento.read()
        sentenze_text = extract_text_from_pdfs(uploaded_sentenze) if uploaded_sentenze else ""

        # RIPRISTINO DEI TRE TASTI
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔎 1. Analizza Vizi"):
                try:
                    with st.spinner("Analisi vizi in corso..."):
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), 
                                     "Individua i vizi di legittimità (motivazione, allegazione, competenza) e di merito nell'atto. Sii tecnico."]
                        )
                        st.session_state['analisi_vizi'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

        with col2:
            if st.button("📚 2. Ricerca Legale"):
                try:
                    with st.spinner("Ricerca online Cassazione e Circolari..."):
                        prompt_web = f"Cerca sentenze Cassazione 2023-2025 e Circolari AdE sul caso analizzato. Usa anche questi precedenti: {sentenze_text}"
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_web],
                            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                        )
                        st.session_state['ricerca_legale'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

        with col3:
            if st.button("✍️ 3. Genera Atto"):
                try:
                    with st.spinner("Redazione atto finale..."):
                        prompt_finale = f"""
                        Redigi un RICORSO formale seguendo lo stile del MODELLO STUDIO:
                        {MODELLO_STUDIO}
                        
                        Usa i dati del PDF caricato e integra i principi di diritto di queste sentenze: {sentenze_text}.
                        Sviluppa i motivi in diritto con lettere (a, b, c) e linguaggio tecnico (es. motivazione per relationem).
                        NON COPIARE LE SENTENZE, usale come citazione a supporto.
                        """
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_finale],
                            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                        )
                        st.session_state['atto_finale'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

    # Visualizzazione risultati
    if 'analisi_vizi' in st.session_state:
        st.info("### 🧐 Analisi Vizi Rilevati")
        st.markdown(st.session_state['analisi_vizi'])
        
    if 'ricerca_legale' in st.session_state:
        st.success("### 📖 Riferimenti Normativi e Giurisprudenza")
        st.markdown(st.session_state['ricerca_legale'])

    if 'atto_finale' in st.session_state:
        st.subheader("🖋️ Anteprima Ricorso (Modificabile)")
        testo_f = st.text_area("Revisiona:", value=st.session_state['atto_finale'], height=500)
        
        if st.button("💾 SCARICA WORD"):
            doc = Document()
            for line in testo_f.split('\n'): doc.add_paragraph(line)
            doc.save("Ricorso_V5.docx")
            with open("Ricorso_V5.docx", "rb") as f:
                st.download_button("Download .docx", f, file_name="Ricorso_V5.docx")

with tab2:
    st.subheader("📅 Scadenziario")
    data_n = st.date_input("Data Notifica", datetime.now())
    scad = data_n + timedelta(days=60)
    if data_n.month <= 8 and scad.month >= 8: scad += timedelta(days=31)
    st.metric("Termine ultimo deposito", scad.strftime("%d/%m/%Y"))
