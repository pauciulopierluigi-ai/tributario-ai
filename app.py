import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - Official Sources", layout="wide")

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

st.title("⚖️ Piattaforma Tributaria - Official Sources Edition")
st.markdown("Ricerca legale limitata a domini istituzionali (.gov.it, .cortecassazione.it, .parlamento.it)")

with st.sidebar:
    st.header("⚙️ Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("1. Carica Atto da Impugnare", type="pdf")
    uploaded_sentenze = st.file_uploader("2. Carica Giurisprudenza Interna", type="pdf", accept_multiple_files=True)
    st.info("La ricerca web è ora vincolata ai siti della Cassazione, AdE, MEF, Parlamento e Gazzetta Ufficiale.")

# Modello basato sul file 'Ricorso.pdf'
MODELLO_STUDIO = """
ON.LE CORTE DI GIUSTIZIA TRIBUTARIA DI [CITTA]
Oggetto: Ricorso avverso l'avviso di accertamento n. [NUMERO] per l'anno [ANNO]
Ricorrente: [DATI COMPLETI], rappresentato e difeso da [NOME DIFENSORE]
FATTO: (Analisi della vicenda e dei rilievi dell'Ufficio)
DIRITTO: (Motivi a, b, c...)
P.Q.M. (Richieste di nullità e spese)
Si chiede la discussione in PUBBLICA UDIENZA.
"""

# Stringa di restrizione domini per il prompt
DOMINI_ISTITUZIONALI = "site:cortecassazione.it OR site:agenziaentrate.gov.it OR site:gazzettaufficiale.it OR site:parlamento.it OR site:mef.gov.it"

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
                                     "Individua i vizi tecnici dell'atto caricato (es. difetto di motivazione)."]
                        )
                        st.session_state['analisi_vizi'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

        with col2:
            if st.button("📚 2. Ricerca Legale (Siti Ufficiali)"):
                try:
                    with st.spinner("Ricerca su Cassazione, AdE e MEF..."):
                        # Forziamo Gemini a usare gli operatori site: per restringere il campo
                        prompt_web = f"""Effettua una ricerca GIURIDICA su: {DOMINI_ISTITUZIONALI}.
                        Trova sentenze, circolari o leggi relative ai vizi riscontrati in questo atto.
                        Usa anche questi riferimenti interni se pertinenti: {sentenze_text}"""
                        
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
                    with st.spinner("Redazione ricorso finale..."):
                        prompt_finale = f"""Scrivi un RICORSO formale seguendo questo modello: {MODELLO_STUDIO}.
                        Integra le leggi e la prassi trovate nella ricerca legale.
                        Usa linguaggio tecnico (es. art. 7 L. 212/2000, art. 42 DPR 600/73).
                        Cita i principi di diritto delle sentenze caricate ({sentenze_text}) senza copiarle."""
                        
                        res = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_finale],
                            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                        )
                        st.session_state['atto_finale'] = res.text
                except Exception as e: st.error(f"Errore: {e}")

    # Visualizzazione risultati
    if 'analisi_vizi' in st.session_state:
        with st.expander("🧐 Analisi Tecnica"): st.markdown(st.session_state['analisi_vizi'])
        
    if 'ricerca_legale' in st.session_state:
        with st.expander("📖 Fonti Istituzionali Trovate"): st.markdown(st.session_state['ricerca_legale'])

    if 'atto_finale' in st.session_state:
        st.subheader("🖋️ Anteprima Atto (Revisionabile)")
        testo_f = st.text_area("Revisiona:", value=st.session_state['atto_finale'], height=500)
        if st.button("💾 SCARICA WORD"):
            doc = Document()
            for line in testo_f.split('\n'): doc.add_paragraph(line)
            doc.save("Ricorso_Istituzionale.docx")
            with open("Ricorso_Istituzionale.docx", "rb") as f:
                st.download_button("Download .docx", f, file_name="Ricorso_Istituzionale.docx")

with tab2:
    st.subheader("📅 Scadenziario Legale")
    data_n = st.date_input("Data Notifica", datetime.now())
    scad = data_n + timedelta(days=60)
    if data_n.month <= 8 and scad.month >= 8: scad += timedelta(days=31)
    st.metric("Termine ultimo (incl. Sosp. Feriale)", scad.strftime("%d/%m/%Y"))
