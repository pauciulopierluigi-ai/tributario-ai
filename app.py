import streamlit as st
import os
import json
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - Professionale", layout="wide")

# --- FUNZIONI CORE ---
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
st.title("⚖️ Piattaforma Tributaria AI Professionale")
st.markdown("Strumento avanzato per l'analisi dei vizi, ricerca di prassi/giurisprudenza e redazione atti complessi.")

with st.sidebar:
    st.header("⚙️ Configurazione")
    api_key = st.text_input("Inserisci API Key Google AI Studio", type="password")
    uploaded_accertamento = st.file_uploader("1. Carica Avviso di Accertamento", type="pdf")
    uploaded_sentenze = st.file_uploader("2. Carica Sentenze della tua Banca Dati", type="pdf", accept_multiple_files=True)
    st.info("Nota: L'IA utilizzerà sia i file caricati che la ricerca web (Cassazione e Circolari) per redigere l'atto.")

tab1, tab2 = st.tabs(["📝 Redazione e Anteprima", "📅 Calendario Scadenze"])

with tab1:
    if not api_key:
        st.warning("⚠️ Inserisci la tua API Key nella barra laterale per iniziare.")
    
    # Pulsanti di azione
    col1, col2, col3 = st.columns(3)
    
    if uploaded_accertamento and api_key:
        client = get_gemini_client(api_key)
        acc_bytes = uploaded_accertamento.read()
        sentenze_text = extract_text_from_pdfs(uploaded_sentenze) if uploaded_sentenze else "Nessuna sentenza specifica fornita."

        with col1:
            if st.button("🔎 1. Analizza Vizi e Criticità"):
                with st.spinner("Analisi tecnica dell'atto..."):
                    prompt_vizi = f"""Analizza questo avviso di accertamento. 
                    Estrai i dati del contribuente e individua tutti i possibili vizi di legittimità e di merito.
                    Focus su: difetto di motivazione, mancata allegazione atti richiamati, violazione Statuto Contribuente.
                    Rispondi in modo schematico ma tecnico."""
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_vizi]
                    )
                    st.session_state['analisi_vizi'] = res.text

        with col2:
            if st.button("📚 2. Cerca Norme, Prassi e Cassazione"):
                with st.spinner("Ricerca online di Circolari e Sentenze 2023-2025..."):
                    prompt_ricerca = f"""In base ai vizi rilevati nell'atto caricato, effettua una ricerca web.
                    Trova: 
                    1. Sentenze della Cassazione (2023-2025) sul difetto di motivazione e allegazione.
                    2. Circolari dell'Agenzia delle Entrate (es. Circolare 9/E o altre) sulla partecipazione del socio.
                    3. Articoli dello Statuto del Contribuente (L. 212/2000) violati.
                    Documentazione locale fornita: {sentenze_text}"""
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_ricerca],
                        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                    )
                    st.session_state['ricerca_legale'] = res.text

        with col3:
            if st.button("✍️ 3. Genera Atto Completo"):
                with st.spinner("Redazione ricorso professionale in corso..."):
                    # Prima estraiamo i dati per l'intestazione
                    res_dati = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), "Estrai JSON: contribuente, anno_imposta."]
                    )
                    dati = json.loads(res_dati.text.strip().replace('```json', '').replace('```', ''))
                    
                    prompt_atto = f"""
                    Sei un Avvocato Tributarista senior esperto in contenzioso. Redigi un RICORSO/APPELLO per {dati['contribuente']}.
                    
                    STRUTTURA OBBLIGATORIA:
                    1. INTESTAZIONE E FATTO: Dettagliato.
                    2. MOTIVI IN DIRITTO (Sviluppo esteso): Per ogni vizio (motivazione, allegazione, merito), scrivi 4-5 paragrafi tecnici.
                       - Usa formule: "Inosservanza e falsa applicazione dell'art...", "Nullità radicale per violazione del diritto di difesa".
                       - Integra la sentenza fornita: {sentenze_text}.
                       - Cita prassi amministrativa (Circolari) e giurisprudenza della Cassazione recente trovata online.
                    3. CONCLUSIONI: Chiare e perentorie.
                    4. ISTANZA DI PUBBLICA UDIENZA.

                    Stile: Accademico, aggressivo verso l'operato dell'Ufficio, estremamente formale. 
                    L'atto deve essere lungo e argomentato, non un semplice elenco.
                    """
                    res = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=[types.Part.from_bytes(data=acc_bytes, mime_type="application/pdf"), prompt_atto],
                        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                    )
                    st.session_state['bozza_testo'] = res.text

    # Visualizzazione Risultati
    if 'analisi_vizi' in st.session_state:
        with st.expander("🧐 Risultato Analisi Vizi", expanded=False):
            st.markdown(st.session_state['analisi_vizi'])
            
    if 'ricerca_legale' in st.session_state:
        with st.expander("📖 Riferimenti Normativi e Prassi trovati", expanded=False):
            st.markdown(st.session_state['ricerca_legale'])

    if 'bozza_testo' in st.session_state:
        st.subheader("🖋️ Anteprima Atto (Modificabile)")
        testo_finale = st.text_area("Revisiona il testo qui sotto:", 
                                     value=st.session_state['bozza_testo'], height=600)
        
        if st.button("💾 Esporta in Word"):
            doc = Document()
            # Impostazione margini e font base (opzionale tramite codice)
            doc.add_heading("CORTE DI GIUSTIZIA TRIBUTARIA", 0)
            for line in testo_finale.split('\n'):
                doc.add_paragraph(line)
            
            nome_file = "Ricorso_Professionale.docx"
            doc.save(nome_file)
            with open(nome_file, "rb") as f:
                st.download_button("📥 Clicca qui per scaricare il file Word", f, file_name=nome_file)

with tab2:
    st.subheader("📅 Scadenziario Legale")
    data_notifica = st.date_input("Data di ricezione atto (Notifica):", datetime.now())
    
    # Calcolo termini standard 60gg
    scadenza_60 = data_notifica + timedelta(days=60)
    
    # Gestione sospensione feriale (1-31 agosto) semplificata
    # Se il termine cade o attraversa agosto, aggiunge 31 giorni
    if data_notifica.month <= 8 and scadenza_60.month >= 8:
        scadenza_60 += timedelta(days=31)
        st.info("ℹ️ Il calcolo include la sospensione feriale dei termini (1-31 agosto).")

    st.metric("Termine ultimo deposito ricorso", scadenza_60.strftime("%d/%m/%Y"))
    
    giorni_mancanti = (scadenza_60 - datetime.now().date()).days
    if giorni_mancanti > 15:
        st.success(f"Mancano {giorni_mancanti} giorni.")
    elif 0 < giorni_mancanti <= 15:
        st.warning(f"⚠️ SCADENZA IMMINENTE: Mancano solo {giorni_mancanti} giorni!")
    else:
        st.error("❌ TERMINE SCADUTO")
