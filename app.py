import streamlit as st
import google.generativeai as genai
import requests
import json
import pypdf
import io
from typing import List, Dict

# ==============================================================================
# 1. CONFIGURAZIONE PAGINA E CSS (UI/UX MODERN)
# ==============================================================================
st.set_page_config(
    page_title="Studio Tributario AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS per Design "LexisNexis" / SaaS Professionale
st.markdown("""
<style>
    /* Importazione Font (opzionale, ma consigliato per look professionale) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* 1. MAIN BACKGROUND */
    .stApp {
        background-color: #f8fafc; /* Light Slate Gray */
    }

    /* 2. SIDEBAR STYLING */
    [data-testid="stSidebar"] {
        background-color: #1a365d; /* Navy Blue */
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #ffffff !important;
    }

    /* 3. FILE UPLOADER FIX (CRITICAL) */
    [data-testid="stSidebar"] .stFileUploader section {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 10px;
    }
    /* Testo del file caricato (dentro il box bianco) deve essere SCURO */
    [data-testid="stSidebar"] .stFileUploader section div {
        color: #0c1a30 !important; 
        font-weight: 700;
    }
    /* Bottone 'Browse files' */
    [data-testid="stSidebar"] .stFileUploader button {
        color: #0c1a30 !important;
        border-color: #0c1a30 !important;
    }

    /* 4. CARDS (Container Risultati) */
    .legal-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border-top: 4px solid #c0a060; /* Gold */
    }
    .legal-card h3 {
        color: #1a365d;
        font-weight: 700;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
    }
    .legal-card p, .legal-card li {
        color: #2d3748; /* Slate Grey */
        line-height: 1.6;
    }

    /* 5. BUTTONS */
    .stButton > button {
        background-color: #1a365d;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background-color: #c0a060; /* Gold hover */
        color: #1a365d;
    }

    /* Input Fields Styling */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 6px;
        border: 1px solid #cbd5e0;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTIONE STATO E FUNZIONI UTILITY
# ==============================================================================

# Inizializzazione Session State
if 'vizi' not in st.session_state:
    st.session_state['vizi'] = None
if 'ricerca_results' not in st.session_state:
    st.session_state['ricerca_results'] = []
if 'pdf_text' not in st.session_state:
    st.session_state['pdf_text'] = ""
if 'sentenze_offline_text' not in st.session_state:
    st.session_state['sentenze_offline_text'] = ""

def extract_text_from_pdf(uploaded_file):
    """Estrae testo da un PDF caricato."""
    if uploaded_file is None:
        return ""
    try:
        pdf_reader = pypdf.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        st.error(f"Errore lettura PDF: {e}")
        return ""

def call_gemini(prompt, api_key, model_name="gemini-2.0-flash"):
    """Wrapper per chiamate a Google Gemini."""
    if not api_key:
        st.error("Inserisci la Gemini API Key nella sidebar.")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Errore API Gemini: {e}")
        return None

def call_perplexity(messages, api_key):
    """
    Chiama l'API di Perplexity (sonar-pro).
    Accetta una lista di messaggi per gestire la history.
    """
    if not api_key:
        st.error("Inserisci la Perplexity API Key nella sidebar.")
        return None
    
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": messages,
        "temperature": 0.1
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Errore API Perplexity: {e}")
        return None

# ==============================================================================
# 3. SIDEBAR: CONFIGURAZIONE & UPLOAD
# ==============================================================================

with st.sidebar:
    st.title("⚖️ Studio Tributario AI")
    st.markdown("---")
    
    st.header("🔑 Credenziali API")
    gemini_key = st.text_input("Gemini API Key", type="password")
    perplexity_key = st.text_input("Perplexity API Key", type="password")
    
    st.markdown("---")
    st.header("📂 Documenti")
    
    # Upload Accertamento
    uploaded_accertamento = st.file_uploader("Accertamento (PDF)", type=["pdf"], key="accertamento")
    if uploaded_accertamento:
        st.session_state['pdf_text'] = extract_text_from_pdf(uploaded_accertamento)
        st.success(f"Caricato: {uploaded_accertamento.name}")
        
    # Upload Sentenze Offline
    uploaded_sentenze = st.file_uploader("Sentenze Offline (PDF)", type=["pdf"], accept_multiple_files=True, key="sentenze")
    if uploaded_sentenze:
        full_text = ""
        for f in uploaded_sentenze:
            full_text += extract_text_from_pdf(f) + "\n---\n"
        st.session_state['sentenze_offline_text'] = full_text
        st.success(f"{len(uploaded_sentenze)} file caricati.")

# ==============================================================================
# 4. NAVIGAZIONE PRINCIPALE
# ==============================================================================

# Simulazione Navigation Bar tramite Sidebar Radio (più pulito per Single File)
page = st.sidebar.radio("Navigazione", ["Analisi Vizi", "Ricerca Banca Dati", "Redazione Atto"])

# --- PAGINA 1: ANALISI VIZI ---
if page == "Analisi Vizi":
    st.title("🔍 Analisi Vizi dell'Atto")
    st.markdown("Analisi automatica di vizi formali e sostanziali tramite Gemini 2.0 Flash.")
    
    if not st.session_state['pdf_text']:
        st.info("Carica un file PDF di accertamento nella sidebar per iniziare.")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("ESEGUI ANALISI", use_container_width=True):
                with st.spinner("Analisi giuridica in corso..."):
                    prompt_analisi = f"""
                    Agisci come un esperto Avvocato Tributarista Italiano.
                    Analizza il seguente testo estratto da un Atto di Accertamento o Cartella Esattoriale.
                    
                    Estrai un elenco dettagliato di potenziali VIZI (Formali e Sostanziali) che possono essere motivo di ricorso.
                    Per ogni vizio:
                    1. Dai un titolo tecnico (es. "Difetto di Motivazione", "Decadenza dei termini").
                    2. Spiega brevemente perché è applicabile in questo caso specifico basandoti sul testo.
                    3. Cita i riferimenti normativi (Tuir, Statuto del Contribuente, ecc.).
                    
                    Sii tecnico, preciso e professionale.
                    
                    TESTO ATTO:
                    {st.session_state['pdf_text'][:30000]} 
                    """ 
                    # Truncate to avoid token limits if massive PDF, though Flash handles huge context
                    
                    vizi_result = call_gemini(prompt_analisi, gemini_key)
                    if vizi_result:
                        st.session_state['vizi'] = vizi_result

        with col2:
            if st.session_state['vizi']:
                st.markdown(f"""
                <div class="legal-card">
                    <h3>📄 Esito Analisi Vizi</h3>
                    {st.session_state['vizi']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="legal-card">
                    <h3>In attesa di analisi</h3>
                    <p>Premi il pulsante per avviare l'intelligenza artificiale.</p>
                </div>
                """, unsafe_allow_html=True)

# --- PAGINA 2: RICERCA BANCA DATI ---
elif page == "Ricerca Banca Dati":
    st.title("📚 Ricerca Giurisprudenza Sequenziale")
    st.markdown("Simulazione di ricerca sul portale *bancadatigiurisprudenza.giustiziatributaria.gov.it*.")
    
    # Layout Filtri
    col_k, col_t, col_y = st.columns(3)
    with col_k:
        keywords = st.text_input("Parole Chiave", placeholder="es. inesistenza notifica pec")
    with col_t:
        tipo_atto = st.selectbox("Tipo Atto", ["Tutti", "Sentenza", "Ordinanza"])
    with col_y:
        anno = st.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])
        
    # Sezione Avanzata
    grade, location, outcome = None, None, None
    if tipo_atto == "Sentenza":
        st.markdown("### ⚙️ Filtri Avanzati")
        c1, c2, c3 = st.columns(3)
        with c1:
            grade = st.selectbox("Grado di Giudizio", ["CGT 1° Grado", "CGT 2° Grado", "Cassazione"])
        with c2:
            # Logica dinamica semplificata per demo
            if grade == "CGT 1° Grado":
                location = st.selectbox("Sede", ["Milano", "Roma", "Napoli", "Torino", "Bari"])
            elif grade == "CGT 2° Grado":
                location = st.selectbox("Regione", ["Lombardia", "Lazio", "Campania", "Piemonte", "Puglia"])
            else:
                location = st.text_input("Sezione", placeholder="es. Trib o V")
        with c3:
            outcome = st.selectbox("Esito", ["Favorevole al Contribuente", "Favorevole Ufficio", "Parziale accoglimento"])

    if st.button("AVVIA RICERCA SEQUENZIALE"):
        result_container = st.empty()
        full_analysis = ""
        
        # LOGICA CORE SEQUENZIALE (CHAIN OF THOUGHT)
        messages = [
            {"role": "system", "content": "Sei un assistente legale esperto che sa navigare e cercare nel portale bancadatigiurisprudenza.giustiziatributaria.gov.it. Devi simulare le azioni di ricerca e riportare i risultati."}
        ]
        
        # STEP 1: Ricerca Base
        with st.status("Esecuzione Ricerca...", expanded=True) as status:
            st.write("🔹 Passo 1: Accesso al portale e ricerca keyword...")
            prompt_1 = f"Vai sul sito bancadatigiurisprudenza.giustiziatributaria.gov.it. Inserisci la keyword '{keywords}'. Clicca Cerca. Leggi il numero esatto accanto all'etichetta 'Risultati di ricerca'. Riporta SOLO quel numero."
            messages.append({"role": "user", "content": prompt_1})
            res_1 = call_perplexity(messages, perplexity_key)
            messages.append({"role": "assistant", "content": res_1 or "Nessun risultato"})
            st.write(f"**Risultati Grezzi:** {res_1}")
            
            # STEP 2: Filtri Temporali e Tipo
            if anno != "Seleziona" or tipo_atto != "Tutti":
                st.write(f"🔹 Passo 2: Applicazione filtri (Anno: {anno}, Tipo: {tipo_atto})...")
                prompt_2 = f"Ora affina la ricerca. Imposta Anno='{anno}' e Tipo Atto='{tipo_atto}'. Clicca Cerca di nuovo. Leggi il numero aggiornato di documenti trovati."
                messages.append({"role": "user", "content": prompt_2})
                res_2 = call_perplexity(messages, perplexity_key)
                messages.append({"role": "assistant", "content": res_2 or "Errore"})
                st.write(f"**Risultati Filtrati:** {res_2}")
            
            # STEP 3: Filtri Avanzati (se attivi)
            if tipo_atto == "Sentenza" and grade:
                st.write(f"🔹 Passo 3: Filtri Avanzati ({grade} - {location} - {outcome})...")
                prompt_3 = f"Affina ulteriormente. Imposta Grado='{grade}', Sede='{location}'. Cerca specificamente sentenze con esito '{outcome}'. Quante ne rimangono?"
                messages.append({"role": "user", "content": prompt_3})
                res_3 = call_perplexity(messages, perplexity_key)
                messages.append({"role": "assistant", "content": res_3 or "Errore"})
                st.write(f"**Risultati Finali:** {res_3}")

            # STEP 4: Analisi Contenuto
            st.write("🔹 Passo 4: Lettura ed Estrazione Massime...")
            prompt_4 = f"Apri le anteprime delle sentenze rimaste (o delle prime 5 più rilevanti). Analizzale legalmente. Sono utili per una difesa basata su '{keywords}'? Estrai la Ratio Decidendi e gli estremi delle sentenze."
            messages.append({"role": "user", "content": prompt_4})
            final_analysis = call_perplexity(messages, perplexity_key)
            status.update(label="Ricerca Completata", state="complete", expanded=False)
        
        # Visualizzazione Risultato
        if final_analysis:
            st.session_state['ricerca_results'] = final_analysis
            st.markdown(f"""
            <div class="legal-card">
                <h3>⚖️ Massimario e Giurisprudenza Rilevata</h3>
                {final_analysis}
            </div>
            """, unsafe_allow_html=True)

# --- PAGINA 3: REDAZIONE ATTO ---
elif page == "Redazione Atto":
    st.title("✍️ Redazione Ricorso Tributario")
    
    col_input, col_preview = st.columns([1, 1])
    
    with col_input:
        st.info("Il sistema utilizzerà i Vizi estratti e la Giurisprudenza trovata per redigere l'atto.")
        st.markdown("### Dati disponibili:")
        st.write(f"- **Testo Atto**: {'✅ Presente' if st.session_state['pdf_text'] else '❌ Mancante'}")
        st.write(f"- **Vizi Rilevati**: {'✅ Presenti' if st.session_state['vizi'] else '❌ Mancanti'}")
        st.write(f"- **Giurisprudenza Online**: {'✅ Presente' if st.session_state['ricerca_results'] else '❌ Mancante'}")
        st.write(f"- **Giurisprudenza Offline**: {'✅ Presente' if st.session_state['sentenze_offline_text'] else '⚠️ Non caricata'}")
        
        cgt_intestazione = st.text_input("Intestazione Corte (es. CGT I Grado di Milano)", value="Corte di Giustizia Tributaria di I Grado di [CITTÀ]")
        
        if st.button("GENERA RICORSO", use_container_width=True):
            if not st.session_state['vizi']:
                st.error("Esegui prima l'analisi dei vizi (Pagina 1).")
            else:
                with st.spinner("Redazione atto in corso..."):
                    context_material = f"""
                    VIZI RILEVATI:
                    {st.session_state['vizi']}
                    
                    GIURISPRUDENZA TROVATA (Online):
                    {st.session_state['ricerca_results']}
                    
                    GIURISPRUDENZA CARICATA (Offline):
                    {st.session_state['sentenze_offline_text'][:10000]}
                    """
                    
                    prompt_redazione = f"""
                    Sei un Avvocato Tributarista Senior. Redigi un RICORSO TRIBUTARIO formale per la {cgt_intestazione}.
                    
                    Struttura Obbligatoria:
                    1. INTESTAZIONE: Corte, Ricorrente (Dati fittizi [NOME]), Resistente (Agenzia Entrate/Riscossione).
                    2. FATTO: Riassumi brevemente che è stato notificato l'atto (usa i dati dall'analisi vizi se presenti).
                    3. DIRITTO: Sviluppa i motivi di ricorso basandoti sui VIZI forniti.
                       - Usa lettere minuscole per i punti (a, b, c).
                       - Per ogni motivo, argomenta in diritto e cita la GIURISPRUDENZA fornita nel contesto.
                       - Sii perentorio e persuasivo.
                    4. P.Q.M.: Conclusioni (Annullamento atto, vittoria spese).
                    
                    CONTESTO GIURIDICO DA USARE:
                    {context_material}
                    """
                    
                    draft = call_gemini(prompt_redazione, gemini_key)
                    if draft:
                        st.session_state['draft_ricorso'] = draft

    with col_preview:
        if 'draft_ricorso' in st.session_state and st.session_state['draft_ricorso']:
            st.markdown("### 📄 Anteprima Atto")
            st.text_area("Bozza Modificabile", value=st.session_state['draft_ricorso'], height=600)
            st.download_button("Scarica .txt", st.session_state['draft_ricorso'], "ricorso_bozza.txt")
        else:
            st.markdown("""
            <div class="legal-card" style="text-align: center; color: #aaa;">
                <br><br>L'atto generato apparirà qui.<br><br><br>
            </div>
            """, unsafe_allow_html=True)
