import streamlit as st
import pandas as pd
import libsql_experimental as libsql
from datetime import datetime
from PIL import Image

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False

st.set_page_config(page_title="A.L.C.I. Stazione", page_icon="🏭", layout="centered")

@st.cache_resource
def get_db():
    url = st.secrets["turso"]["url"]
    token = st.secrets["turso"]["token"]
    conn = libsql.connect("alci_local.db", sync_url=url, auth_token=token)
    conn.sync()
    return conn

db = get_db()

def format_number(n):
    return f"{n:,}".replace(",", ".")

st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    .main-container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .header-box {
        background: white; padding: 24px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px;
        border-left: 4px solid #2563eb;
    }
    .header-box h1 { margin: 0; font-size: 24px; color: #1e293b; font-weight: 600; }
    .header-box p { margin: 4px 0 0; color: #64748b; font-size: 14px; }
    .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
    .stat-card {
        background: white; padding: 20px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); text-align: center;
    }
    .stat-label {
        font-size: 12px; color: #64748b; text-transform: uppercase;
        letter-spacing: 0.5px; margin-bottom: 8px; font-weight: 600;
    }
    .stat-value { font-size: 32px; font-weight: 700; color: #1e293b; }
    .action-box {
        background: white; padding: 24px; border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 16px;
    }
    .success-alert {
        background: #f0fdf4; border: 1px solid #86efac; border-left: 4px solid #22c55e;
        padding: 16px; border-radius: 8px; margin: 16px 0;
    }
    .success-alert h3 { color: #15803d; margin: 0 0 8px; font-size: 16px; }
    .error-alert {
        background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444;
        padding: 16px; border-radius: 8px; margin: 16px 0;
    }
    .warning-alert {
        background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b;
        padding: 16px; border-radius: 8px; margin: 16px 0;
    }
    .stButton>button {
        width: 100%; border-radius: 8px; padding: 12px 24px;
        font-weight: 600; font-size: 15px;
    }
</style>
""", unsafe_allow_html=True)

if "stazione_logged" not in st.session_state:
    st.session_state.stazione_logged = None

if not st.session_state.stazione_logged:
    st.markdown("<div class='main-container'>", unsafe_allow_html=True)
    st.markdown("""
        <div class='header-box'>
            <h1>🏭 A.L.C.I. - Attivazione Certificati</h1>
            <p>Sistema di gestione lavaggio cisterne</p>
        </div>
    """, unsafe_allow_html=True)
    
    stazioni = pd.read_sql("SELECT stazione_id, ragione_sociale FROM stazioni WHERE attiva=1", db)
    
    if len(stazioni) == 0:
        st.error("❌ Nessuna stazione disponibile")
        st.stop()
    
    st.markdown("<div class='action-box'>", unsafe_allow_html=True)
    sel = st.selectbox(
        "Seleziona la tua stazione",
        stazioni["stazione_id"].tolist(),
        format_func=lambda x: stazioni[stazioni["stazione_id"]==x]["ragione_sociale"].values[0]
    )
    pwd = st.text_input("Password", type="password")
    
    if st.button("🔓 Accedi", type="primary"):
        if pwd == "lavaggio123":
            st.session_state.stazione_logged = sel
            st.rerun()
        else:
            st.error("❌ Password errata")
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.stop()

staz = db.execute("SELECT * FROM stazioni WHERE stazione_id=?", (st.session_state.stazione_logged,)).fetchone()

st.markdown("<div class='main-container'>", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    st.markdown(f"""
        <div class='header-box'>
            <h1>🏭 {staz['ragione_sociale']}</h1>
            <p>{staz['citta']}</p>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Esci"):
        st.session_state.stazione_logged = None
        st.rerun()

tot = db.execute("SELECT count(*) FROM certificati WHERE stazione_id=?", (staz['stazione_id'],)).fetchone()[0]
att = db.execute("SELECT count(*) FROM certificati WHERE stazione_id=? AND stato='ATTIVO'", (staz['stazione_id'],)).fetchone()[0]
disponibili = tot - att

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

with tab1:
    st.markdown("### Scansiona il QR Code del certificato")
    
    if not PYZBAR_AVAILABLE:
        st.error("❌ **Libreria pyzbar non installata**")
        st.code("pip install pyzbar pillow", language="bash")
    else:
        uploaded_file = st.file_uploader(
            "📸 Scatta o carica una foto del QR code",
            type=["jpg", "jpeg", "png"],
            help="Usa la fotocamera del dispositivo per scattare una foto del QR code sul certificato"
        )
        
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Foto caricata", width=300)
            
            decoded = pyzbar.decode(image)
            
            if decoded:
                qr_data = decoded[0].data.decode('utf-8')
                
                try:
                    if "?c=" in qr_data:
                        code = qr_data.split("?c=")[1].split("&")[0]
                    else:
                        st.error("❌ Formato QR non valido")
                        st.stop()
                    
                    cert = db.execute("SELECT * FROM certificati WHERE code=?", (code,)).fetchone()
                    
                    if not cert:
                        st.markdown(f"""
                            <div class='error-alert'>
                                <h3>❌ Certificato non trovato</h3>
                                <p>Codice: <strong>{code}</strong><br>
                                Il certificato non esiste nel database</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.stop()
                    
                    if cert["stazione_id"] != staz["stazione_id"]:
                        st.markdown(f"""
                            <div class='error-alert'>
                                <h3>❌ Certificato non valido</h3>
                                <p>Questo certificato è assegnato alla stazione: <strong>{cert['stazione_id']}</strong></p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.stop()
                    
                    if cert["stato"] == "ATTIVO":
                        data_att = datetime.fromisoformat(cert["data_uso"]).strftime("%d/%m/%Y alle %H:%M")
                        st.markdown(f"""
                            <div class='warning-alert'>
                                <h3>⚠️ Certificato già attivato</h3>
                                <p><strong>Data:</strong> {data_att}<br>
                                <strong>Targa:</strong> {cert['targa'] or 'Non specificata'}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.stop()
                    
                    st.markdown(f"""
                        <div class='success-alert'>
                            <h3>✅ Certificato Valido</h3>
                            <p><strong>Codice:</strong> {cert['code']}<br>
                            <strong>Lotto:</strong> {cert['lotto']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    with st.form("attiva_qr"):
                        st.markdown("#### Dati lavaggio (opzionali)")
                        targa = st.text_input("🚛 Targa veicolo", max_chars=12)
                        note = st.text_area("Note", max_chars=200)
                        
                        if st.form_submit_button("🔓 ATTIVA CERTIFICATO", type="primary"):
                            db.execute("""
                                UPDATE certificati 
                                SET stato='ATTIVO', data_uso=?, targa=?, note=?
                                WHERE code=?
                            """, (datetime.now().isoformat(), targa.upper().strip() if targa else None, note or None, cert['code']))
                            db.commit()
                            db.sync()
                            st.success(f"✅ Certificato {cert['code']} attivato!")
                            st.rerun()
                    
                except Exception as e:
                    st.error(f"Errore lettura QR: {e}")
            else:
                st.warning("⚠️ Nessun QR Code trovato nell'immagine. Riprova con una foto più nitida.")

with tab2:
    st.markdown("### Inserisci il codice del certificato")
    
    if "cert_to_activate" not in st.session_state:
        st.session_state.cert_to_activate = None
    
    code_input = st.text_input(
        "Codice Certificato",
        placeholder="Es: ALCI-0000001",
        help="Il codice è stampato sul certificato",
        key="code_input"
    )
    
    if st.button("🔍 Cerca Certificato", type="secondary"):
        if code_input:
            code_clean = code_input.strip().upper()
            cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_clean,)).fetchone()
            
            if not cert:
                st.markdown("""
                    <div class='error-alert'>
                        <h3>❌ Certificato non trovato</h3>
                        <p>Il codice inserito non esiste nel database</p>
                    </div>
                """, unsafe_allow_html=True)
                st.session_state.cert_to_activate = None
            
            elif cert["stazione_id"] != staz["stazione_id"]:
                st.markdown(f"""
                    <div class='error-alert'>
                        <h3>❌ Certificato non valido</h3>
                        <p>Questo certificato è assegnato alla stazione: <strong>{cert['stazione_id']}</strong></p>
                    </div>
                """, unsafe_allow_html=True)
                st.session_state.cert_to_activate = None
            
            elif cert["stato"] == "ATTIVO":
                data_att = datetime.fromisoformat(cert["data_uso"]).strftime("%d/%m/%Y alle %H:%M")
                st.markdown(f"""
                    <div class='warning-alert'>
                        <h3>⚠️ Certificato già attivato</h3>
                        <p><strong>Data:</strong> {data_att}<br>
                        <strong>Targa:</strong> {cert['targa'] or 'Non specificata'}</p>
                    </div>
                """, unsafe_allow_html=True)
                st.session_state.cert_to_activate = None
            
            else:
                st.session_state.cert_to_activate = dict(cert)
                st.rerun()
        else:
            st.warning("⚠️ Inserisci un codice certificato")
    
    if st.session_state.cert_to_activate:
        cert = st.session_state.cert_to_activate
        
        st.markdown(f"""
            <div class='success-alert'>
                <h3>✅ Certificato Valido</h3>
                <p><strong>Codice:</strong> {cert['code']}<br>
                <strong>Lotto:</strong> {cert['lotto']}</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("attiva_cert_manual"):
            st.markdown("#### Dati lavaggio (opzionali)")
            targa = st.text_input("🚛 Targa veicolo", max_chars=12)
            note = st.text_area("Note", max_chars=200)
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.form_submit_button("🔓 ATTIVA CERTIFICATO", type="primary"):
                    db.execute("""
                        UPDATE certificati 
                        SET stato='ATTIVO', data_uso=?, targa=?, note=?
                        WHERE code=?
                    """, (datetime.now().isoformat(), targa.upper().strip() if targa else None, note or None, cert['code']))
                    db.commit()
                    db.sync()
                    st.session_state.cert_to_activate = None
                    st.success(f"✅ Certificato {cert['code']} attivato!")
                    st.rerun()
            
            with col_b:
                if st.form_submit_button("❌ Annulla"):
                    st.session_state.cert_to_activate = None
                    st.rerun()

with tab3:
    st.markdown("### Ultimi certificati attivati")
    df = pd.read_sql(f"""
        SELECT 
            code as "Codice",
            targa as "Targa",
            datetime(data_uso) as "Data Attivazione",
            note as "Note"
        FROM certificati
        WHERE stazione_id='{staz['stazione_id']}' AND stato='ATTIVO'
        ORDER BY data_uso DESC
        LIMIT 50
    """, db)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("📋 Nessuna attivazione registrata")

st.markdown("</div></div>", unsafe_allow_html=True)
