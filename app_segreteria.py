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

# --- CSS STYLES (FIX VISIBILITÀ INPUT) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); font-family: 'Inter', sans-serif; }
    
    /* FIX VISIBILITÀ INPUT E SELECTBOX */
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
    # Creiamo 3 colonne: spazi laterali (1) e spazio centrale (2)
    col_sx, col_center, col_dx = st.columns([1, 2, 1])
    
    with col_center:
        try:
            # Larghezza consigliata per la sidebar: 130-150px
            st.image("logo alci.jpg", width=600) 
        except: 
            st.warning("No Logo")
        
    st.markdown("""
        <div style='text-align:center; padding:10px 0;'>
            <div style='font-size:24px; font-weight:800; 
                        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        letter-spacing: 2px;'>A.L.C.I.</div>
            <div style='color:#6c757d; font-size:18px; margin-top:4px; font-weight:600;'>SEGRETERIA</div>
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
    st.markdown("<div class='main-header'><h1>📊 Dashboard</h1></div>", unsafe_allow_html=True)
    
    with st.spinner("Calcolo statistiche in corso..."):
        # KPI GLOBALI (Velocissimi con count=exact)
        try:
            tot = supabase.table("certificati").select("*", count="exact", head=True).execute().count
            gen = supabase.table("certificati").select("*", count="exact", head=True).eq("stato", "GENERATO").execute().count
            
            # Per KPI temporali scarichiamo SOLO date attive (dataset ridotto)
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
            <div class='kpi-card'><div class='kpi-label'>Totale Emessi</div><div class='kpi-value'>{format_number(tot)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Da Attivare</div><div class='kpi-value'>{format_number(gen)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Attivati Oggi</div><div class='kpi-value' style='color:green'>{format_number(att_oggi)}</div></div>
            <div class='kpi-card'><div class='kpi-label'>Mese Corrente</div><div class='kpi-value' style='color:blue'>{format_number(att_mese)}</div></div>
        </div>
    """, unsafe_allow_html=True)
    
    # --- LOGICA AGGREGATA SCALABILE ---
    st.subheader("Riepilogo Stazioni")
    
    try:
        # 1. Scarica lista stazioni (poche righe)
        staz_res = supabase.table("stazioni").select("stazione_id, ragione_sociale").execute()
        stazioni = staz_res.data
        
        if stazioni:
            stats_list = []
            
            # Barra di progresso se ci sono tante stazioni
            prog_bar = st.progress(0)
            
            for idx, s in enumerate(stazioni):
                sid = s['stazione_id']
                
                # 2. Query COUNT specifica per ogni stazione (Molto veloce, non scarica righe)
                # Conta Totali
                c_tot = supabase.table("certificati").select("*", count="exact", head=True)\
                    .eq("stazione_id", sid).execute().count
                
                # Conta Attivi
                c_att = supabase.table("certificati").select("*", count="exact", head=True)\
                    .eq("stazione_id", sid).eq("stato", "ATTIVO").execute().count
                
                c_rim = c_tot - c_att
                
                stats_list.append({
                    "Stazione": s['ragione_sociale'],
                    "Rimanenti (Da Attivare)": c_rim,
                    "Attivati": c_att,
                    "Totale Assegnati": c_tot
                })
                prog_bar.progress((idx + 1) / len(stazioni))
            
            prog_bar.empty()
            
            # Visualizza tabella
            df_stats = pd.DataFrame(stats_list)
            # Ordina per Rimanenti descrescente
            df_stats = df_stats.sort_values(by="Rimanenti (Da Attivare)", ascending=False)
            
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna stazione configurata.")
            
    except Exception as e:
        st.error(f"Errore nel calcolo statistiche: {e}")

