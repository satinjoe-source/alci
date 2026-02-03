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
    try:
        geolocator = Nominatim(user_agent="alci_segreteria_app")
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None, None
    except:
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

    st.markdown(f"""
        <div class='kpi-grid'>
            <div class='kpi-card'><div class='kpi-label'>Emessi Totali</div><div class='kpi-value'>{format_number(tot)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Da Attivare</div><div class='kpi-value'>{format_number(gen)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Oggi</div><div class='kpi-value' style='color:green'>{format_number(att_oggi)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Mese Corrente</div><div class='kpi-value' style='color:blue'>{format_number(att_mese)}</div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Riepilogo Stazioni")
    try:
        staz_res = supabase.table("stazioni").select("stazione_id, ragione_sociale").execute()
        stazioni = staz_res.data
        if stazioni:
            stats_list = []
            prog_bar = st.progress(0)
            for idx, s in enumerate(stazioni):
                sid = s['stazione_id']
                c_tot = supabase.table("certificati").select("*", count="exact", head=True).eq("stazione_id", sid).execute().count
                c_att = supabase.table("certificati").select("*", count="exact", head=True).eq("stazione_id", sid).eq("stato", "ATTIVO").execute().count
                stats_list.append({
                    "Stazione": s['ragione_sociale'],
                    "Rimanenti": c_tot - c_att,
                    "Attivati": c_att,
                    "Totale Assegnati": c_tot
                })
                prog_bar.progress((idx + 1) / len(stazioni))
            prog_bar.empty()
            st.dataframe(pd.DataFrame(stats_list).sort_values("Rimanenti", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna stazione configurata.")
    except Exception as e:
        st.error(f"Errore: {e}")

# --- GESTIONE STAZIONI (NUOVA VERSIONE COMPLETA) ---
elif page == "🏭 Gestione Stazioni":
    st.markdown("<div class='main-header'><h1>🏭 Gestione Stazioni</h1></div>", unsafe_allow_html=True)
    
    # Tabs per organizzare meglio
    tab_list, tab_add, tab_edit = st.tabs(["📋 Elenco Stazioni", "➕ Aggiungi Nuova", "✏️ Modifica/Elimina"])

    # 1. ELENCO
    with tab_list:
        try:
            res = supabase.table("stazioni").select("*").order("ragione_sociale").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                # Riordiniamo le colonne per leggibilità
                cols = ["stazione_id", "ragione_sociale", "citta", "email", "password", "gps_lat", "gps_lon", "attiva"]
                # Filtriamo solo quelle che esistono nel df (per evitare errori se mancano colonne)
                cols = [c for c in cols if c in df.columns]
                st.dataframe(df[cols], use_container_width=True, hide_index=True)
            else:
                st.info("Nessuna stazione presente.")
        except Exception as e:
            st.error(f"Errore caricamento elenco: {e}")

    # 2. AGGIUNGI NUOVA
    with tab_add:
        st.subheader("Inserisci Nuova Stazione")
        
        # Inizializza session state per coordinate se non esiste
        if "new_lat" not in st.session_state: st.session_state.new_lat = 0.0
        if "new_lon" not in st.session_state: st.session_state.new_lon = 0.0

        with st.container(border=True):
            col_a, col_b = st.columns(2)
            new_id = col_a.text_input("ID Stazione (es. MATRA02)", help="Codice univoco interno").upper().strip()
            new_name = col_b.text_input("Ragione Sociale")
            
            col_c, col_d = st.columns(2)
            new_email = col_c.text_input("Email Utente", help="Email per login o comunicazioni")
            new_pass = col_d.text_input("Password App", value="lavaggio123")
            
            new_city = st.text_input("Città / Indirizzo")
            
            st.markdown("---")
            st.markdown("###### 📍 Coordinate GPS")
            
            # Calcolatore GPS
            c_cal, c_res = st.columns([3, 1])
            addr_to_calc = c_cal.text_input("Indirizzo completo per calcolo GPS", placeholder="Via Roma 1, Milano, Italia")
            if c_res.button("📍 Trova Coordinate", key="btn_calc_new"):
                lat, lon = get_coordinates(addr_to_calc)
                if lat:
                    st.session_state.new_lat = lat
                    st.session_state.new_lon = lon
                    st.success("Coordinate trovate!")
                else:
                    st.error("Indirizzo non trovato.")

            # Campi Lat/Lon (prendono valore da session_state)
            c1, c2, c3 = st.columns(3)
            lat_val = c1.number_input("Latitudine", value=st.session_state.new_lat, format="%.6f", key="input_new_lat")
            lon_val = c2.number_input("Longitudine", value=st.session_state.new_lon, format="%.6f", key="input_new_lon")
            raggio = c3.number_input("Raggio Attivazione (metri)", value=200, step=50)

            if st.button("💾 Salva Stazione", type="primary"):
                if new_id and new_name:
                    try:
                        data = {
                            "stazione_id": new_id,
                            "ragione_sociale": new_name,
                            "citta": new_city,
                            "email": new_email,
                            "password": new_pass,
                            "gps_lat": lat_val,
                            "gps_lon": lon_val,
                            "raggio_attivazione": raggio,
                            "attiva": True
                        }
                        supabase.table("stazioni").insert(data).execute()
                        st.success(f"Stazione {new_name} creata con successo!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore inserimento: {e}. Controlla che l'ID non sia duplicato.")
                else:
                    st.warning("ID e Ragione Sociale sono obbligatori.")

    # 3. MODIFICA / ELIMINA
    with tab_edit:
        st.subheader("Modifica Dati Stazione")
        
        # Recupera stazioni per selectbox
        try:
            staz_list = supabase.table("stazioni").select("*").order("ragione_sociale").execute().data
        except: staz_list = []
        
        if not staz_list:
            st.warning("Nessuna stazione da modificare.")
        else:
            options = {s['stazione_id']: f"{s['ragione_sociale']} ({s['stazione_id']})" for s in staz_list}
            sel_id = st.selectbox("Seleziona Stazione da Modificare", options.keys(), format_func=lambda x: options[x])
            
            # Recupera dati della selezione corrente
            curr_staz = next((s for s in staz_list if s['stazione_id'] == sel_id), None)
            
            if curr_staz:
                with st.form("edit_form"):
                    c_e1, c_e2 = st.columns(2)
                    # ID non modificabile facilmente (è primary key), meglio lasciarlo read-only o gestire con cura
                    st.caption(f"Stai modificando ID: **{curr_staz['stazione_id']}**")
                    
                    edit_name = c_e1.text_input("Ragione Sociale", value=curr_staz.get('ragione_sociale', ''))
                    edit_email = c_e2.text_input("Email", value=curr_staz.get('email', ''))
                    
                    c_e3, c_e4 = st.columns(2)
                    edit_city = c_e3.text_input("Città", value=curr_staz.get('citta', ''))
                    edit_pass = c_e4.text_input("Password", value=curr_staz.get('password', ''))
                    
                    st.markdown("---")
                    st.markdown("###### 📍 Coordinate GPS")
                    
                    # Coordinate attuali o 0.0
                    curr_lat = curr_staz.get('gps_lat') or 0.0
                    curr_lon = curr_staz.get('gps_lon') or 0.0
                    curr_rag = curr_staz.get('raggio_attivazione') or 200

                    ce_1, ce_2, ce_3 = st.columns(3)
                    edit_lat = ce_1.number_input("Latitudine", value=float(curr_lat), format="%.6f")
                    edit_lon = ce_2.number_input("Longitudine", value=float(curr_lon), format="%.6f")
                    edit_rag = ce_3.number_input("Raggio (m)", value=int(curr_rag))

                    edit_active = st.checkbox("Stazione Attiva", value=curr_staz.get('attiva', True))
                    
                    col_save, col_del = st.columns([1, 1])
                    
                    # Pulsanti azione
                    update_btn = col_save.form_submit_button("💾 Aggiorna Dati", type="primary")
                    delete_btn = col_del.form_submit_button("🗑️ ELIMINA STAZIONE", type="secondary")
                    
                    if update_btn:
                        try:
                            upd_data = {
                                "ragione_sociale": edit_name,
                                "citta": edit_city,
                                "email": edit_email,
                                "password": edit_pass,
                                "gps_lat": edit_lat,
                                "gps_lon": edit_lon,
                                "raggio_attivazione": edit_rag,
                                "attiva": edit_active
                            }
                            supabase.table("stazioni").update(upd_data).eq("stazione_id", sel_id).execute()
                            st.success("Dati aggiornati correttamente!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore aggiornamento: {e}")

                    if delete_btn:
                        # Controllo integrità referenziale manuale (opzionale ma consigliato)
                        # Se ha certificati, Supabase darà errore foreign key se non è cascade, 
                        # ma meglio avvisare l'utente prima o gestire l'errore.
                        try:
                            supabase.table("stazioni").delete().eq("stazione_id", sel_id).execute()
                            st.success("Stazione eliminata!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Non posso eliminare: Probabilmente ci sono certificati collegati a questa stazione. Disattivala invece di eliminarla.\nErrore tecnico: {e}")

                # Calcolatore fuori dal form per non triggerare il submit del form stesso
                with st.expander("🛠️ Calcolatore GPS per Modifica"):
                    c_calc_e, c_res_e = st.columns([3, 1])
                    addr_edit_calc = c_calc_e.text_input("Scrivi indirizzo", key="addr_edit")
                    if c_res_e.button("Calcola", key="btn_calc_edit"):
                        lat_e, lon_e = get_coordinates(addr_edit_calc)
                        if lat_e:
                            st.info(f"Copia questi valori nei campi sopra:\nLat: **{lat_e}**\nLon: **{lon_e}**")
                        else:
                            st.error("Indirizzo non trovato")


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
            sid = col1.selectbox("Seleziona Stazione", opt.keys(), format_func=lambda x: opt[x])
            prefix = col2.text_input("Prefisso Codice", "ALCI")
            
            try:
                last = supabase.table("certificati").select("code").order("code", desc=True).limit(1).execute()
                if last.data:
                    parts = last.data[0]['code'].split("-")
                    last_n = int(parts[-1]) if parts[-1].isdigit() else 0
                else: last_n = 0
            except: last_n = 0
            
            st.info(f"Ultimo numero presente: **{last_n}**")
            
            c3, c4 = st.columns(2)
            start = c3.number_input("Dal numero", value=last_n+1, step=1)
            end = c4.number_input("Al numero", value=last_n+100, step=1)
            
            if st.form_submit_button("🚀 Genera Lotto"):
                qty = end - start + 1
                if qty > 5000:
                    st.error("Limite max 5000.")
                else:
                    lotto = f"LOT-{sid}-{datetime.now().strftime('%y%m%d%H%M')}"
                    rows = [{"code": f"{prefix}-{str(i).zfill(7)}", "lotto": lotto, "stazione_id": sid} for i in range(start, end+1)]
                    try:
                        chunk = 1000
                        bar = st.progress(0)
                        for i in range(0, len(rows), chunk):
                            supabase.table("certificati").insert(rows[i:i+chunk]).execute()
                            bar.progress(min((i+chunk)/len(rows), 1.0))
                        st.success(f"Generati {len(rows)} certificati per {opt[sid]}.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Errore: {e}")

# --- QR CODE ---
elif page == "🔍 QR Code":
    st.markdown("<div class='main-header'><h1>🔍 Visualizzazione QR Code</h1></div>", unsafe_allow_html=True)
    
    st.markdown("### 1. Cerca Certificato Singolo")
    col_s1, col_s2 = st.columns([3, 1])
    code = col_s1.text_input("Inserisci Codice", placeholder="Es. ALCI-0001000")
    if col_s2.button("Cerca"):
        res = supabase.table("certificati").select("*").eq("code", code.strip().upper()).execute()
        if res.data:
            c = res.data[0]
            st.success(f"Trovato: {c['code']} - Stato: {c['stato']}")
            st.image(f"data:image/png;base64,{make_qr_image(c['code'])}", width=200)
        else:
            st.error("Non trovato")
            
    st.markdown("---")
    st.markdown("### 2. Lista QR Code (Anteprima Stampa)")
    
    try:
        stazioni = supabase.table("stazioni").select("stazione_id, ragione_sociale").eq("attiva", True).execute().data
        opts = {s['stazione_id']: s['ragione_sociale'] for s in stazioni}
    except: stazioni = []

    if stazioni:
        c1, c2 = st.columns([2, 1])
        staz_sel = c1.selectbox("Filtra per Stazione", opts.keys(), format_func=lambda x: opts[x])
        limit = c2.slider("Quantità", 3, 50, 6)
            
        if staz_sel:
            try:
                res_list = supabase.table("certificati").select("code, lotto, stato").eq("stazione_id", staz_sel).order("code", desc=False).limit(limit).execute()
                certs = res_list.data
                if certs:
                    st.write(f"Anteprima per: **{opts[staz_sel]}**")
                    cols = st.columns(3)
                    for idx, cert in enumerate(certs):
                        with cols[idx % 3]:
                            with st.container(border=True):
                                st.image(f"data:image/png;base64,{make_qr_image(cert['code'])}", use_container_width=True)
                                st.markdown(f"**{cert['code']}**")
                                if cert['stato'] == 'ATTIVO':
                                    st.markdown("✅ <span style='color:green'>ATTIVO</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown("📄 <span style='color:grey'>GENERATO</span>", unsafe_allow_html=True)
                else: st.warning("Nessun certificato.")
            except Exception as e: st.error(f"Errore: {e}")

# --- ALERT SOSPETTI ---
st.markdown("---")
    st.subheader("📡 Anomalie GPS (Tentativi fuori zona)")
    try:
        # Recupera anomalie
        res_anom = supabase.table("anomalie").select("*").order("data", desc=True).limit(50).execute()
        df_anom = pd.DataFrame(res_anom.data)
        if not df_anom.empty:
            df_anom['data'] = pd.to_datetime(df_anom['data']).dt.strftime('%d/%m/%Y %H:%M')
            st.dataframe(df_anom[["data", "stazione_id", "messaggio"]], use_container_width=True)
        else:
            st.info("Nessuna anomalia GPS registrata.")
    except Exception as e:
        st.error(f"Errore caricamento anomalie: {e}")

# --- DIAGNOSTICA ---
elif page == "🔧 Diagnostica DB":
    st.title("Diagnostica")
    code = st.text_input("Cerca codice certificato")
    if code:
        res = supabase.table("certificati").select("*").eq("code", code.strip().upper()).execute()
        if res.data:
            st.write(res.data[0])
            c1, c2 = st.columns(2)
            if c1.button("Reset a GENERATO"):
                supabase.table("certificati").update({"stato": "GENERATO", "data_uso": None, "targa": None, "note": None}).eq("code", code.strip().upper()).execute()
                st.success("Resettato!")
                st.rerun()
            if c2.button("Elimina"):
                supabase.table("certificati").delete().eq("code", code.strip().upper()).execute()
                st.warning("Eliminato!")
                st.rerun()
        else: st.error("Non trovato")

# --- IMPOSTAZIONI ---
elif page == "⚙️ Impostazioni":
    st.title("Impostazioni")
    if st.button("Download CSV Completo Certificati"):
        df = pd.DataFrame(supabase.table("certificati").select("*").execute().data)
        st.download_button("Scarica CSV", df.to_csv().encode(), "backup_full.csv", "text/csv")
