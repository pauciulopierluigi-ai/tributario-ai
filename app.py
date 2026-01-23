import streamlit as st
import requests
from google import genai
from google.genai import types
from pypdf import PdfReader
from io import BytesIO
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# =========================
# CONFIGURAZIONE APP
# =========================

st.set_page_config(page_title="Studio Tributario AI - V22.0", layout="wide")

st.markdown("""
    <style>
    :root { --primary: #1a365d; --accent: #c0a060; }
    .main { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: var(--primary) !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stFileUploader section div { color: #1a365d !important; font-weight: 600; }
    [data-testid="stSidebar"] .stFileUploader button p { color: #1a365d !important; }
    [data-testid="stSidebar"] .stFileUploader button { border: 1px solid #1a365d !important; background-color: #f0f2f6 !important; }
    [data-testid="stSidebar"] input, [data-testid="stSidebar"] select { color: black !important; background-color: white !important; }
    .legal-card { background: white; padding: 25px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border-top: 4px solid var(--accent); margin-bottom: 2rem; color: #2d3748; }
    .stButton>button { border-radius: 10px; height: 3.5em; background-color: var(--primary); color: white; font-weight: 700; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# =========================
# COSTANTI E LISTE
# =========================

PROVINCE = [
    "Seleziona", "Agrigento", "Alessandria", "Ancona", "Aosta", "L'Aquila", "Arezzo",
    "Ascoli Piceno", "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno",
    "Benevento", "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi",
    "Cagliari", "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro",
    "Chieti", "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo",
    "Ferrara", "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia",
    "Grosseto", "Imperia", "Isernia", "La Spezia", "Latina", "Lecce", "Lecco",
    "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", "Matera",
    "Messina", "Milano", "Modena", "Monza e della Brianza", "Napoli", "Novara",
    "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia",
    "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone",
    "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia",
    "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena",
    "Siracusa", "Sondrio", "Taranto", "Teramo", "Terni", "Torino", "Trapani",
    "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia",
    "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza",
    "Viterbo"
]

REGIONI = [
    "Seleziona", "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise",
    "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige",
    "Umbria", "Valle d'Aosta", "Veneto"
]

# =========================
# DATA MODEL (IN-MEMORIA)
# =========================

@dataclass
class TaxCase:
    id: int
    created_at: datetime
    updated_at: datetime
    titolo: str
    codice_fiscale: Optional[str] = None
    partita_iva: Optional[str] = None
    numero_avviso: Optional[str] = None
    anno_imposta: Optional[int] = None
    importo_accertato: Optional[float] = None
    stato: str = "bozza"

if "cases" not in st.session_state:
    st.session_state["cases"]: List[TaxCase] = []
if "current_case_id" not in st.session_state:
    st.session_state["current_case_id"] = None

def create_case_from_extracted_data(extracted: dict) -> TaxCase:
    new_id = len(st.session_state["cases"]) + 1
    now = datetime.utcnow()
    titolo = f"Ricorso {new_id} - {extracted.get('numero_avviso', 'Senza numero')}"
    case = TaxCase(
        id=new_id,
        created_at=now,
        updated_at=now,
        titolo=titolo,
        codice_fiscale=extracted.get("codice_fiscale"),
        partita_iva=extracted.get("partita_iva"),
        numero_avviso=extracted.get("numero_avviso"),
        importo_accertato=None,
        stato="bozza"
    )
    st.session_state["cases"].append(case)
    st.session_state["current_case_id"] = case.id
    return case

def get_current_case() -> Optional[TaxCase]:
    cid = st.session_state.get("current_case_id")
    if not cid:
        return None
    for c in st.session_state["cases"]:
        if c.id == cid:
            return c
    return None

# =========================
# OCR + PARSING
# =========================

CF_REGEX = r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]"
PIVA_REGEX = r"P\.?\s*IVA[:\s]*(\d{11})"
AVVISO_NUM_REGEX = r"(avviso\s+di\s+accertamento\s+n\.?\s*([\w\/\-]+))"
IMPORTO_REGEX = r"([\d\.\']+,\d{2})\s*€?"

def ocr_pdf_to_text(pdf_bytes: bytes, lang: str = "ita") -> str:
    images = convert_from_bytes(pdf_bytes)
    all_text = []
    for img in images:
        text = pytesseract.image_to_string(img, lang=lang)
        all_text.append(text)
    return "\n".join(all_text)

def extract_tax_data(text: str) -> dict:
    data = {}
    cf_match = re.search(CF_REGEX, text)
    if cf_match:
        data["codice_fiscale"] = cf_match.group(0)
    piva_match = re.search(PIVA_REGEX, text, flags=re.IGNORECASE)
    if piva_match:
        data["partita_iva"] = piva_match.group(1)
    avv_match = re.search(AVVISO_NUM_REGEX, text, flags=re.IGNORECASE)
    if avv_match:
        data["numero_avviso"] = avv_match.group(2)
    imp_match = re.search(IMPORTO_REGEX, text)
    if imp_match:
        data["importo"] = imp_match.group(1)
    return data

# =========================
# PERPLEXITY WRAPPER
# =========================

def call_perplexity(api_key, query, system_prompt, retries=2, timeout=60):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "temperature": 0.1
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"ok": True, "content": content, "raw": data}
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                continue
            return {"ok": False, "content": "", "error": str(e)}

# =========================
# PAGINA 1 - ANALISI VIZI
# =========================

def pagina_analisi():
    st.markdown("<h1>🔎 1. Analisi Vizi</h1>", unsafe_allow_html=True)
    if not st.session_state.get("gemini_key"):
        st.warning("Configura Gemini Key.")
        return
    if "f_atto" in st.session_state:
        if st.button("ESEGUI ANALISI VIZI"):
            client = genai.Client(api_key=st.session_state["gemini_key"])
            res = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    types.Part.from_bytes(data=st.session_state["f_atto"], mime_type="application/pdf"),
                    "Estrai vizi tecnici e sostanziali dell'atto, in forma sintetica e strutturata."
                ]
            )
            st.session_state["vizi"] = res.text
        if "vizi" in st.session_state:
            st.markdown(f'<div class="legal-card">{st.session_state["vizi"]}</div>', unsafe_allow_html=True)
    else:
        st.info("Carica un avviso di accertamento (PDF) nella sidebar.")

# =========================
# PAGINA 2 - RICERCA BANCA DATI
# =========================

def pagina_ricerca():
    st.markdown("<h1>🌐 2. Ricerca Strategica Banca Dati</h1>", unsafe_allow_html=True)
    if not st.session_state.get("pplx_key"):
        st.warning("Configura Perplexity Key.")
        return

    st.subheader("1. Censimento sentenze e ordinanze")
    with st.container():
        st.markdown('<div class="legal-card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        default_keywords = st.session_state.get("vizi", "")[:120]
        with c1:
            s_parole = st.text_input("Parole da ricercare", value=default_keywords)
        with c2:
            s_tipo = st.selectbox("Tipo provvedimento", ["Tutti", "Sentenza", "Ordinanza di rinvio/remissione"])
        with c3:
            s_anno = st.selectbox("Anno", ["Seleziona", "2025", "2024", "2023", "2022", "2021", "2020"])

        fase1_disabled = not s_parole.strip()
        if st.button("AVVIA FASE 1: CENSIMENTO", disabled=fase1_disabled):
            with st.spinner("Navigazione web attiva su Giustizia Tributaria..."):
                sys = (
                    "Sei un analista esperto di giurisprudenza tributaria. "
                    "Devi usare la funzione di ricerca sul sito bancadatigiurisprudenza.giustiziatributaria.gov.it. "
                    "Non inventare sentenze o dati numerici inesistenti. "
                    "Se non puoi fornire numeri precisi, fornisci solo una valutazione qualitativa in forma sintetica."
                )
                q = (
                    f"Esegui ricerca su bancadatigiurisprudenza.giustiziatributaria.gov.it "
                    f"per '{s_parole}'. Tipo: {s_tipo}, Anno: {s_anno}. "
                    "Fornisci una sintesi dei risultati, elencando alcuni casi rappresentativi con riferimento (numero/anno, CGT, esito)."
                )
                res = call_perplexity(st.session_state["pplx_key"], q, sys)
                if res["ok"]:
                    st.session_state["fase1_res"] = res["content"]
                else:
                    st.error(f"Errore Perplexity: {res['error']}")
        st.markdown('</div>', unsafe_allow_html=True)

    if "fase1_res" in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Sintesi Censimento</h3>{st.session_state["fase1_res"]}</div>', unsafe_allow_html=True)

        st.subheader("2. Ricerca avanzata e Analisi di utilità")
        with st.container():
            st.markdown('<div class="legal-card">', unsafe_allow_html=True)
            a1, a2 = st.columns(2)
            with a1:
                s_grado = st.selectbox("Grado autorità emittente", ["Seleziona", "CGT primo grado/Provinciale", "CGT secondo grado/Regionale", "Intera regione"])
            with a2:
                lista_sede = PROVINCE if s_grado == "CGT primo grado/Provinciale" else (REGIONI if s_grado in ["CGT secondo grado/Regionale", "Intera regione"] else ["Seleziona"])
                s_sede = st.selectbox("Autorità emittente", lista_sede)

            b1, b2 = st.columns(2)
            with b1:
                s_app = st.selectbox("Appello", ["Seleziona", "Si", "No"]) if s_grado == "CGT primo grado/Provinciale" else "Seleziona"
            with b2:
                s_cass = st.selectbox("Cassazione", ["Seleziona", "Si", "No"])

            d1, d2 = st.columns(2)
            with d1:
                s_esito = st.selectbox("Esito giudizio", ["Seleziona", "Favorevole al contribuente", "Favorevole all'ufficio", "Tutti", "Conciliazione", "Condono"])
            with d2:
                s_spese = st.selectbox("Spese Giudizio", ["Seleziona", "Compensate", "A carico del contribuente", "A carico dell'ufficio"])

            fase2_disabled = (s_grado == "Seleziona") or (s_sede == "Seleziona")
            if st.button("AVVIA FASE 2: ANALISI DETTAGLIATA", disabled=fase2_disabled):
                with st.spinner("Analisi giuridica dei precedenti..."):
                    base_context = st.session_state.get("fase1_res", "")[:2000]
                    sys = (
                        "Sei un Avvocato Tributarista esperto. "
                        "Devi usare il sito bancadatigiurisprudenza.giustiziatributaria.gov.it per individuare sentenze rilevanti. "
                        "Non inventare mai riferimenti o numeri di sentenza; riporta solo ciò che è plausibile dalla banca dati. "
                        "Se i criteri sono troppo stretti, suggerisci varianti di ricerca (parole chiave alternative, anni contigui)."
                    )
                    q = (
                        f"Considera questo quadro riassuntivo: '''{base_context}'''. "
                        f"Cerca ora sentenze con parametri: Parole '{s_parole}', Grado {s_grado}, Sede {s_sede}, Esito {s_esito}. "
                        "Elenca alcuni precedenti con riferimento (numero/anno, CGT, breve massima) e spiega sinteticamente la loro utilità nel contrastare l'avviso."
                    )
                    res = call_perplexity(st.session_state["pplx_key"], q, sys)
                    if res["ok"]:
                        st.session_state["giur"] = res["content"]
                    else:
                        st.error(f"Errore Perplexity: {res['error']}")
            st.markdown('</div>', unsafe_allow_html=True)

    if "giur" in st.session_state:
        st.markdown(f'<div class="legal-card"><h3>Analisi Giuridica Sentenze</h3>{st.session_state["giur"]}</div>', unsafe_allow_html=True)

# =========================
# PAGINA 3 - REDAZIONE ATTO
# =========================

def pagina_redazione():
    st.markdown("<h1>✍️ 3. Redazione Atto</h1>", unsafe_allow_html=True)
    if not st.session_state.get("gemini_key"):
        st.warning("Configura Gemini Key.")
        return
    if "vizi" not in st.session_state:
        st.info("Esegui prima l'analisi dei vizi (pagina 1).")
        return
    if "f_atto" not in st.session_state:
        st.info("Carica l'avviso di accertamento (PDF) nella sidebar.")
        return

    if st.button("GENERA RICORSO FINALE"):
        client = genai.Client(api_key=st.session_state["gemini_key"])
        giur_riassunto = st.session_state.get("giur", "")[:4000]
        prompt = (
            "Redigi un ricorso tributario strutturato in sezioni FATTO / DIRITTO / PQM, "
            f"utilizzando i seguenti vizi: {st.session_state['vizi']} "
            f"e la seguente analisi di giurisprudenza: {giur_riassunto}. "
            "Il ricorso deve essere coerente con il contesto italiano e con le CGT."
        )
        res = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Part.from_bytes(data=st.session_state["f_atto"], mime_type="application/pdf"),
                prompt
            ]
        )
        st.session_state["atto"] = res.text

    if "atto" in st.session_state:
        st.text_area("Bozza Generata:", value=st.session_state["atto"], height=500)

# =========================
# SIDEBAR
# =========================

with st.sidebar:
    st.markdown("<h2>Configurazione</h2>", unsafe_allow_html=True)
    st.session_state["gemini_key"] = st.text_input("Gemini Key", type="password")
    st.session_state["pplx_key"] = st.text_input("Perplexity Key", type="password")
    st.markdown("---")
    f_acc = st.file_uploader("Accertamento (PDF)", type="pdf")
    if f_acc:
        pdf_bytes = f_acc.getvalue()
        st.session_state["f_atto"] = pdf_bytes

        if st.button("Esegui OCR avviso"):
            with st.spinner("OCR in corso..."):
                ocr_text = ocr_pdf_to_text(pdf_bytes, lang="ita")
                st.session_state["ocr_text"] = ocr_text
                extracted = extract_tax_data(ocr_text)
                st.session_state["tax_data"] = extracted
                create_case_from_extracted_data(extracted)
            st.success("OCR completato e dati fiscali estratti (ove possibile).")

        if "tax_data" in st.session_state:
            st.markdown("**Dati fiscali estratti (bozza):**")
            td = st.session_state["tax_data"]
            st.write(f"Codice Fiscale: {td.get('codice_fiscale', 'N/D')}")
            st.write(f"Partita IVA: {td.get('partita_iva', 'N/D')}")
            st.write(f"Numero Avviso: {td.get('numero_avviso', 'N/D')}")
            st.write(f"Importo (grezzo): {td.get('importo', 'N/D')}")

    f_pre = st.file_uploader("Sentenze Offline", type="pdf", accept_multiple_files=True)
    if f_pre:
        st.session_state["f_sentenze"] = [f.getvalue() for f in f_pre]

    st.markdown("---")
    current_case = get_current_case()
    if current_case:
        st.markdown("**Pratica corrente:**")
        st.write(current_case.titolo)
        st.write(f"CF: {current_case.codice_fiscale or 'N/D'}")
        st.write(f"P.IVA: {current_case.partita_iva or 'N/D'}")

# =========================
# NAVIGAZIONE
# =========================

pg = st.navigation([
    st.Page(pagina_analisi, title="1. Analisi Vizi", icon="🔎"),
    st.Page(pagina_ricerca, title="2. Banca Dati", icon="🌐"),
    st.Page(pagina_redazione, title="3. Redazione Atto", icon="✍️")
])
pg.run()