# --- GESTIONE LOTTI ---
elif page == "📦 Gestione Lotti":
    st.markdown("<div class='main-header'><h1>📦 Generazione Lotti</h1></div>", unsafe_allow_html=True)
    
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
            sid = col1.selectbox("Seleziona Stazione", opt.keys(), format_func=lambda x: opt[x])
            prefix = col2.text_input("Prefisso Codice", "ALCI")
            
            # Ultimo numero (Query ottimizzata, chiede solo 1 riga)
            try:
                last = supabase.table("certificati").select("code").order("code", desc=True).limit(1).execute()
                if last.data:
                    parts = last.data[0]['code'].split("-")
                    last_n = int(parts[-1]) if parts[-1].isdigit() else 0
                else:
                    last_n = 0
            except: last_n = 0
            
            st.info(f"Ultimo numero presente nel sistema: **{last_n}**")
            
            c3, c4 = st.columns(2)
            start = c3.number_input("Dal numero", value=last_n+1, step=1)
            end = c4.number_input("Al numero", value=last_n+100, step=1)
            
            if st.form_submit_button("🚀 Genera Lotto"):
                qty = end - start + 1
                if qty > 5000:
                    st.error("Limite massimo 5000 certificati per operazione.")
                else:
                    lotto = f"LOT-{sid}-{datetime.now().strftime('%y%m%d%H%M')}"
                    rows = [{"code": f"{prefix}-{str(i).zfill(7)}", "lotto": lotto, "stazione_id": sid} for i in range(start, end+1)]
                    
                    # Batch insert
                    chunk = 1000
                    bar = st.progress(0)
                    try:
                        for i in range(0, len(rows), chunk):
                            supabase.table("certificati").insert(rows[i:i+chunk]).execute()
                            bar.progress(min((i+chunk)/len(rows), 1.0))
                        st.success(f"✅ Creati {len(rows)} certificati per {opt[sid]}.")
                        st.cache_data.clear() # Pulisce cache se necessario
                    except Exception as e:
                        st.error(f"Errore durante la creazione: {e}")

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
    except:
        stazioni = []
        opts = {}

    if stazioni:
        c1, c2 = st.columns([2, 1])
        staz_sel = c1.selectbox("Filtra per Stazione", opts.keys(), format_func=lambda x: opts[x])
        limit = c2.slider("Quantità da mostrare", 3, 50, 6)
            
        if staz_sel:
            # Scarica solo quelli necessari
            try:
                res_list = supabase.table("certificati")\
                    .select("code, lotto, stato")\
                    .eq("stazione_id", staz_sel)\
                    .order("code", desc=False)\
                    .limit(limit)\
                    .execute()
                
                certs = res_list.data
                
                if certs:
                    st.write(f"Prime {len(certs)} voci per: **{opts[staz_sel]}**")
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
                else:
                    st.warning("Nessun certificato trovato per questa stazione.")
            except Exception as e:
                st.error(f"Errore caricamento lista: {e}")

# --- ALERT SOSPETTI ---
elif page == "🚨 Alert Sospetti":
    st.markdown("<div class='main-header'><h1>🚨 Certificati Sospetti</h1></div>", unsafe_allow_html=True)
    try:
        # Scarichiamo solo gli ultimi 1000 attivi per controllare le date
        res = supabase.table("certificati").select("*").eq("stato", "ATTIVO").order("data_uso", desc=True).limit(1000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_uso'] = pd.to_datetime(df['data_uso'])
            now = pd.Timestamp.now(tz=df['data_uso'].dt.tz) if df['data_uso'].dt.tz else pd.Timestamp.now()
            
            # Filtro Python
            old = df[df['data_uso'] < now - timedelta(days=7)]
            
            if not old.empty:
                st.warning(f"⚠️ Ci sono {len(old)} certificati attivati da più di 7 giorni.")
                st.dataframe(old[["code", "stazione_id", "data_uso", "targa"]], use_container_width=True)
            else:
                st.success("✅ Nessuna anomalia recente rilevata.")
        else:
            st.info("Nessun certificato attivo da analizzare.")
    except Exception as e:
        st.error(str(e))

# --- STAZIONI ---
elif page == "🏭 Stazioni":
    st.markdown("<div class='main-header'><h1>🏭 Gestione Stazioni</h1></div>", unsafe_allow_html=True)
    
    with st.expander("➕ Aggiungi Nuova Stazione", expanded=False):
        with st.form("add"):
            c1, c2 = st.columns(2)
            sid = c1.text_input("ID Stazione (es. MATRA02)")
            name = c2.text_input("Ragione Sociale")
            c3, c4 = st.columns(2)
            city = c3.text_input("Città")
            pwd = c4.text_input("Password App", "lavaggio123")
            
            if st.form_submit_button("Salva"):
                try:
                    supabase.table("stazioni").insert({"stazione_id": sid, "ragione_sociale": name, "citta": city, "password": pwd}).execute()
                    st.success("Stazione salvata con successo!")
                    st.rerun()
                except Exception as e: st.error(f"Errore: {e}")
                
    # Lista Stazioni
    try:
        df = pd.DataFrame(supabase.table("stazioni").select("*").execute().data)
        if not df.empty:
            st.dataframe(df[["stazione_id", "ragione_sociale", "citta", "attiva", "password"]], use_container_width=True)
    except: pass

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
        else:
            st.error("Codice non trovato")

# --- IMPOSTAZIONI ---
elif page == "⚙️ Impostazioni":
    st.title("Impostazioni")
    st.info("Il backup completo scarica tutti i dati. Potrebbe richiedere tempo.")
    if st.button("Download CSV Completo Certificati"):
        # Attenzione: qui scarica tutto. Se sono milioni, va gestito diversamente in futuro.
        # Per ora va bene così.
        df = pd.DataFrame(supabase.table("certificati").select("*").execute().data)
        st.download_button("Scarica CSV", df.to_csv().encode(), "backup_full.csv", "text/csv")
