import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps
import time
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
import numpy as np

# --- IMPORTAZIONE MOTORI DI LETTURA ---
# 1. Pyzbar (Principale)
try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

# 2. OpenCV (Riserva/Potenziato)
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

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
    st.error("❌ Errore connessione Supabase.")
    st.stop()

def format_number(n):
    return f"{n:,}".replace(",", ".")

# --- CSS STYLES ---
st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    .stSelectbox div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea {
        background-color: #ffffff !important; border: 1px solid #cbd5e1 !important; color: #1e293b !important; border-radius: 8px !important;
    }
    .main-container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .header-box { background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; border-left: 4px solid #2563eb; }
    .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center; }
    .stat-value { font-size: 32px; font-weight: 700; color: #1e293b; }
    .stat-label { font-size: 12px; color: #64748b; font-weight: 600; text-transform: uppercase; }
    .success-alert { background: #f0fdf4; border: 1px solid #86efac; border-left: 4px solid #22c55e; padding: 16px; border-radius: 8px; margin: 16px 0; }
    .error-alert { background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444; padding: 16px; border-radius: 8px; margin: 16px 0; }
    .warning-alert { background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 8px; margin: 16px 0; }
    .gps-ok { color: #16a34a; font-weight: bold; font-size: 14px; }
    .gps-ko { color: #dc2626; font-weight: bold; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

if "stazione_logged" not in st.session_state:
    st.session_state.stazione_logged = None

# --- LOGIN SCREEN ---
if not st.session_state.stazione_logged:
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try: st.image("logo alci.jpg", width=150)
        except: pass

    st.markdown("""
        <div class='header-box' style='text-align:center'>
            <h1>🏭 A.L.C.I. - Attivazione</h1>
            <p>Sistema lavaggio cisterne</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='background: white; padding: 24px; border-radius: 12px;'>", unsafe_allow_html=True)
    email_input = st.text_input("Email Utente")
    pwd_input = st.text_input("Password", type="password")
    
    if st.button("🔓 Accedi", type="primary"):
        if email_input and pwd_input:
            try:
                response = supabase.table("stazioni").select("*").eq("email", email_input.strip()).eq("attiva", True).execute()
                if response.data:
                    found_stazione = response.data[0]
                    db_pwd = found_stazione.get("password", "lavaggio123")
                    if pwd_input == db_pwd:
                        st.session_state.stazione_logged = found_stazione["stazione_id"]
                        st.success(f"Benvenuto {found_stazione['ragione_sociale']}!")
                        time.sleep(0.5)
                        st.rerun()
                    else: st.error("❌ Password errata")
                else: st.error("❌ Email non trovata o stazione non attiva")
            except Exception as e: st.error(f"Errore: {e}")
        else: st.warning("Inserisci credenziali")
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

# --- RECUPERO DATI STAZIONE ---
try:
    staz_resp = supabase.table("stazioni").select("*").eq("stazione_id", st.session_state.stazione_logged).execute()
    staz = staz_resp.data[0]
except:
    st.session_state.stazione_logged = None
    st.rerun()

# --- GPS CHECK ---
loc = get_geolocation() 
gps_status = "WAITING" 
distanza_mt = 0

if loc:
    try:
        user_coords = (loc['coords']['latitude'], loc['coords']['longitude'])
        station_coords = (staz['gps_lat'], staz['gps_lon'])
        
        if station_coords[0] and station_coords[1]:
            distanza_mt = geodesic(user_coords, station_coords).meters
            limit = staz.get('raggio_attivazione', 200) 
            
            if distanza_mt <= limit:
                gps_status = "OK"
            else:
                gps_status = "ERROR"
        else:
            gps_status = "OK" 
            distanza_mt = 0
    except:
        gps_status = "WAITING"

# --- UI PRINCIPALE ---
st.markdown("<div class='main-container'>", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    c_logo, c_text = st.columns([0.8, 3.2])
    with c_logo:
        try: st.image("logo alci.jpg", width=80)
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

# --- BOX GPS ---
if gps_status == "OK":
    st.markdown(f"<div class='gps-ok'>📍 GPS OK (Distanza: {int(distanza_mt)}m)</div>", unsafe_allow_html=True)
elif gps_status == "ERROR":
    st.markdown(f"<div class='gps-ko'>⛔ POSIZIONE ERRATA (Distanza: {int(distanza_mt)}m). Impossibile attivare.</div>", unsafe_allow_html=True)
else:
    st.warning("📡 In attesa del GPS... (Assicurati di aver dato i permessi)")

# --- STATISTICHE ---
try:
    tot = supabase.table("certificati").select("*", count="exact", head=True).eq("stazione_id", staz['stazione_id']).execute().count
    att = supabase.table("certificati").select("*", count="exact", head=True).eq("stazione_id", staz['stazione_id']).eq("stato", "ATTIVO").execute().count
    disponibili = tot - att
except: tot, att, disponibili = 0, 0, 0

st.markdown(f"""
    <div class='stats-grid'>
        <div class='stat-card'><div class='stat-label'>Disponibili</div><div class='stat-value' style='color:#2563eb'>{format_number(disponibili)}</div></div>
        <div class='stat-card'><div class='stat-label'>Attivati</div><div class='stat-value' style='color:#22c55e'>{format_number(att)}</div></div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📸 Scansiona QR", "🔢 Manuale"])

# --- FUNZIONI DI SUPPORTO ---
def verifica_e_mostra_cert(code):
    try:
        resp = supabase.table("certificati").select("*").eq("code", code).execute()
        if not resp.data:
            st.error(f"❌ Certificato {code} non trovato")
            return None
        cert = resp.data[0]
        if cert["stazione_id"] != staz["stazione_id"]:
            st.error(f"❌ Certificato assegnato ad altra stazione ({cert['stazione_id']})")
            return None
        if cert["stato"] == "ATTIVO":
            st.warning(f"⚠️ Già attivato! Targa: {cert['targa']}")
            return None
        return cert
    except Exception as e:
        st.error(f"Errore ricerca: {e}")
        return None

def attiva_certificato(code, targa, note):
    if gps_status == "ERROR":
        st.error("⛔ Attivazione bloccata: Sei troppo lontano.")
        try:
            supabase.table("anomalie").insert({
                "stazione_id": staz['stazione_id'],
                "tipo": "GPS_DISTANZA",
                "messaggio": f"Tentativo attivazione {code} a {int(distanza_mt)}m di distanza",
                "gps_rilevato": str(loc['coords']) if loc else "N/A"
            }).execute()
        except: pass
        return False

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

# --- MOTORE DI DECODIFICA AVANZATO ---
def decodifica_robusta(image_file):
    """
    Tenta di leggere il QR code applicando diverse trasformazioni
    """
    try:
        # Carica immagine
        img_original = Image.open(image_file)
        
        # 1. RIDIMENSIONAMENTO (Se enorme, riduci per pyzbar)
        if img_original.width > 2000:
            img_original = img_original.resize((int(img_original.width/2), int(img_original.height/2)))
        
        # LISTA DI IMMAGINI DA PROVARE
        attempts = [
            ("Originale", img_original),
            ("Scala di Grigi", img_original.convert('L')),
            ("Contrasto Alto", ImageEnhance.Contrast(img_original.convert('L')).enhance(2.0)),
            ("Bianco/Nero", img_original.convert('L').point(lambda p: 255 if p > 128 else 0))
        ]

        # TENTATIVO 1: PYZBAR (Loop sui filtri)
        if PYZBAR_AVAILABLE:
            for name, img_variant in attempts:
                decoded = pyzbar.decode(img_variant)
                if decoded:
                    data = decoded[0].data.decode('utf-8')
                    # st.success(f"Letto con filtro: {name}") # Debug
                    return data

        # TENTATIVO 2: OPENCV (Fallback potente)
        if CV2_AVAILABLE:
            # Converti in formato OpenCV (numpy array)
            open_cv_image = np.array(img_original.convert('RGB')) 
            # Converti RGB a BGR 
            open_cv_image = open_cv_image[:, :, ::-1].copy()
            
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(open_cv_image)
            if data:
                # st.success("Letto con OpenCV (AI)") # Debug
                return data
                
    except Exception as e:
        st.error(f"Errore tecnico analisi immagine: {e}")
        
    return None

# --- LOGICA ATTIVAZIONE (TAB 1) ---
with tab1:
    if not PYZBAR_AVAILABLE and not CV2_AVAILABLE:
        st.error("❌ Nessuna libreria di lettura QR installata (manca libzbar0 o opencv).")
    else:
        uploaded_file = st.file_uploader("Carica foto QR", type=["jpg","png","jpeg"], key="qr_up")
        
        if uploaded_file:
            st.image(uploaded_file, width=200, caption="Analisi in corso...")
            
            # CHIAMATA AL DECODER ROBUSTO
            qr_data = decodifica_robusta(uploaded_file)
            
            if qr_data:
                # Parsing del link (es. https://.../?c=CODICE)
                if "?c=" in qr_data:
                    code = qr_data.split("?c=")[1].split("&")[0]
                    cert = verifica_e_mostra_cert(code)
                    
                    if cert:
                        st.markdown(f"<div class='success-alert'><h3>✅ Rilevato: {cert['code']}</h3></div>", unsafe_allow_html=True)
                        
                        # FORM ATTIVAZIONE
                        with st.form(f"form_attivazione_{cert['code']}"):
                            t = st.text_input("🚛 Targa Veicolo")
                            n = st.text_input("Note (Opzionale)")
                            
                            if st.form_submit_button("🔓 ATTIVA ORA", type="primary"):
                                if attiva_certificato(cert['code'], t, n):
                                    st.success("✅ Attivazione riuscita!")
                                    time.sleep(1.5)
                                    st.rerun()
                else:
                    st.error(f"⚠️ QR Code rilevato ma non valido: {qr_data}")
            else:
                st.error("❌ Nessun QR Code trovato. Prova ad avvicinarti o aumentare la luminosità.")

# --- LOGICA MANUALE (TAB 2) ---
with tab2:
    ci = st.text_input("Inserisci Codice Manualmente")
    if st.button("Cerca"):
        st.session_state.man_cert = verifica_e_mostra_cert(ci.strip().upper())
    
    if "man_cert" in st.session_state and st.session_state.man_cert:
        c = st.session_state.man_cert
        st.info(f"Certificato Selezionato: {c['code']}")
        with st.form("f_man"):
            t = st.text_input("Targa")
            n = st.text_input("Note")
            if st.form_submit_button("ATTIVA"):
                if attiva_certificato(c['code'], t, n):
                    st.success("✅ Attivazione riuscita!")
                    st.session_state.man_cert = None
                    time.sleep(1.5)
                    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
