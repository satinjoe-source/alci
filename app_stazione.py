import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from PIL import Image
import time

# Tentativo di importazione pyzbar
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

st.set_page_config(page_title="A.L.C.I. Stazione", page_icon="🏭", layout="centered")

# --- CONNESSIONE SUPABASE ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase = init_supabase()

if not supabase:
    st.error("❌ Errore di connessione a Supabase. Controlla i secrets.")
    st.stop()

def format_number(n):
    return f"{n:,}".replace(",", ".")

# --- CSS STYLES ---
st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    
    /* FIX VISIBILITÀ INPUT E SELECTBOX */
    .stSelectbox div[data-baseweb="select"] > div, 
    .stTextInput input, 
    .stTextArea textarea {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important;
        border-radius: 8px !important;
    }

    .main-container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .header-box { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; border-left: 4px solid #2563eb; }
    .header-box h1 { margin: 0; font-size: 24px; color: #1e293b; font-weight: 600; }
    .header-box p { margin: 4px 0 0; color: #64748b; font-size: 14px; }
    .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
    .stat-label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; font-weight: 600; }
    .stat-value { font-size: 32px; font-weight: 700; color: #1e293b; }
    .action-box { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 16px; }
    .success-alert { background: #f0fdf4; border: 1px solid #86efac; border-left: 4px solid #22c55e; padding: 16px; border-radius: 8px; margin: 16px 0; }
    .success-alert h3 { color: #15803d; margin: 0 0 8px; font-size: 16px; }
    .error-alert { background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444; padding: 16px; border-radius: 8px; margin: 16px 0; }
    .warning-alert { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 8px; margin: 16px 0; }
    .stButton>button { width: 100%; border-radius: 8px; padding: 12px 24px; font-weight: 600; font-size: 15px; }
</style>
""", unsafe_allow_html=True)

if "stazione_logged" not in st.session_state:
    st.session_state.stazione_logged = None

# --- LOGIN SCREEN ---
if not st.session_state.stazione_logged:
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    
    # LOGO CENTRATO NEL LOGIN
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try:
            st.image("logo alci.jpg", width=150)
        except: pass

    st.markdown("""
        <div class='header-box' style='text-align:center'>
            <h1>🏭 A.L.C.I. - Attivazione</h1>
            <p>Sistema lavaggio cisterne</p>
        </div>
    """, unsafe_allow_html=True)
    
    try:
        stazioni_resp = supabase.table("stazioni").select("stazione_id, ragione_sociale, password").eq("attiva", True).execute()
        stazioni = pd.DataFrame(stazioni_resp.data)
    except:
        stazioni = pd.DataFrame()
    
    if stazioni.empty:
        st.error("❌ Nessuna stazione disponibile.")
        st.stop()
    
    st.markdown("<div class='action-box'>", unsafe_allow_html=True)
    sel = st.selectbox(
        "Seleziona la tua stazione",
        stazioni["stazione_id"].tolist(),
        format_func=lambda x: stazioni[stazioni["stazione_id"]==x]["ragione_sociale"].values[0]
    )
    pwd = st.text_input("Password", type="password")
    
    if st.button("🔓 Accedi", type="primary"):
        selected_staz = stazioni[stazioni["stazione_id"]==sel].iloc[0]
        db_pwd = selected_staz.get("password")
        valid_pwd = db_pwd if db_pwd else "lavaggio123"
        
        if pwd == valid_pwd:
            st.session_state.stazione_logged = sel
            st.rerun()
        else:
            st.error("❌ Password errata")
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

# --- MAIN APP ---
try:
    staz_resp = supabase.table("stazioni").select("*").eq("stazione_id", st.session_state.stazione_logged).execute()
    if not staz_resp.data:
        raise Exception("Stazione non trovata")
    staz = staz_resp.data[0]
except:
    st.session_state.stazione_logged = None
    st.rerun()

st.markdown("<div class='main-container'>", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    # LOGO E TITOLO STAZIONE
    c_logo, c_text = st.columns([0.8, 3.2])
    with c_logo:
        try:
            st.image("logo alci.jpg", width=80)
        except: pass
    with c_text:
        st.markdown(f"""
            <div class='header-box' style='margin-bottom:0; padding:15px'>
                <h1 style='font-size:20px'>🏭 {staz['ragione_sociale']}</h1>
                <p>{staz['citta']}</p>
            </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Esci"):
        st.session_state.stazione_logged = None
        st.rerun()

# --- STATISTICHE ---
try:
    tot = supabase.table("certificati").select("*", count="exact", head=True).eq("stazione_id", staz['stazione_id']).execute().count
    att = supabase.table("certificati").select("*", count="exact", head=True).eq("stazione_id", staz['stazione_id']).eq("stato", "ATTIVO").execute().count
    disponibili = tot - att
except:
    tot, att, disponibili = 0, 0, 0

st.markdown(f"""
    <div class='stats-grid'>
        <div class='stat-card'>
            <div class='stat-label'>Totale Assegnati</div>
            <div class='stat-value'>{format_number(tot)}</div>
        </div>
        <div class='stat-card'>
            <div class='stat-label'>Disponibili</div>
            <div class='stat-value' style='color:#2563eb'>{format_number(disponibili)}</div>
        </div>
        <div class='stat-card'>
            <div class='stat-label'>Attivati</div>
            <div class='stat-value' style='color:#22c55e'>{format_number(att)}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("<div class='action-box'>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📸 Scansiona QR", "🔢 Inserisci Codice", "📋 Storico"])

def verifica_e_mostra_cert(code):
    resp = supabase.table("certificati").select("*").eq("code", code).execute()
    if not resp.data:
        st.markdown(f"<div class='error-alert'><h3>❌ Certificato non trovato</h3><p>Codice: <strong>{code}</strong></p></div>", unsafe_allow_html=True)
        return None
    
    cert = resp.data[0]
    
    if cert["stazione_id"] != staz["stazione_id"]:
        st.markdown(f"<div class='error-alert'><h3>❌ Certificato non valido qui</h3><p>Assegnato a: <strong>{cert['stazione_id']}</strong></p></div>", unsafe_allow_html=True)
        return None
        
    if cert["stato"] == "ATTIVO":
        st.markdown(f"<div class='warning-alert'><h3>⚠️ Già attivato</h3><p>Targa: {cert['targa']}</p></div>", unsafe_allow_html=True)
        return None
        
    return cert

def attiva_certificato(code, targa, note):
    try:
        supabase.table("certificati").update({
            "stato": "ATTIVO",
            "data_uso": datetime.now().isoformat(),
            "targa": targa.upper().strip() if targa else None,
            "note": note or None
        }).eq("code", code).execute()
        return True
    except Exception as e:
        st.error(f"Errore DB: {e}")
        return False

# --- LOGICA DI SCANSIONE QR (Solo FILE) ---
def processa_immagine_qr(img_file):
    if not img_file: return
    
    image = Image.open(img_file)
    decoded = pyzbar.decode(image)
    
    if decoded:
        qr_data = decoded[0].data.decode('utf-8')
        if "?c=" in qr_data:
            code = qr_data.split("?c=")[1].split("&")[0]
            cert = verifica_e_mostra_cert(code)
            
            if cert:
                st.markdown(f"<div class='success-alert'><h3>✅ Rilevato: {cert['code']}</h3></div>", unsafe_allow_html=True)
                with st.form(f"attiva_qr_{cert['code']}"):
                    targa = st.text_input("🚛 Targa", max_chars=12)
                    note = st.text_area("Note", max_chars=200)
                    if st.form_submit_button("🔓 ATTIVA ORA", type="primary"):
                        if attiva_certificato(cert['code'], targa, note):
                            st.success(f"✅ Attivato!")
                            time.sleep(1)
                            st.rerun()
        else:
            st.error("QR Code non valido per A.L.C.I.")
    else:
        st.warning("Nessun QR code rilevato nella foto.")

with tab1:
    st.markdown("### Scansiona il QR Code")
    st.info("Carica una foto del QR code presente sul certificato.")
    
    if not PYZBAR_AVAILABLE:
        st.error("""
        ❌ **Libreria di sistema mancante.**
        Per far funzionare il lettore QR su Streamlit Cloud:
        1. Crea un file chiamato `packages.txt`
        2. Scrivici dentro: `libzbar0`
        3. Riavvia l'app.
        """)
    else:
        uploaded_file = st.file_uploader("📸 Carica foto QR", type=["jpg","png","jpeg"], key="qr_up")
        if uploaded_file:
            st.image(uploaded_file, width=200)
            processa_immagine_qr(uploaded_file)

with tab2:
    st.markdown("### Inserimento Manuale")
    if "cert_manual" not in st.session_state:
        st.session_state.cert_manual = None
        
    code_input = st.text_input("Codice Certificato", key="manual_code")
    if st.button("🔍 Cerca"):
        if code_input:
            st.session_state.cert_manual = verifica_e_mostra_cert(code_input.strip().upper())
            
    if st.session_state.cert_manual:
        cert = st.session_state.cert_manual
        st.markdown(f"<div class='success-alert'><h3>✅ Pronto per attivazione: {cert['code']}</h3></div>", unsafe_allow_html=True)
        with st.form("attiva_man"):
            targa = st.text_input("🚛 Targa", max_chars=12)
            note = st.text_area("Note", max_chars=200)
            if st.form_submit_button("🔓 ATTIVA", type="primary"):
                if attiva_certificato(cert['code'], targa, note):
                    st.success("✅ Fatto!")
                    st.session_state.cert_manual = None
                    time.sleep(1)
                    st.rerun()

with tab3:
    st.markdown("### Ultimi 50 attivati")
    try:
        resp = supabase.table("certificati")\
            .select("code, targa, data_uso, note")\
            .eq("stazione_id", staz['stazione_id'])\
            .eq("stato", "ATTIVO")\
            .order("data_uso", desc=True)\
            .limit(50)\
            .execute()
        
        df = pd.DataFrame(resp.data)
        if not df.empty:
            df['data_uso'] = pd.to_datetime(df['data_uso']).dt.strftime('%d/%m/%Y %H:%M')
            df = df[["code", "targa", "data_uso", "note"]]
            df.columns = ["Codice", "Targa", "Data", "Note"]
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuno storico disponibile")
    except:
        st.info("Errore caricamento storico")

st.markdown("</div></div>", unsafe_allow_html=True)
