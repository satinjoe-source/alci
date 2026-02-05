import streamlit as st
import pandas as pd
from supabase import create_client, Client
import qrcode
import io
import base64
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import time

BASE_URL = "https://appverificapy.streamlit.app"

st.set_page_config(page_title="A.L.C.I. Segreteria", page_icon="🏢", layout="wide")

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
    st.error("❌ Errore connessione Supabase. Verifica i Secrets.")
    st.stop()

# --- GEOLOCATOR (OpenStreetMap) ---
def get_coordinates(address):
    if not address:
        return None, None
    try:
        # Aggiungiamo un user_agent molto specifico e casuale per evitare blocchi
        # E un timeout lungo (10 secondi) per connessioni lente
        geolocator = Nominatim(user_agent="alci_segreteria_app_v3_fix", timeout=10)
        location = geolocator.geocode(address)
        
        if location:
            return location.latitude, location.longitude
        else:
            # Se arrivi qui, OpenStreetMap non ha trovato l'indirizzo
            st.toast(f"Indirizzo '{address}' non trovato sulle mappe.", icon="⚠️")
            return None, None
            
    except Exception as e:
        # Se arrivi qui, c'è un errore di connessione o blocco IP
        st.error(f"Errore connessione mappe: {e}")
        return None, None

# --- FUNZIONI UTILI ---
def make_qr_image(code: str) -> str:
    url = f"{BASE_URL}/?c={code}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

def format_number(n):
    return f"{n:,}".replace(",", ".")

