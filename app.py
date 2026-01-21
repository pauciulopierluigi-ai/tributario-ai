import streamlit as st
import os
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document
from datetime import datetime, timedelta

st.set_page_config(page_title="Studio Tributario AI - V13", layout="wide")

# --- DATABASE LISTE ---
PROVINCE = ["Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo", "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera", "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara", "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", "Viterbo"]
REGIONI = ["Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna", "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"]

# --- FUNZIONI ---
def call_perplexity(api_key, query):
    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "Sei un esperto legale. Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it. Restituisci sentenze con estremi e massime."},
            {"role": "user", "content": query}
        ]
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content']
    except: return "Errore nella ricerca."

def extract_text(files):
    t = ""
    for f in files:
        r = PdfReader(f)
        for p in r.pages: t += p.extract_text()
    return t

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Configurazione")
    gemini_key = st.text_input("API Key Gemini", type="password")
    pplx_key = st.text_input("API Key Perplexity", type="password")
    
    st.header("📂 Caricamento")
    f_atto = st.file_uploader("Atto da impugnare", type="pdf")
    f_giur = st.file_uploader("Sentenze interne", type="pdf", accept_multiple_files=True)
    
    st.header("🔍 Ricerca Banca Dati")
    s_parole = st.text_input("Parole da ricercare")
    s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza"])
    s_anno = st.selectbox("Anno", ["Tutti", "2025", "2024", "2023", "2022", "2021", "2020"])
    
    s_grado = st.selectbox("Grado autorità", ["Tutti", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale"])
    
    # Logica Condizionale Autorità
    s_autorita = "Tutte"
    s_appello = "No"
    s_cassazione = "No"
    
    if s_grado == "CGT primo grado/Provinciale":
        s_autorita = st.selectbox("Provincia", PROVINCE)
        s_appello = st.radio("Appello", ["Si", "No"])
        s_cassazione = st.radio("Cassazione", ["Si", "No"])
    elif s_grado == "CGT secondo grado/Regionale":
        s_autorita = st.selectbox("Regione", REGIONI)

    s_da = st.date_input("Data da", value=None)
    s_a = st.date_input("Data a", value=None)
    s_esito = st.selectbox("Esito", ["Tutti", "Favorevole al contribuente", "Favorevole all'ufficio", "Giudizio intermedio"])

# --- MAIN ---
st.title("⚖️ Piattaforma Tributaria Professional")

tab1, tab2 = st.tabs(["📝 Redazione Atto", "📅 Scadenziario"])

with tab1:
    # Qui appaiono i 3 pulsanti
    c1, c2, c3 = st.columns(3)
    
    if f_atto and gemini_key:
        client = genai.Client(api_key=gemini_key)
        
        with c1:
            if st.button("🔎 1. Analizza Atto"):
                with st.spinner("Analisi..."):
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=f_atto.read(), mime_type="application/pdf"), "Analizza vizi tecnici."])
                    st.session_state['vizi'] = res.text
                    f_atto.seek(0) # Reset file pointer

        with c2:
            if st.button("🌐 2. Ricerca Perplexity"):
                if not pplx_key: st.error("Manca chiave Perplexity")
                else:
                    with st.spinner("Ricerca..."):
                        q = f"Cerca su bancadatigiurisprudenza.giustiziatributaria.gov.it: {s_parole}. Grado: {s_grado}, Sede: {s_autorita}, Esito: {s_esito}, Date: {s_da}-{s_a}."
                        st.session_state['giur'] = call_perplexity(pplx_key, q)

        with c3:
            if st.button("✍️ 3. Genera Ricorso"):
                with st.spinner("Generazione..."):
                    txt_giur = extract_text(f_giur) if f_giur else ""
                    prompt = f"Scrivi un ricorso professionale usando i vizi: {st.session_state.get('vizi','')} e i precedenti: {st.session_state.get('giur','')} e {txt_giur}."
                    res = client.models.generate_content(model="gemini-2.0-flash", contents=[types.Part.from_bytes(data=f_atto.read(), mime_type="application/pdf"), prompt])
                    st.session_state['atto'] = res.text
                    f_atto.seek(0)

    # Visualizzazione risultati
    if 'vizi' in st.session_state: st.info(st.session_state['vizi'])
    if 'giur' in st.session_state: st.success(st.session_state['giur'])
    if 'atto' in st.session_state: 
        st.subheader("Atto Finale")
        st.text_area("Bozza:", value=st.session_state['atto'], height=500)

with tab2:
    d_not = st.date_input("Data Notifica", datetime.now())
    scad = d_not + timedelta(days=60)
    if d_not.month <= 8 and scad.month >= 8: scad += timedelta(days=31)
    st.metric("Scadenza deposito", scad.strftime("%d/%m/%Y"))
