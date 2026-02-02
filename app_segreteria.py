import streamlit as st
import pandas as pd
from supabase import create_client, Client
import qrcode
import io
import base64
from datetime import datetime

BASE_URL = "https://appverificapy.streamlit.app"

st.set_page_config(page_title="A.L.C.I. Segreteria", page_icon="🏢", layout="wide")

@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Errore connessione Supabase: {e}")
    st.stop()

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
    .main-header { background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); padding: 32px 40px; border-radius: 20px; margin-bottom: 32px; box-shadow: 0 10px 40px rgba(37, 99, 235, 0.3); }
    .main-header h1 { color: white; font-size: 32px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .main-header p { color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 15px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px; }
    .kpi-card { background: white; border-radius: 16px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e1e4e8; transition: all 0.3s; }
    .kpi-label { font-size: 13px; color: #586069; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 8px; }
    .kpi-value { font-size: 36px; font-weight: 700; color: #24292e; line-height: 1; }
    .section-title { font-size: 20px; font-weight: 700; color: #24292e; margin: 32px 0 16px; padding-bottom: 12px; border-bottom: 2px solid #e1e4e8; }
    .form-container { background: white; padding: 28px; border-radius: 16px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e1e4e8; }
    .stButton>button { border-radius: 8px; font-weight: 600; padding: 0.5rem 2rem; transition: all 0.2s; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
        <div style='text-align:center; padding:20px 0;'>
            <div style='font-size:32px; font-weight:900; 
                        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        letter-spacing: 2px;'>A.L.C.I.</div>
            <div style='color:#6c757d; font-size:12px; margin-top:4px; font-weight:600;'>SEGRETERIA</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("Menu", ["📊 Dashboard", "📦 Gestione Lotti", "🏭 Stazioni"])

if page == "📊 Dashboard":
    st.markdown("<div class='main-header'><h1>📊 Dashboard Centrale</h1><p>Panoramica sistema certificati A.L.C.I.</p></div>", unsafe_allow_html=True)
    
    with st.spinner("Caricamento dati Supabase..."):
        # Fetching raw data
        try:
            cert_resp = supabase.table("certificati").select("stato, data_uso").execute()
            df_cert = pd.DataFrame(cert_resp.data)
        except Exception as e:
            st.error(f"Errore lettura dati: {e}")
            df_cert = pd.DataFrame()

        # FIX: Gestione caso DataFrame vuoto per evitare KeyError
        if df_cert.empty:
            tot = 0
            gen = 0
            att_oggi = 0
            att_mese = 0
            att_anno = 0
        else:
            # Se ci sono dati, possiamo accedere alle colonne in sicurezza
            tot = len(df_cert)
            gen = len(df_cert[df_cert['stato'] == 'GENERATO'])
            
            # Filtro attivi
            df_att = df_cert[df_cert['stato'] == 'ATTIVO'].copy()
            
            if not df_att.empty:
                # Convertiamo in datetime gestendo il fuso orario
                df_att['data_uso'] = pd.to_datetime(df_att['data_uso'])
                
                # Otteniamo la data di oggi "timezone-aware" se necessario, o naive
                if df_att['data_uso'].dt.tz is not None:
                    now = pd.Timestamp.now(tz=df_att['data_uso'].dt.tz)
                else:
                    now = pd.Timestamp.now()
                
                oggi = now.normalize()
                inizio_mese = today = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                inizio_anno = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                
                att_oggi = len(df_att[df_att['data_uso'].dt.date == now.date()])
                att_mese = len(df_att[df_att['data_uso'] >= inizio_mese])
                att_anno = len(df_att[df_att['data_uso'] >= inizio_anno])
            else:
                att_oggi = 0
                att_mese = 0
                att_anno = 0

    st.markdown(f"""
        <div class='kpi-grid'>
            <div class='kpi-card'><div class='kpi-label'>Certificati Totali</div><div class='kpi-value'>{format_number(tot)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Stampati</div><div class='kpi-value'>{format_number(gen)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Oggi</div><div class='kpi-value' style='color:#22c55e'>{format_number(att_oggi)}</div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='section-title'>📋 Certificati Rimanenti per Stazione</div>", unsafe_allow_html=True)
    
    # Anche qui, gestione caso vuoto
    staz_resp = supabase.table("stazioni").select("stazione_id, ragione_sociale").execute()
    df_staz = pd.DataFrame(staz_resp.data)
    
    cert_agg_resp = supabase.table("certificati").select("stazione_id, stato").execute()
    df_c = pd.DataFrame(cert_agg_resp.data)
    
    if not df_c.empty and not df_staz.empty:
        # Aggregazione
        pivot = df_c.groupby(['stazione_id', 'stato']).size().unstack(fill_value=0)
        if 'GENERATO' not in pivot.columns: pivot['GENERATO'] = 0
        if 'ATTIVO' not in pivot.columns: pivot['ATTIVO'] = 0
        
        pivot['Totale'] = pivot['GENERATO'] + pivot['ATTIVO']
        pivot = pivot.reset_index()
        
        # Merge con nomi stazioni
        final = pd.merge(df_staz, pivot, on='stazione_id', how='left').fillna(0)
        final['Rimanenti'] = final['GENERATO'].astype(int)
        final['Attivati'] = final['ATTIVO'].astype(int)
        final['Totale'] = final['Totale'].astype(int)
        
        # Calcolo % sicuro (evita divisione per zero)
        final['% Utilizzo'] = final.apply(lambda x: (x['Attivati'] / x['Totale'] * 100) if x['Totale'] > 0 else 0, axis=1).round(1)
        
        st.dataframe(
            final[["ragione_sociale", "Totale", "Rimanenti", "Attivati", "% Utilizzo"]].sort_values("Rimanenti", ascending=False),
            use_container_width=True, hide_index=True
        )
    elif not df_staz.empty:
        st.info("Nessun certificato ancora generato.")
    else:
        st.warning("Nessuna stazione configurata.")

elif page == "📦 Gestione Lotti":
    st.markdown("<div class='main-header'><h1>📦 Gestione Lotti</h1><p>Assegnazione range certificati</p></div>", unsafe_allow_html=True)
    
    resp = supabase.table("stazioni").select("stazione_id, ragione_sociale").eq("attiva", True).execute()
    stazioni_df = pd.DataFrame(resp.data)
    
    if stazioni_df.empty:
        st.warning("⚠️ Nessuna stazione attiva trovata. Crea prima una stazione nel database.")
    else:
        with st.form("nuovo_lotto"):
            col1, col2 = st.columns(2)
            with col1:
                staz_sel = st.selectbox("Stazione", stazioni_df["stazione_id"].tolist(), format_func=lambda x: stazioni_df[stazioni_df["stazione_id"]==x]["ragione_sociale"].values[0])
            with col2:
                prefix = st.text_input("Prefisso", value="ALCI")
            
            # Get last code
            try:
                last_resp = supabase.table("certificati").select("code").order("code", desc=True).limit(1).execute()
                ultimo_num = 0
                if last_resp.data:
                    parts = last_resp.data[0]['code'].split("-")
                    if len(parts) > 1 and parts[-1].isdigit():
                        ultimo_num = int(parts[-1])
            except:
                ultimo_num = 0
                
            st.info(f"Ultimo numero rilevato: {ultimo_num}")
            
            col3, col4 = st.columns(2)
            with col3:
                num_inizio = st.number_input("Inizio", min_value=ultimo_num+1, value=ultimo_num+1)
            with col4:
                num_fine = st.number_input("Fine", min_value=num_inizio, value=num_inizio+999)
                
            if st.form_submit_button("🚀 Genera"):
                quantita = num_fine - num_inizio + 1
                if quantita > 5000:
                    st.error("Max 5000 per lotto (limitazione API)")
                else:
                    lotto_id = f"LOT-{staz_sel}-{datetime.now().strftime('%y%m%d%H%M')}"
                    data_list = []
                    for i in range(num_inizio, num_fine + 1):
                        data_list.append({
                            "code": f"{prefix}-{str(i).zfill(7)}",
                            "lotto": lotto_id,
                            "stazione_id": staz_sel,
                            "stato": "GENERATO"
                        })
                    
                    chunk_size = 1000
                    progress = st.progress(0)
                    try:
                        for i in range(0, len(data_list), chunk_size):
                            chunk = data_list[i:i + chunk_size]
                            supabase.table("certificati").insert(chunk).execute()
                            progress.progress(min((i + chunk_size) / len(data_list), 1.0))
                        
                        st.success(f"✅ Generati {quantita} certificati!")
                        st.cache_data.clear() # Pulisce cache se usata
                    except Exception as e:
                        st.error(f"Errore: {e}")

    # Visualizzazione Lotti
    if st.button("Aggiorna Lista Lotti"):
        try:
            resp = supabase.table("certificati").select("lotto, code, stato").execute()
            all_certs = pd.DataFrame(resp.data)
            
            if not all_certs.empty:
                stats = all_certs.groupby('lotto').agg({
                    'code': ['min', 'max', 'count'],
                    'stato': lambda x: (x == 'ATTIVO').sum()
                }).reset_index()
                
                # Appiattimento MultiIndex
                stats.columns = ['Lotto', 'Primo', 'Ultimo', 'Totale', 'Attivati']
                st.dataframe(stats, use_container_width=True)
            else:
                st.info("Nessun lotto presente.")
        except Exception as e:
            st.error(f"Errore lettura lista: {e}")

elif page == "🏭 Stazioni":
    st.title("Lista Stazioni")
    try:
        resp = supabase.table("stazioni").select("*").execute()
        df = pd.DataFrame(resp.data)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nessuna stazione inserita.")
    except Exception as e:
        st.error(f"Errore caricamento stazioni: {e}")
