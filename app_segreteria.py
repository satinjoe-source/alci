# app_segreteria.py
import streamlit as st
import pandas as pd
import libsql_experimental as libsql
import qrcode
import io
import base64
from datetime import datetime, timedelta

BASE_URL = "https://appverificapy.streamlit.app"

st.set_page_config(page_title="A.L.C.I. Segreteria", page_icon="🏢", layout="wide")

@st.cache_resource
def get_db():
    url = st.secrets["turso"]["url"]
    token = st.secrets["turso"]["token"]
    conn = libsql.connect("alci_local.db", sync_url=url, auth_token=token)
    conn.sync()
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stazioni (
            stazione_id TEXT PRIMARY KEY,
            ragione_sociale TEXT,
            citta TEXT,
            gps_lat REAL,
            gps_lon REAL,
            raggio_attivazione INTEGER DEFAULT 150,
            attiva BOOLEAN DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS certificati (
            code TEXT PRIMARY KEY,
            lotto TEXT,
            stato TEXT DEFAULT 'GENERATO',
            stazione_id TEXT,
            data_uso TIMESTAMP,
            targa TEXT,
            note TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_lotto ON certificati(lotto);
        CREATE INDEX IF NOT EXISTS idx_stato ON certificati(stato);
        CREATE INDEX IF NOT EXISTS idx_data_uso ON certificati(data_uso);
    """)
    conn.commit()
    conn.sync()
    return conn

db = init_db()

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

if page == "📊 Dashboard":
    st.markdown("""
        <div class='main-header'>
            <h1>📊 Dashboard Centrale</h1>
            <p>Panoramica sistema certificati A.L.C.I.</p>
        </div>
    """, unsafe_allow_html=True)
    
    tot = db.execute("SELECT count(*) FROM certificati").fetchone()[0]
    gen = db.execute("SELECT count(*) FROM certificati WHERE stato='GENERATO'").fetchone()[0]
    
    oggi = datetime.now().date()
    att_oggi = db.execute("SELECT count(*) FROM certificati WHERE stato='ATTIVO' AND date(data_uso)=?", (oggi.isoformat(),)).fetchone()[0]
    mese_inizio = oggi.replace(day=1)
    att_mese = db.execute("SELECT count(*) FROM certificati WHERE stato='ATTIVO' AND date(data_uso)>=?", (mese_inizio.isoformat(),)).fetchone()[0]
    anno_inizio = oggi.replace(month=1, day=1)
    att_anno = db.execute("SELECT count(*) FROM certificati WHERE stato='ATTIVO' AND date(data_uso)>=?", (anno_inizio.isoformat(),)).fetchone()[0]
    
    st.markdown(f"""
        <div class='kpi-grid'>
            <div class='kpi-card'>
                <div class='kpi-label'>Certificati Totali</div>
                <div class='kpi-value'>{format_number(tot)}</div>
            </div>
            <div class='kpi-card'>
                <div class='kpi-label'>Stampati</div>
                <div class='kpi-value'>{format_number(gen)}</div>
            </div>
            <div class='kpi-card'>
                <div class='kpi-label'>Attivati Oggi</div>
                <div class='kpi-value' style='color:#22c55e'>{format_number(att_oggi)}</div>
            </div>
            <div class='kpi-card'>
                <div class='kpi-label'>Attivati Questo Mese</div>
                <div class='kpi-value' style='color:#2563eb'>{format_number(att_mese)}</div>
            </div>
            <div class='kpi-card'>
                <div class='kpi-label'>Attivati Quest\'Anno</div>
                <div class='kpi-value' style='color:#f59e0b'>{format_number(att_anno)}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='section-title'>📋 Certificati Rimanenti per Stazione</div>", unsafe_allow_html=True)
    
    df_rim = pd.read_sql("""
        SELECT 
            s.stazione_id as "ID Stazione",
            s.ragione_sociale as "Stazione",
            COUNT(*) as Totale,
            SUM(CASE WHEN c.stato='GENERATO' THEN 1 ELSE 0 END) as Rimanenti,
            SUM(CASE WHEN c.stato='ATTIVO' THEN 1 ELSE 0 END) as Attivati,
            ROUND(SUM(CASE WHEN c.stato='ATTIVO' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as "% Utilizzo"
        FROM certificati c
        LEFT JOIN stazioni s ON c.stazione_id = s.stazione_id
        GROUP BY s.stazione_id, s.ragione_sociale
        ORDER BY Rimanenti DESC
    """, db)
    
    if not df_rim.empty:
        df_rim['Totale'] = df_rim['Totale'].apply(lambda x: format_number(int(x)))
        df_rim['Rimanenti'] = df_rim['Rimanenti'].apply(lambda x: format_number(int(x)))
        df_rim['Attivati'] = df_rim['Attivati'].apply(lambda x: format_number(int(x)))
        st.dataframe(df_rim, use_container_width=True, hide_index=True)

elif page == "📦 Gestione Lotti":
    st.markdown("""
        <div class='main-header'>
            <h1>📦 Gestione Lotti</h1>
            <p>Assegnazione range certificati per tipografia ModuloSei</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.info(f"💡 **Nota:** La tipografia stamperà QR code con URL: {BASE_URL}/?c=CODICE")
    
    st.markdown("<div class='section-title'>➕ Nuovo Lotto</div>", unsafe_allow_html=True)
    
    stazioni_df = pd.read_sql("SELECT stazione_id, ragione_sociale FROM stazioni WHERE attiva=1", db)
    
    if len(stazioni_df) == 0:
        st.error("❌ Nessuna stazione configurata.")
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
        
        ultimo = db.execute("SELECT code FROM certificati ORDER BY code DESC LIMIT 1").fetchone()
        ultimo_num = 0
        if ultimo:
            try:
                parts = ultimo["code"].split("-")
                ultimo_num = int(parts[-1])
            except:
                pass
        
        st.info(f"📊 **Ultimo numero globale:** {format_number(ultimo_num)}")
        
        st.markdown("#### 🔢 Range Assegnazione")
        
        col3, col4, col5 = st.columns([1, 1, 1])
        
        with col3:
            num_inizio = st.number_input("Numero inizio", min_value=ultimo_num + 1, value=ultimo_num + 1, step=1)
        with col4:
            num_fine = st.number_input("Numero fine", min_value=num_inizio, value=num_inizio + 999, step=1)
        with col5:
            quantita = num_fine - num_inizio + 1
            st.metric("Quantità", format_number(quantita))
        
        submitted = st.form_submit_button("🚀 Genera Lotto", type="primary", use_container_width=True)
        
        if submitted:
            if quantita <= 0:
                st.error("❌ Range non valido")
            else:
                lotto_id = f"LOT-{staz_sel}-{datetime.now().strftime('%y%m%d%H%M')}"
                
                rows = []
                for i in range(num_inizio, num_fine + 1):
                    code = f"{prefix}-{str(i).zfill(7)}"
                    rows.append((code, lotto_id, staz_sel, "GENERATO"))
                
                db.executemany(
                    "INSERT INTO certificati (code, lotto, stazione_id, stato) VALUES (?,?,?,?)",
                    rows
                )
                db.commit()
                db.sync()
                
                st.success(f"✅ **Lotto generato:** {format_number(quantita)} certificati")
                st.info(f"**ID Lotto:** `{lotto_id}`  \n**Range:** {format_number(num_inizio)} → {format_number(num_fine)}")
                
                st.markdown("---")
                st.markdown("### 📄 Istruzioni per Tipografia ModuloSei")
                
                primo_codice = f"{prefix}-{str(num_inizio).zfill(7)}"
                ultimo_codice = f"{prefix}-{str(num_fine).zfill(7)}"
                
                istruzioni_txt = f"""
ORDINE STAMPA CERTIFICATI A.L.C.I.

Range: {primo_codice} → {ultimo_codice}
Quantità: {format_number(quantita)} certificati
Stazione: {staz_sel}

QR CODE DA STAMPARE:
- URL base: {BASE_URL}/?c=CODICE_CERTIFICATO
- Esempio primo: {BASE_URL}/?c={primo_codice}
- Esempio ultimo: {BASE_URL}/?c={ultimo_codice}

IMPORTANTE:
Il QR code deve contenere l'URL completo con il codice del singolo certificato.
Ogni certificato deve avere il suo QR code univoco.
"""
                st.code(istruzioni_txt, language="text")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='section-title'>📋 Lotti Esistenti</div>", unsafe_allow_html=True)
    
    df_lotti = pd.read_sql("""
        SELECT 
            c.lotto as "ID Lotto",
            s.ragione_sociale as Stazione,
            MIN(c.code) as "Primo Codice",
            MAX(c.code) as "Ultimo Codice",
            COUNT(*) as Totale,
            SUM(CASE WHEN c.stato='GENERATO' THEN 1 ELSE 0 END) as "Non Attivati",
            SUM(CASE WHEN c.stato='ATTIVO' THEN 1 ELSE 0 END) as Attivati
        FROM certificati c
        LEFT JOIN stazioni s ON c.stazione_id = s.stazione_id
        GROUP BY c.lotto
        ORDER BY c.lotto DESC
    """, db)
    
    if not df_lotti.empty:
        df_lotti['Totale'] = df_lotti['Totale'].apply(lambda x: format_number(int(x)))
        df_lotti['Non Attivati'] = df_lotti['Non Attivati'].apply(lambda x: format_number(int(x)))
        df_lotti['Attivati'] = df_lotti['Attivati'].apply(lambda x: format_number(int(x)))
        st.dataframe(df_lotti, use_container_width=True, hide_index=True)

elif page == "🔍 QR Code":
    st.markdown("""
        <div class='main-header'>
            <h1>🔍 Visualizzazione QR Code</h1>
            <p>Genera anteprima QR per verificare la stampa</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.info(f"🌐 **URL Verifica Pubblica:** {BASE_URL}")
    
    st.markdown("### Genera QR Code di Test")
    
    code_search = st.text_input("Inserisci codice certificato", placeholder="ALCI-0000001")
    
    if code_search:
        cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_search.strip().upper(),)).fetchone()
        
        if cert:
            staz = db.execute("SELECT ragione_sociale FROM stazioni WHERE stazione_id=?", (cert['stazione_id'],)).fetchone()
            
            st.success(f"✅ Certificato trovato: **{cert['code']}**")
            st.info(f"Stazione: {staz['ragione_sociale'] if staz else cert['stazione_id']} | Stato: {cert['stato']}")
            
            qr_img = make_qr_image(cert['code'])
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(f"data:image/png;base64,{qr_img}", width=250)
            with col2:
                url = f"{BASE_URL}/?c={cert['code']}"
                st.markdown("**URL nel QR Code:**")
                st.code(url, language="text")
                
                st.markdown("**Istruzioni Tipografia:**")
                st.code(f"Stampare QR code con URL:\n{url}", language="text")
        else:
            st.error("❌ Certificato non trovato")
    
    st.markdown("---")
    st.markdown("### 📋 QR Code per Range")
    
    stazioni_df = pd.read_sql("SELECT stazione_id, ragione_sociale FROM stazioni WHERE attiva=1", db)
    
    if len(stazioni_df) > 0:
        staz_sel = st.selectbox(
            "Seleziona Stazione",
            stazioni_df["stazione_id"].tolist(),
            format_func=lambda x: stazioni_df[stazioni_df["stazione_id"]==x]["ragione_sociale"].values[0]
        )
        
        limit = st.slider("Numero certificati da visualizzare", 3, 20, 6)
        
        certs = pd.read_sql(f"""
            SELECT code, lotto, stato FROM certificati 
            WHERE stazione_id='{staz_sel}' 
            ORDER BY code 
            LIMIT {limit}
        """, db)
        
        if not certs.empty:
            st.markdown(f"**Mostrando {len(certs)} certificati:**")
            
            cols = st.columns(3)
            for idx, (_, cert) in enumerate(certs.iterrows()):
                with cols[idx % 3]:
                    qr_img = make_qr_image(cert['code'])
                    st.image(f"data:image/png;base64,{qr_img}", width=150)
                    st.caption(f"{cert['code']}")
                    st.caption(f"Stato: {cert['stato']}")

elif page == "🚨 Alert Sospetti":
    st.markdown("""
        <div class='main-header'>
            <h1>🚨 Certificati Sospetti</h1>
            <p>Monitoraggio attivazioni anomale</p>
        </div>
    """, unsafe_allow_html=True)
    
    limite_giorni = (datetime.now() - timedelta(days=7)).isoformat()
    
    df_vecchi = pd.read_sql(f"""
        SELECT 
            c.code as "Codice",
            s.ragione_sociale as "Stazione",
            datetime(c.data_uso) as "Data Attivazione",
            c.targa as "Targa",
            CAST((julianday('now') - julianday(c.data_uso)) as INTEGER) as "Giorni Fa"
        FROM certificati c
        LEFT JOIN stazioni s ON c.stazione_id = s.stazione_id
        WHERE c.stato='ATTIVO' AND c.data_uso < '{limite_giorni}'
        ORDER BY c.data_uso ASC
        LIMIT 50
    """, db)
    
    if not df_vecchi.empty:
        st.warning(f"⚠️ **{len(df_vecchi)} certificati** attivati da più di 7 giorni")
        
        st.markdown("### Certificati Datati (possibile riutilizzo)")
        st.dataframe(df_vecchi, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nessun certificato sospetto rilevato")
    
    st.markdown("---")
    st.markdown("### 📊 Statistiche Attivazioni per Giorno")
    
    df_daily = pd.read_sql("""
        SELECT 
            date(data_uso) as Data,
            COUNT(*) as Attivazioni
        FROM certificati
        WHERE stato='ATTIVO' AND data_uso >= date('now', '-30 days')
        GROUP BY date(data_uso)
        ORDER BY date(data_uso) DESC
    """, db)
    
    if not df_daily.empty:
        st.line_chart(df_daily.set_index("Data"))

elif page == "🏭 Stazioni":
    st.markdown("""
        <div class='main-header'>
            <h1>🏭 Rete Stazioni</h1>
            <p>Gestione stazioni di lavaggio</p>
        </div>
    """, unsafe_allow_html=True)
    
    df_staz = pd.read_sql("SELECT * FROM stazioni", db)
    
    if not df_staz.empty:
        st.dataframe(df_staz, use_container_width=True, hide_index=True)
    else:
        st.info("Nessuna stazione configurata")
    
    st.markdown("<div class='section-title'>➕ Aggiungi Stazione</div>", unsafe_allow_html=True)
    
    with st.form("add_staz"):
        col1, col2, col3 = st.columns(3)
        sid = col1.text_input("ID Stazione (solo numero)", placeholder="001")
        rag = col2.text_input("Ragione Sociale")
        citta = col3.text_input("Città")
        col4, col5 = st.columns(2)
        lat = col4.number_input("Latitudine", format="%.6f", value=45.584)
        lon = col5.number_input("Longitudine", format="%.6f", value=12.048)
        
        if st.form_submit_button("Aggiungi Stazione", type="primary"):
            try:
                db.execute("""
                    INSERT INTO stazioni (stazione_id, ragione_sociale, citta, gps_lat, gps_lon, attiva)
                    VALUES (?,?,?,?,?,1)
                """, (sid, rag, citta, lat, lon))
                db.commit()
                db.sync()
                st.success(f"✅ Stazione {sid} aggiunta")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Errore: {e}")

elif page == "🔧 Diagnostica DB":
    st.markdown("""
        <div class='main-header'>
            <h1>🔧 Diagnostica Database</h1>
            <p>Verifica e ripara inconsistenze</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🔍 Cerca Certificato")
    
    search_code = st.text_input("Inserisci codice certificato", placeholder="ALCI-0000002")
    
    if search_code:
        code_clean = search_code.strip().upper()
        
        # Forza sync prima di cercare
        db.sync()
        cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_clean,)).fetchone()
        
        if cert:
            st.success(f"✅ Certificato trovato: **{cert['code']}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Stato Attuale", cert['stato'])
                st.metric("Stazione", cert['stazione_id'])
                st.metric("Lotto", cert['lotto'])
            
            with col2:
                if cert['data_uso']:
                    data_str = datetime.fromisoformat(cert['data_uso']).strftime("%d/%m/%Y %H:%M")
                    st.metric("Data Attivazione", data_str)
                else:
                    st.metric("Data Attivazione", "Non attivato")
                
                st.metric("Targa", cert['targa'] or "Non specificata")
            
            st.markdown("---")
            st.markdown("### 🔧 Azioni Correttive")
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("🔄 Resetta a GENERATO", type="secondary"):
                    db.execute("""
                        UPDATE certificati 
                        SET stato='GENERATO', data_uso=NULL, targa=NULL, note=NULL
                        WHERE code=?
                    """, (code_clean,))
                    db.commit()
                    db.sync()
                    st.cache_resource.clear()
                    st.success("✅ Certificato resettato a GENERATO")
                    st.rerun()
            
            with col_b:
                if cert['stato'] == 'GENERATO':
                    if st.button("✅ Forza ATTIVO", type="primary"):
                        db.execute("""
                            UPDATE certificati 
                            SET stato='ATTIVO', data_uso=?
                            WHERE code=?
                        """, (datetime.now().isoformat(), code_clean))
                        db.commit()
                        db.sync()
                        st.cache_resource.clear()
                        st.success("✅ Certificato forzato ad ATTIVO")
                        st.rerun()
            
            with col_c:
                if st.button("🗑️ Elimina Certificato"):
                    conferma_elim = st.checkbox("Conferma eliminazione", key="conf_elim")
                    if conferma_elim:
                        db.execute("DELETE FROM certificati WHERE code=?", (code_clean,))
                        db.commit()
                        db.sync()
                        st.cache_resource.clear()
                        st.error("🗑️ Certificato eliminato")
                        st.rerun()
        
        else:
            st.error("❌ Certificato non trovato")
    
    st.markdown("---")
    st.markdown("### 🔧 Azioni Globali")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔄 Refresh Cache")
        if st.button("Pulisci Cache Streamlit", type="secondary"):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success("✅ Cache pulita! Ricarica la pagina.")
        
        if st.button("🔄 Sincronizza Database", type="primary"):
            db.sync()
            st.success("✅ Database sincronizzato con Turso!")
    
    with col2:
        st.markdown("#### 📊 Statistiche DB")
        tot = db.execute("SELECT COUNT(*) as c FROM certificati").fetchone()[0]
        gen = db.execute("SELECT COUNT(*) as c FROM certificati WHERE stato='GENERATO'").fetchone()[0]
        att = db.execute("SELECT COUNT(*) as c FROM certificati WHERE stato='ATTIVO'").fetchone()[0]
        
        st.metric("Totale Certificati", format_number(tot))
        st.metric("GENERATO", format_number(gen))
        st.metric("ATTIVO", format_number(att))
    
    st.markdown("---")
    st.markdown("### 🔍 Trova Duplicati o Inconsistenze")
    
    if st.button("🔎 Scansiona Database"):
        db.sync()
        
        null_stati = pd.read_sql("SELECT code, stazione_id FROM certificati WHERE stato IS NULL OR stato=''", db)
        if not null_stati.empty:
            st.warning(f"⚠️ Trovati {len(null_stati)} certificati con stato NULL")
            st.dataframe(null_stati)
        
        attivi_senza_data = pd.read_sql("SELECT code, stazione_id FROM certificati WHERE stato='ATTIVO' AND data_uso IS NULL", db)
        if not attivi_senza_data.empty:
            st.error(f"❌ Trovati {len(attivi_senza_data)} certificati ATTIVI senza data_uso")
            st.dataframe(attivi_senza_data)
            
            if st.button("🔧 Correggi Automaticamente"):
                db.execute("UPDATE certificati SET data_uso=? WHERE stato='ATTIVO' AND data_uso IS NULL", 
                          (datetime.now().isoformat(),))
                db.commit()
                db.sync()
                st.success("✅ Corretti!")
                st.rerun()
        
        generati_con_data = pd.read_sql("SELECT code, stazione_id, data_uso FROM certificati WHERE stato='GENERATO' AND data_uso IS NOT NULL", db)
        if not generati_con_data.empty:
            st.error(f"❌ Trovati {len(generati_con_data)} certificati GENERATI con data_uso")
            st.dataframe(generati_con_data)
            
            if st.button("🔧 Pulisci date"):
                db.execute("UPDATE certificati SET data_uso=NULL WHERE stato='GENERATO' AND data_uso IS NOT NULL")
                db.commit()
                db.sync()
                st.success("✅ Date pulite!")
                st.rerun()
        
        if null_stati.empty and attivi_senza_data.empty and generati_con_data.empty:
            st.success("✅ Nessuna inconsistenza trovata!")

elif page == "⚙️ Impostazioni":
    st.markdown("""
        <div class='main-header'>
            <h1>⚙️ Impostazioni</h1>
            <p>Gestione database e configurazione</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌐 Configurazione")
        st.info(f"**URL Verifica:** {BASE_URL}")
        st.success("**Database:** Turso Cloud (persistente)")
        st.caption("Per cambiare l'URL, modifica BASE_URL nel codice")
    
    with col2:
        st.markdown("### 🗑️ Reset Database")
        st.warning("⚠️ **ATTENZIONE:** Questa operazione cancellerà TUTTI i dati!")
        conferma = st.checkbox("Confermo di voler cancellare tutto")
        if conferma:
            if st.button("🗑️ RESET COMPLETO", type="secondary"):
                db.execute("DELETE FROM certificati")
                db.commit()
                db.sync()
                st.error("🗑️ Database resettato")
                st.rerun()
