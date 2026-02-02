import streamlit as st
import pandas as pd
from supabase import create_client, Client
import qrcode
import io
import base64
from datetime import datetime, timedelta

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
    st.title("🏢 A.L.C.I. Segreteria")
    st.markdown("---")
    page = st.radio("Menu", [
        "📊 Dashboard",
        "📦 Gestione Lotti",
        "🔍 QR Code",
        "🚨 Alert Sospetti",
        "🏭 Stazioni",
        "🔧 Diagnostica DB",
        "⚙️ Impostazioni"
    ])

# --- DASHBOARD ---
if page == "📊 Dashboard":
    st.markdown("<div class='main-header'><h1>📊 Dashboard</h1></div>", unsafe_allow_html=True)
    
    with st.spinner("Caricamento dati..."):
        try:
            tot = supabase.table("certificati").select("*", count="exact", head=True).execute().count
            gen = supabase.table("certificati").select("*", count="exact", head=True).eq("stato", "GENERATO").execute().count
            
            # Calcoli date (ultimi 5000 per velocità)
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
            <div class='kpi-card'><div class='kpi-label'>Totale</div><div class='kpi-value'>{format_number(tot)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Da Attivare</div><div class='kpi-value'>{format_number(gen)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Oggi</div><div class='kpi-value' style='color:green'>{format_number(att_oggi)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Mese</div><div class='kpi-value' style='color:blue'>{format_number(att_mese)}</div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Riepilogo Stazioni")
    try:
        staz_df = pd.DataFrame(supabase.table("stazioni").select("stazione_id, ragione_sociale").execute().data)
        cert_df = pd.DataFrame(supabase.table("certificati").select("stazione_id, stato").execute().data)
        
        if not staz_df.empty and not cert_df.empty:
            pivot = cert_df.groupby(['stazione_id', 'stato']).size().unstack(fill_value=0)
            if 'GENERATO' not in pivot: pivot['GENERATO'] = 0
            if 'ATTIVO' not in pivot: pivot['ATTIVO'] = 0
            
            merged = pd.merge(staz_df, pivot, on='stazione_id', how='left').fillna(0)
            merged['Rimanenti'] = merged['GENERATO'].astype(int)
            merged['Attivati'] = merged['ATTIVO'].astype(int)
            st.dataframe(merged[["ragione_sociale", "Rimanenti", "Attivati"]], use_container_width=True)
    except Exception as e:
        st.error(f"Errore dati: {e}")

# --- GESTIONE LOTTI ---
elif page == "📦 Gestione Lotti":
    st.markdown("<div class='main-header'><h1>📦 Generazione Lotti</h1></div>", unsafe_allow_html=True)
    
    # Select Stazioni
    try:
        stazioni = supabase.table("stazioni").select("stazione_id, ragione_sociale").eq("attiva", True).execute().data
    except:
        stazioni = []
        
    if not stazioni:
        st.warning("Nessuna stazione attiva.")
    else:
        with st.form("new_lotto"):
            col1, col2 = st.columns(2)
            opt = {s['stazione_id']: s['ragione_sociale'] for s in stazioni}
            sid = col1.selectbox("Stazione", opt.keys(), format_func=lambda x: opt[x])
            prefix = col2.text_input("Prefisso", "ALCI")
            
            # Ultimo numero
            try:
                last = supabase.table("certificati").select("code").order("code", desc=True).limit(1).execute()
                last_n = int(last.data[0]['code'].split("-")[-1]) if last.data else 0
            except: last_n = 0
            
            st.caption(f"Ultimo: {last_n}")
            c3, c4 = st.columns(2)
            start = c3.number_input("Inizio", value=last_n+1)
            end = c4.number_input("Fine", value=last_n+100)
            
            if st.form_submit_button("Genera"):
                lotto = f"LOT-{sid}-{datetime.now().strftime('%y%m%d%H%M')}"
                rows = [{"code": f"{prefix}-{str(i).zfill(7)}", "lotto": lotto, "stazione_id": sid} for i in range(start, end+1)]
                
                # Batch insert
                chunk = 500
                bar = st.progress(0)
                try:
                    for i in range(0, len(rows), chunk):
                        supabase.table("certificati").insert(rows[i:i+chunk]).execute()
                        bar.progress(min((i+chunk)/len(rows), 1.0))
                    st.success(f"Creati {len(rows)} certificati.")
                except Exception as e:
                    st.error(f"Errore: {e}")

# --- QR CODE (RIPRISTINATO CON LISTA) ---
elif page == "🔍 QR Code":
    st.markdown("<div class='main-header'><h1>🔍 Visualizzazione QR Code</h1></div>", unsafe_allow_html=True)
    
    # 1. Ricerca Singola
    st.markdown("### Ricerca Singola")
    code = st.text_input("Codice", placeholder="ALCI-0000001")
    if code:
        res = supabase.table("certificati").select("*").eq("code", code.strip().upper()).execute()
        if res.data:
            c = res.data[0]
            st.success(f"Trovato: {c['code']} - Stato: {c['stato']}")
            st.image(f"data:image/png;base64,{make_qr_image(c['code'])}", width=200)
        else:
            st.error("Non trovato")
            
    st.markdown("---")
    
    # 2. Lista Massiva (Come richiesto)
    st.markdown("### 📋 Lista QR Code per Stazione")
    
    # Select Stazione
    try:
        stazioni = supabase.table("stazioni").select("stazione_id, ragione_sociale").eq("attiva", True).execute().data
        opts = {s['stazione_id']: s['ragione_sociale'] for s in stazioni}
    except:
        stazioni = []
        opts = {}

    if stazioni:
        col_sel, col_lim = st.columns([2, 1])
        with col_sel:
            staz_sel = st.selectbox("Seleziona Stazione", opts.keys(), format_func=lambda x: opts[x])
        with col_lim:
            limit = st.slider("Numero certificati da mostrare", 3, 50, 9)
            
        if staz_sel:
            # Query per la lista
            try:
                res_list = supabase.table("certificati")\
                    .select("code, lotto, stato")\
                    .eq("stazione_id", staz_sel)\
                    .order("code", desc=False)\
                    .limit(limit)\
                    .execute()
                
                certs = res_list.data
                
                if certs:
                    st.markdown(f"**Mostrando i primi {len(certs)} certificati per {opts[staz_sel]}:**")
                    
                    # Griglia a 3 colonne
                    cols = st.columns(3)
                    for idx, cert in enumerate(certs):
                        with cols[idx % 3]:
                            qr_img = make_qr_image(cert['code'])
                            st.image(f"data:image/png;base64,{qr_img}", width=150)
                            st.markdown(f"**{cert['code']}**")
                            
                            # Badge Stato
                            if cert['stato'] == 'ATTIVO':
                                st.markdown(":white_check_mark: <span style='color:green'>ATTIVO</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(":page_facing_up: <span style='color:grey'>GENERATO</span>", unsafe_allow_html=True)
                            st.caption(f"Lotto: {cert['lotto']}")
                            st.divider()
                else:
                    st.info("Nessun certificato trovato per questa stazione.")
            except Exception as e:
                st.error(f"Errore caricamento lista: {e}")

# --- ALERT SOSPETTI ---
elif page == "🚨 Alert Sospetti":
    st.markdown("<div class='main-header'><h1>🚨 Certificati Sospetti</h1></div>", unsafe_allow_html=True)
    try:
        res = supabase.table("certificati").select("*").eq("stato", "ATTIVO").order("data_uso", desc=True).limit(1000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_uso'] = pd.to_datetime(df['data_uso'])
            now = pd.Timestamp.now(tz=df['data_uso'].dt.tz) if df['data_uso'].dt.tz else pd.Timestamp.now()
            old = df[df['data_uso'] < now - timedelta(days=7)]
            if not old.empty:
                st.warning(f"{len(old)} certificati > 7 giorni.")
                st.dataframe(old[["code", "stazione_id", "data_uso", "targa"]], use_container_width=True)
            else:
                st.success("Tutto ok.")
        else:
            st.info("Nessun dato.")
    except Exception as e:
        st.error(str(e))

# --- STAZIONI ---
elif page == "🏭 Stazioni":
    st.markdown("<div class='main-header'><h1>🏭 Gestione Stazioni</h1></div>", unsafe_allow_html=True)
    
    # Form aggiunta
    with st.expander("➕ Nuova Stazione"):
        with st.form("add"):
            c1, c2 = st.columns(2)
            sid = c1.text_input("ID Stazione")
            name = c2.text_input("Nome")
            c3, c4 = st.columns(2)
            city = c3.text_input("Città")
            pwd = c4.text_input("Password", "lavaggio123")
            if st.form_submit_button("Salva"):
                try:
                    supabase.table("stazioni").insert({"stazione_id": sid, "ragione_sociale": name, "citta": city, "password": pwd}).execute()
                    st.success("Salvata")
                    st.rerun()
                except Exception as e: st.error(str(e))
                
    # Lista
    try:
        df = pd.DataFrame(supabase.table("stazioni").select("*").execute().data)
        if not df.empty: st.dataframe(df, use_container_width=True)
    except: pass

# --- DIAGNOSTICA ---
elif page == "🔧 Diagnostica DB":
    st.title("Diagnostica")
    code = st.text_input("Cerca codice")
    if code:
        res = supabase.table("certificati").select("*").eq("code", code).execute()
        if res.data:
            st.write(res.data[0])
            if st.button("Reset a GENERATO"):
                supabase.table("certificati").update({"stato": "GENERATO", "data_uso": None, "targa": None}).eq("code", code).execute()
                st.success("Resettato")

# --- IMPOSTAZIONI ---
elif page == "⚙️ Impostazioni":
    st.title("Impostazioni")
    if st.button("Download Backup CSV"):
        df = pd.DataFrame(supabase.table("certificati").select("*").execute().data)
        st.download_button("Scarica", df.to_csv().encode(), "backup.csv", "text/csv")