# --- CSS STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); font-family: 'Inter', sans-serif; }
    
    /* FIX INPUT */
    .stSelectbox div[data-baseweb="select"] > div, 
    .stTextInput input, 
    .stNumberInput input,
    .stTextArea textarea {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%); border-right: 1px solid #e1e4e8; }
    .main-header { background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); padding: 32px 40px; border-radius: 20px; margin-bottom: 32px; color: white; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px; }
    .kpi-card { background: white; border-radius: 16px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); text-align: center; }
    .kpi-value { font-size: 36px; font-weight: 700; color: #24292e; }
    .kpi-label { font-size: 13px; color: #586069; text-transform: uppercase; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    col_sx, col_center, col_dx = st.columns([1, 2, 1])
    with col_center:
        try:
            st.image("logo alci.jpg", width=130)
        except: st.warning("No Logo")
        
    st.markdown("""
        <div style='text-align:center; padding:10px 0;'>
            <div style='font-size:24px; font-weight:900; 
                        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        letter-spacing: 2px;'>A.L.C.I.</div>
            <div style='color:#6c757d; font-size:12px; margin-top:4px; font-weight:600;'>SEGRETERIA</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    page = st.radio("Menu", [
        "📊 Dashboard",
        "📦 Gestione Lotti",
        "🏭 Gestione Stazioni",
        "🔍 QR Code",
        "🚨 Alert Sospetti",
        "🔧 Diagnostica DB",
        "⚙️ Impostazioni"
    ])

# --- DASHBOARD ---
if page == "📊 Dashboard":
    st.markdown("<div class='main-header'><h1>📊 Dashboard</h1></div>", unsafe_allow_html=True)
    
    with st.spinner("Calcolo statistiche..."):
        try:
            tot = supabase.table("certificati").select("*", count="exact", head=True).execute().count
            gen = supabase.table("certificati").select("*", count="exact", head=True).eq("stato", "GENERATO").execute().count
            
            resp = supabase.table("certificati").select("data_uso").eq("stato", "ATTIVO").order("data_uso", desc=True).limit(5000).execute()
            df = pd.DataFrame(resp.data)
            
            att_oggi, att_mese = 0, 0
            if not df.empty:
                df['data_uso'] = pd.to_datetime(df['data_uso'])
                now = pd.Timestamp.now(tz=df['data_uso'].dt.tz) if df['data_uso'].dt.tz else pd.Timestamp.now()
                att_oggi = len(df[df['data_uso'].dt.date == now.date()])
                att_mese = len(df[df['data_uso'] >= now.replace(day=1, hour=0)])
                
        except:
            tot, gen, att_oggi, att_mese = 0, 0, 0, 0

    # KPI AGGREGATI (Privacy Safe)
    st.markdown(f"""
        <div class='kpi-grid'>
            <div class='kpi-card'><div class='kpi-label'>Emessi Totali</div><div class='kpi-value'>{format_number(tot)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Da Attivare (Totale Rete)</div><div class='kpi-value'>{format_number(gen)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Oggi</div><div class='kpi-value' style='color:green'>{format_number(att_oggi)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Mese Corrente</div><div class='kpi-value' style='color:blue'>{format_number(att_mese)}</div></div>
        </div>
    """, unsafe_allow_html=True)
    
    # RIEPILOGO RETE (Senza dettaglio scorte per stazione)
    st.subheader("Riepilogo Rete")
    try:
        # Contiamo solo quante stazioni sono attive
        count_staz = supabase.table("stazioni").select("*", count="exact", head=True).eq("attiva", True).execute().count
        
        st.markdown(f"""
        <div style='background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-top: 10px;'>
            <h4 style='color: #2563eb; margin: 0 0 10px 0;'>🏢 Rete Stazioni A.L.C.I.</h4>
            <p style='font-size: 18px; color: #1e293b;'>
                Il network è attualmente composto da <strong>{count_staz}</strong> stazioni di lavaggio operative.
            </p>
            <p style='color: #64748b; font-size: 13px; font-style: italic; margin-top: 15px;'>
                🔒 Nota Privacy: Il dettaglio delle giacenze per singola stazione è oscurato. 
                I dati visualizzati nei riquadri in alto rappresentano i totali aggregati dell'intera associazione.
            </p>
        </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Errore nel recupero dati rete: {e}")

# --- GESTIONE STAZIONI ---
elif page == "🏭 Gestione Stazioni":
    st.markdown("<div class='main-header'><h1>🏭 Gestione Stazioni</h1></div>", unsafe_allow_html=True)
    
    tab_list, tab_add, tab_edit = st.tabs(["📋 Elenco Stazioni", "➕ Aggiungi Nuova", "✏️ Modifica/Elimina"])

    with tab_list:
        try:
            res = supabase.table("stazioni").select("*").order("ragione_sociale").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                cols = ["stazione_id", "ragione_sociale", "citta", "email", "attiva"]
                cols = [c for c in cols if c in df.columns]
                st.dataframe(df[cols], use_container_width=True, hide_index=True)
            else:
                st.info("Nessuna stazione presente.")
        except Exception as e:
            st.error(f"Errore: {e}")

    with tab_add:
        st.subheader("Inserisci Nuova Stazione")
        if "new_lat" not in st.session_state: st.session_state.new_lat = 0.0
        if "new_lon" not in st.session_state: st.session_state.new_lon = 0.0

        with st.container(border=True):
            col_a, col_b = st.columns(2)
            new_id = col_a.text_input("ID Stazione (es. MATRA02)").upper().strip()
            new_name = col_b.text_input("Ragione Sociale")
            
            col_c, col_d = st.columns(2)
            new_email = col_c.text_input("Email Utente")
            new_pass = col_d.text_input("Password App", value="lavaggio123")
            
            new_city = st.text_input("Città / Indirizzo")
            
            st.markdown("---")
            st.markdown("###### 📍 Coordinate GPS")
            c_cal, c_res = st.columns([3, 1])
            addr_to_calc = c_cal.text_input("Indirizzo per calcolo GPS")
            if c_res.button("📍 Trova", key="btn_calc_new"):
                lat, lon = get_coordinates(addr_to_calc)
                if lat:
                    st.session_state.new_lat = lat
                    st.session_state.new_lon = lon
                    st.success("Trovato!")
                else: st.error("Non trovato.")

            c1, c2, c3 = st.columns(3)
            lat_val = c1.number_input("Latitudine", value=st.session_state.new_lat, format="%.6f", key="input_new_lat")
            lon_val = c2.number_input("Longitudine", value=st.session_state.new_lon, format="%.6f", key="input_new_lon")
            raggio = c3.number_input("Raggio (m)", value=200, step=50)

            if st.button("💾 Salva Stazione", type="primary"):
                if new_id and new_name:
                    try:
                        data = {
                            "stazione_id": new_id, "ragione_sociale": new_name, "citta": new_city,
                            "email": new_email, "password": new_pass, "gps_lat": lat_val,
                            "gps_lon": lon_val, "raggio_attivazione": raggio, "attiva": True
                        }
                        supabase.table("stazioni").insert(data).execute()
                        st.success(f"Stazione {new_name} creata!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e: st.error(f"Errore: {e}")
                else: st.warning("Dati mancanti.")

    with tab_edit:
        st.subheader("Modifica Dati")
        try:
            staz_list = supabase.table("stazioni").select("*").order("ragione_sociale").execute().data
        except: staz_list = []
        
        if staz_list:
            options = {s['stazione_id']: f"{s['ragione_sociale']} ({s['stazione_id']})" for s in staz_list}
            sel_id = st.selectbox("Seleziona Stazione", options.keys(), format_func=lambda x: options[x])
            curr_staz = next((s for s in staz_list if s['stazione_id'] == sel_id), None)
            
            if curr_staz:
                with st.form("edit_form"):
                    c_e1, c_e2 = st.columns(2)
                    edit_name = c_e1.text_input("Ragione Sociale", value=curr_staz.get('ragione_sociale', ''))
                    edit_email = c_e2.text_input("Email", value=curr_staz.get('email', ''))
                    
                    c_e3, c_e4 = st.columns(2)
                    edit_city = c_e3.text_input("Città", value=curr_staz.get('citta', ''))
                    edit_pass = c_e4.text_input("Password", value=curr_staz.get('password', ''))
                    
                    st.markdown("---")
                    ce_1, ce_2, ce_3 = st.columns(3)
                    edit_lat = ce_1.number_input("Lat", value=float(curr_staz.get('gps_lat') or 0.0), format="%.6f")
                    edit_lon = ce_2.number_input("Lon", value=float(curr_staz.get('gps_lon') or 0.0), format="%.6f")
                    edit_rag = ce_3.number_input("Raggio", value=int(curr_staz.get('raggio_attivazione') or 200))
                    
                    edit_active = st.checkbox("Attiva", value=curr_staz.get('attiva', True))
                    
                    c_save, c_del = st.columns([1,1])
                    if c_save.form_submit_button("💾 Aggiorna", type="primary"):
                        try:
                            upd = {"ragione_sociale": edit_name, "citta": edit_city, "email": edit_email,
                                   "password": edit_pass, "gps_lat": edit_lat, "gps_lon": edit_lon,
                                   "raggio_attivazione": edit_rag, "attiva": edit_active}
                            supabase.table("stazioni").update(upd).eq("stazione_id", sel_id).execute()
                            st.success("Aggiornato!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e: st.error(f"Errore: {e}")
                        
                    if c_del.form_submit_button("🗑️ ELIMINA", type="secondary"):
                        try:
                            supabase.table("stazioni").delete().eq("stazione_id", sel_id).execute()
                            st.success("Eliminata!")
                            time.sleep(1)
                            st.rerun()
                        except: st.error("Impossibile eliminare: ci sono certificati collegati.")

# --- GESTIONE LOTTI ---
elif page == "📦 Gestione Lotti":
    st.markdown("<div class='main-header'><h1>📦 Generazione Lotti</h1></div>", unsafe_allow_html=True)
    try:
        stazioni = supabase.table("stazioni").select("stazione_id, ragione_sociale").eq("attiva", True).execute().data
    except: stazioni = []
        
    if not stazioni:
        st.warning("Nessuna stazione attiva.")
    else:
        with st.form("new_lotto"):
            col1, col2 = st.columns(2)
            opt = {s['stazione_id']: s['ragione_sociale'] for s in stazioni}
            sid = col1.selectbox("Stazione", opt.keys(), format_func=lambda x: opt[x])
            prefix = col2.text_input("Prefisso", "ALCI")
            
            try:
                last = supabase.table("certificati").select("code").order("code", desc=True).limit(1).execute()
                last_n = int(last.data[0]['code'].split("-")[-1]) if last.data else 0
            except: last_n = 0
            
            st.info(f"Ultimo numero: **{last_n}**")
            c3, c4 = st.columns(2)
            start = c3.number_input("Inizio", value=last_n+1)
            end = c4.number_input("Fine", value=last_n+100)
            
            if st.form_submit_button("🚀 Genera"):
                lotto = f"LOT-{sid}-{datetime.now().strftime('%y%m%d%H%M')}"
                rows = [{"code": f"{prefix}-{str(i).zfill(7)}", "lotto": lotto, "stazione_id": sid} for i in range(start, end+1)]
                try:
                    chunk = 1000
                    bar = st.progress(0)
                    for i in range(0, len(rows), chunk):
                        supabase.table("certificati").insert(rows[i:i+chunk]).execute()
                        bar.progress(min((i+chunk)/len(rows), 1.0))
                    st.success(f"Generati {len(rows)} certificati.")
                except Exception as e: st.error(f"Errore: {e}")

# --- QR CODE ---
elif page == "🔍 QR Code":
    st.markdown("<div class='main-header'><h1>🔍 Visualizzazione QR</h1></div>", unsafe_allow_html=True)
    code = st.text_input("Cerca Codice")
    if st.button("Cerca"):
        res = supabase.table("certificati").select("*").eq("code", code.strip().upper()).execute()
        if res.data:
            c = res.data[0]
            st.image(f"data:image/png;base64,{make_qr_image(c['code'])}", width=200)
            st.write(f"Stato: {c['stato']}")
        else: st.error("Non trovato")

# --- ALERT SOSPETTI ---
elif page == "🚨 Alert Sospetti":
    st.markdown("<div class='main-header'><h1>🚨 Alert e Anomalie</h1></div>", unsafe_allow_html=True)
    
    st.subheader("⚠️ Certificati vecchi (> 7 gg)")
    try:
        res = supabase.table("certificati").select("*").eq("stato", "ATTIVO").order("data_uso", desc=True).limit(1000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_uso'] = pd.to_datetime(df['data_uso'])
            now = pd.Timestamp.now(tz=df['data_uso'].dt.tz) if df['data_uso'].dt.tz else pd.Timestamp.now()
            old = df[df['data_uso'] < now - timedelta(days=7)]
            if not old.empty:
                st.dataframe(old[["code", "stazione_id", "data_uso", "targa"]], use_container_width=True)
            else: st.success("Nessun certificato vecchio.")
    except Exception as e: st.error(str(e))

    st.markdown("---")
    st.subheader("📡 Anomalie GPS")
    try:
        res_anom = supabase.table("anomalie").select("*").order("data", desc=True).limit(50).execute()
        df_anom = pd.DataFrame(res_anom.data)
        if not df_anom.empty:
            st.dataframe(df_anom[["data", "stazione_id", "messaggio"]], use_container_width=True)
        else: st.info("Nessuna anomalia GPS.")
    except: st.warning("Tabella anomalie non trovata.")

# --- DIAGNOSTICA ---
elif page == "🔧 Diagnostica DB":
    st.title("Diagnostica")
    code = st.text_input("Codice da resettare")
    if st.button("Reset a GENERATO"):
        supabase.table("certificati").update({"stato": "GENERATO", "data_uso": None, "targa": None}).eq("code", code).execute()
        st.success("Fatto")

# --- IMPOSTAZIONI ---
elif page == "⚙️ Impostazioni":
    st.title("Impostazioni")
    if st.button("Download CSV Backup"):
        df = pd.DataFrame(supabase.table("certificati").select("*").execute().data)
        st.download_button("Scarica", df.to_csv().encode(), "backup.csv", "text/csv")
