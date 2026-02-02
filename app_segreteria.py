import streamlit as st
import pandas as pd
from supabase import create_client, Client
import qrcode
import io
import base64
from datetime import datetime, timedelta
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

# --- FUNZIONI DI UTILITÀ ---
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
    .main-header {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        padding: 32px 40px; border-radius: 20px; margin-bottom: 32px;
        box-shadow: 0 10px 40px rgba(37, 99, 235, 0.3);
    }
    .main-header h1 { color: white; font-size: 32px; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .main-header p { color: rgba(255,255,255,0.85); margin: 8px 0 0; font-size: 15px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 32px; }
    .kpi-card {
        background: white; border-radius: 16px; padding: 24px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e1e4e8; transition: all 0.3s;
    }
    .kpi-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.12); }
    .kpi-label { font-size: 13px; color: #586069; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; margin-bottom: 8px; }
    .kpi-value { font-size: 36px; font-weight: 700; color: #24292e; line-height: 1; }
    .section-title {
        font-size: 20px; font-weight: 700; color: #24292e;
        margin: 32px 0 16px; padding-bottom: 12px; border-bottom: 2px solid #e1e4e8;
    }
    .form-container {
        background: white; padding: 28px; border-radius: 16px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08); border: 1px solid #e1e4e8;
    }
    .stButton>button { border-radius: 8px; font-weight: 600; padding: 0.5rem 2rem; transition: all 0.2s; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
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
    st.markdown("<div class='main-header'><h1>📊 Dashboard Centrale</h1><p>Panoramica sistema certificati A.L.C.I.</p></div>", unsafe_allow_html=True)
    
    with st.spinner("Caricamento dati..."):
        # Scarichiamo i dati necessari per i calcoli
        try:
            # count='exact', head=True serve per avere solo il numero totale senza scaricare i dati
            tot = supabase.table("certificati").select("*", count="exact", head=True).execute().count
            gen = supabase.table("certificati").select("*", count="exact", head=True).eq("stato", "GENERATO").execute().count
            
            # Per le date, scarichiamo i record attivi (limitiamo a 5000 per performance)
            resp = supabase.table("certificati").select("data_uso").eq("stato", "ATTIVO").order("data_uso", desc=True).limit(5000).execute()
            df_dates = pd.DataFrame(resp.data)
        except Exception as e:
            st.error(f"Errore caricamento dati: {e}")
            tot, gen = 0, 0
            df_dates = pd.DataFrame()

        att_oggi, att_mese, att_anno = 0, 0, 0

        if not df_dates.empty:
            df_dates['data_uso'] = pd.to_datetime(df_dates['data_uso'])
            # Normalizzazione timezone
            if df_dates['data_uso'].dt.tz is not None:
                now = pd.Timestamp.now(tz=df_dates['data_uso'].dt.tz)
            else:
                now = pd.Timestamp.now()
            
            today = now.date()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

            att_oggi = len(df_dates[df_dates['data_uso'].dt.date == today])
            att_mese = len(df_dates[df_dates['data_uso'] >= month_start])
            att_anno = len(df_dates[df_dates['data_uso'] >= year_start])
    
    st.markdown(f"""
        <div class='kpi-grid'>
            <div class='kpi-card'><div class='kpi-label'>Certificati Totali</div><div class='kpi-value'>{format_number(tot)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Stampati</div><div class='kpi-value'>{format_number(gen)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Oggi</div><div class='kpi-value' style='color:#22c55e'>{format_number(att_oggi)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Questo Mese</div><div class='kpi-value' style='color:#2563eb'>{format_number(att_mese)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Quest'Anno</div><div class='kpi-value' style='color:#f59e0b'>{format_number(att_anno)}</div></div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='section-title'>📋 Certificati Rimanenti per Stazione</div>", unsafe_allow_html=True)
    
    # Aggregazione via Pandas
    try:
        staz_resp = supabase.table("stazioni").select("stazione_id, ragione_sociale").execute()
        cert_resp = supabase.table("certificati").select("stazione_id, stato").execute()
        
        df_staz = pd.DataFrame(staz_resp.data)
        df_cert = pd.DataFrame(cert_resp.data)
        
        if not df_staz.empty:
            if not df_cert.empty:
                pivot = df_cert.groupby(['stazione_id', 'stato']).size().unstack(fill_value=0)
                if 'GENERATO' not in pivot.columns: pivot['GENERATO'] = 0
                if 'ATTIVO' not in pivot.columns: pivot['ATTIVO'] = 0
                
                pivot['Totale'] = pivot['GENERATO'] + pivot['ATTIVO']
                pivot = pivot.reset_index()
                
                merged = pd.merge(df_staz, pivot, on='stazione_id', how='left').fillna(0)
                merged['Rimanenti'] = merged['GENERATO'].astype(int)
                merged['Attivati'] = merged['ATTIVO'].astype(int)
                merged['Totale'] = merged['Totale'].astype(int)
                merged['% Utilizzo'] = merged.apply(lambda x: (x['Attivati']/x['Totale']*100) if x['Totale']>0 else 0, axis=1).round(1)
                
                st.dataframe(
                    merged[["ragione_sociale", "Totale", "Rimanenti", "Attivati", "% Utilizzo"]].sort_values("Rimanenti", ascending=False),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("Nessun certificato presente.")
        else:
            st.warning("Nessuna stazione configurata.")
    except Exception as e:
        st.error(f"Errore elaborazione dati stazioni: {e}")

# --- GESTIONE LOTTI ---
elif page == "📦 Gestione Lotti":
    st.markdown("<div class='main-header'><h1>📦 Gestione Lotti</h1><p>Assegnazione range certificati</p></div>", unsafe_allow_html=True)
    
    st.info(f"💡 **URL Base QR Code:** {BASE_URL}/?c=CODICE")
    
    # Recupero stazioni attive
    res_staz = supabase.table("stazioni").select("stazione_id, ragione_sociale").eq("attiva", True).execute()
    stazioni_df = pd.DataFrame(res_staz.data)
    
    if stazioni_df.empty:
        st.error("❌ Nessuna stazione attiva trovata.")
        st.stop()
    
    st.markdown("<div class='form-container'>", unsafe_allow_html=True)
    
    with st.form("nuovo_lotto"):
        st.markdown("#### 📋 Dettagli Lotto")
        col1, col2 = st.columns(2)
        
        with col1:
            staz_sel = st.selectbox(
                "Stazione destinataria",
                stazioni_df["stazione_id"].tolist(),
                format_func=lambda x: stazioni_df[stazioni_df["stazione_id"]==x]["ragione_sociale"].values[0]
            )
        with col2:
            prefix = st.text_input("Prefisso serie", value="ALCI", max_chars=10)
        
        # Recupero ultimo codice
        try:
            last = supabase.table("certificati").select("code").order("code", desc=True).limit(1).execute()
            ultimo_num = int(last.data[0]['code'].split("-")[-1]) if last.data else 0
        except:
            ultimo_num = 0
            
        st.info(f"📊 **Ultimo numero globale:** {format_number(ultimo_num)}")
        
        col3, col4, col5 = st.columns([1, 1, 1])
        with col3:
            num_inizio = st.number_input("Numero inizio", min_value=ultimo_num + 1, value=ultimo_num + 1, step=1)
        with col4:
            num_fine = st.number_input("Numero fine", min_value=num_inizio, value=num_inizio + 999, step=1)
        with col5:
            quantita = num_fine - num_inizio + 1
            st.metric("Quantità", format_number(quantita))
            
        if st.form_submit_button("🚀 Genera Lotto", type="primary"):
            if quantita > 2000:
                st.error("Massimo 2000 certificati per volta.")
            else:
                lotto_id = f"LOT-{staz_sel}-{datetime.now().strftime('%y%m%d%H%M')}"
                rows = []
                for i in range(num_inizio, num_fine + 1):
                    code = f"{prefix}-{str(i).zfill(7)}"
                    rows.append({"code": code, "lotto": lotto_id, "stazione_id": staz_sel, "stato": "GENERATO"})
                
                try:
                    # Batch insert
                    chunk_size = 500
                    bar = st.progress(0)
                    for i in range(0, len(rows), chunk_size):
                        supabase.table("certificati").insert(rows[i:i+chunk_size]).execute()
                        bar.progress(min((i+chunk_size)/len(rows), 1.0))
                    
                    st.success(f"✅ Generati {quantita} certificati per {staz_sel}")
                    
                    # Istruzioni Tipografia
                    primo = f"{prefix}-{str(num_inizio).zfill(7)}"
                    ultimo = f"{prefix}-{str(num_fine).zfill(7)}"
                    st.code(f"""
ORDINE STAMPA
Range: {primo} -> {ultimo}
Qtà: {quantita}
Stazione: {staz_sel}
URL QR: {BASE_URL}/?c=CODICE
                    """)
                except Exception as e:
                    st.error(f"Errore creazione: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
    
    # Lista Lotti (Semplificata via Pandas per evitare query complesse API)
    if st.button("🔄 Aggiorna Lista Lotti"):
        try:
            # Scarichiamo solo colonne essenziali
            all_c = pd.DataFrame(supabase.table("certificati").select("lotto, code, stato").execute().data)
            if not all_c.empty:
                stats = all_c.groupby('lotto').agg({
                    'code': ['min', 'max', 'count'],
                    'stato': lambda x: (x == 'ATTIVO').sum()
                }).reset_index()
                stats.columns = ['Lotto', 'Primo', 'Ultimo', 'Totale', 'Attivati']
                st.dataframe(stats, use_container_width=True)
            else:
                st.info("Nessun lotto.")
        except Exception as e:
            st.error(f"Errore lettura lista: {e}")

# --- QR CODE ---
elif page == "🔍 QR Code":
    st.markdown("<div class='main-header'><h1>🔍 Visualizzazione QR Code</h1></div>", unsafe_allow_html=True)
    
    code_search = st.text_input("Inserisci codice certificato", placeholder="ALCI-0000001")
    
    if code_search:
        try:
            res = supabase.table("certificati").select("*").eq("code", code_search.strip().upper()).execute()
            if res.data:
                cert = res.data[0]
                st.success(f"Trovato: {cert['code']}")
                qr_img = make_qr_image(cert['code'])
                st.image(f"data:image/png;base64,{qr_img}", width=200)
                st.code(f"{BASE_URL}/?c={cert['code']}")
            else:
                st.error("Non trovato")
        except Exception as e:
            st.error(f"Errore: {e}")

# --- ALERT SOSPETTI ---
elif page == "🚨 Alert Sospetti":
    st.markdown("<div class='main-header'><h1>🚨 Certificati Sospetti</h1></div>", unsafe_allow_html=True)
    
    try:
        # Recuperiamo gli attivi e filtriamo in Python
        resp = supabase.table("certificati").select("code, stazione_id, data_uso, targa").eq("stato", "ATTIVO").order("data_uso", desc=True).limit(2000).execute()
        df = pd.DataFrame(resp.data)
        
        if not df.empty:
            df['data_uso'] = pd.to_datetime(df['data_uso'])
            if df['data_uso'].dt.tz is not None:
                now = pd.Timestamp.now(tz=df['data_uso'].dt.tz)
            else:
                now = pd.Timestamp.now()
            
            # Filtro > 7 giorni fa
            limit_date = now - timedelta(days=7)
            df_old = df[df['data_uso'] < limit_date].copy()
            
            if not df_old.empty:
                df_old['Giorni Fa'] = (now - df_old['data_uso']).dt.days
                st.warning(f"⚠️ {len(df_old)} certificati attivati da più di 7 giorni.")
                st.dataframe(df_old[['code', 'stazione_id', 'data_uso', 'targa', 'Giorni Fa']], use_container_width=True)
            else:
                st.success("✅ Nessuna anomalia recente.")
            
            st.markdown("### 📈 Attivazioni ultimi 30 giorni")
            df['date_only'] = df['data_uso'].dt.date
            daily = df.groupby('date_only').size()
            st.line_chart(daily)
        else:
            st.info("Nessun certificato attivo da analizzare.")
            
    except Exception as e:
        st.error(f"Errore analisi: {e}")

# --- STAZIONI ---
elif page == "🏭 Stazioni":
    st.markdown("<div class='main-header'><h1>🏭 Rete Stazioni</h1></div>", unsafe_allow_html=True)
    
    # Lista
    res = supabase.table("stazioni").select("*").execute()
    df_staz = pd.DataFrame(res.data)
    if not df_staz.empty:
        st.dataframe(df_staz, use_container_width=True)
    
    # Aggiungi
    with st.form("add_staz"):
        st.markdown("### Aggiungi Stazione")
        c1, c2, c3 = st.columns(3)
        sid = c1.text_input("ID Stazione")
        rag = c2.text_input("Ragione Sociale")
        citta = c3.text_input("Città")
        c4, c5 = st.columns(2)
        lat = c4.number_input("Lat", format="%.6f", value=45.0)
        lon = c5.number_input("Lon", format="%.6f", value=12.0)
        pwd = st.text_input("Password App", value="lavaggio123")
        
        if st.form_submit_button("Salva"):
            try:
                data = {
                    "stazione_id": sid, "ragione_sociale": rag, "citta": citta,
                    "gps_lat": lat, "gps_lon": lon, "attiva": True, "password": pwd
                }
                supabase.table("stazioni").insert(data).execute()
                st.success("✅ Stazione aggiunta!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore inserimento: {e}")

# --- DIAGNOSTICA DB ---
elif page == "🔧 Diagnostica DB":
    st.markdown("<div class='main-header'><h1>🔧 Diagnostica Database</h1></div>", unsafe_allow_html=True)
    
    search = st.text_input("Cerca codice per reset/modifica")
    if search:
        res = supabase.table("certificati").select("*").eq("code", search.strip().upper()).execute()
        if res.data:
            cert = res.data[0]
            st.write(cert)
            c1, c2, c3 = st.columns(3)
            if c1.button("Reset a GENERATO"):
                supabase.table("certificati").update({"stato": "GENERATO", "data_uso": None, "targa": None}).eq("code", cert['code']).execute()
                st.success("Fatto")
                st.rerun()
            if c2.button("Forza ATTIVO (Oggi)"):
                supabase.table("certificati").update({"stato": "ATTIVO", "data_uso": datetime.now().isoformat()}).eq("code", cert['code']).execute()
                st.success("Fatto")
                st.rerun()
            if c3.button("Elimina Certificato"):
                supabase.table("certificati").delete().eq("code", cert['code']).execute()
                st.success("Eliminato")
                st.rerun()
        else:
            st.warning("Non trovato")

    st.markdown("---")
    st.markdown("### Controlli Integrità")
    if st.button("Cerca Inconsistenze"):
        # Esempio: ATTIVO senza data
        try:
            bad = supabase.table("certificati").select("*").eq("stato", "ATTIVO").is_("data_uso", "null").execute()
            if bad.data:
                st.error(f"Trovati {len(bad.data)} certificati ATTIVI senza data.")
                if st.button("Correggi date mancanti"):
                    supabase.table("certificati").update({"data_uso": datetime.now().isoformat()}).eq("stato", "ATTIVO").is_("data_uso", "null").execute()
                    st.success("Corretti!")
            else:
                st.success("✅ Nessuna anomalia 'Attivo senza data'.")
        except Exception as e:
            st.error(f"Errore controllo: {e}")

# --- IMPOSTAZIONI ---
elif page == "⚙️ Impostazioni":
    st.markdown("<div class='main-header'><h1>⚙️ Impostazioni</h1></div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 📥 Export Dati (Backup)")
        if st.button("Scarica CSV Certificati"):
            res = supabase.table("certificati").select("*").execute()
            df = pd.DataFrame(res.data)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "certificati_backup.csv", "text/csv")
            
    with c2:
        st.markdown("### 🗑️ Zona Pericolo")
        if st.checkbox("Abilita cancellazione totale"):
            if st.button("RESETTA TUTTO IL DB", type="primary"):
                supabase.table("certificati").delete().neq("code", "0").execute()
                st.error("Database svuotato.")
