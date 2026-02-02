import streamlit as st
import libsql_experimental as libsql
from datetime import datetime
import time

st.set_page_config(page_title="A.L.C.I. Verifica", page_icon="🔍", layout="centered")

@st.cache_resource
def get_db():
    url = st.secrets["turso"]["url"]
    token = st.secrets["turso"]["token"]
    conn = libsql.connect("alci_local.db", sync_url=url, auth_token=token)
    conn.sync()
    return conn

db = get_db()

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); }
    .logo-container { text-align: center; margin: 40px 0 20px 0; }
    .logo-title { color: #2563eb; font-size: 56px; font-weight: 900; letter-spacing: 6px; margin-bottom: 8px; }
    .subtitle { color: #64748b; font-size: 18px; margin-bottom: 0; }
    .verify-card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); max-width: 700px; margin: 30px auto; }
    .result-title { color: #16a34a; font-size: 28px; font-weight: 700; margin: 0 0 30px 0; text-align: center; }
    .info-item { margin: 20px 0; padding-bottom: 20px; border-bottom: 1px solid #e5e7eb; }
    .info-item:last-child { border-bottom: none; padding-bottom: 0; }
    .info-label { color: #6b7280; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .info-value { color: #1e293b; font-size: 18px; font-weight: 500; }
    .error-title { color: #dc2626; font-size: 28px; font-weight: 700; margin: 0 0 20px 0; text-align: center; }
    .error-text { color: #7f1d1d; line-height: 1.8; text-align: center; font-size: 16px; }
    .warning-title { color: #d97706; font-size: 28px; font-weight: 700; margin: 0 0 20px 0; text-align: center; }
    .warning-text { color: #78350f; line-height: 1.8; text-align: center; font-size: 16px; }
    .alert-old { background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; border-radius: 8px; margin-top: 24px; }
    .alert-old-title { color: #dc2626; margin: 0 0 8px 0; font-weight: 700; font-size: 16px; }
    .alert-old-text { color: #7f1d1d; margin: 0; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class='logo-container'>
    <div class='logo-title'>🔍 A.L.C.I.</div>
    <div class='subtitle'>Verifica Certificato Lavaggio Cisterna</div>
</div>
""", unsafe_allow_html=True)

query_params = st.query_params
code_param = query_params.get("c", "")

if code_param:
    with st.spinner("🔍 Verifica in corso..."):
        time.sleep(0.5)
        
        try:
            cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_param,)).fetchone()
            
            if not cert:
                html_error = f"""
<div class='verify-card'>
    <div class='error-title'>❌ CERTIFICATO NON VALIDO</div>
    <div class='error-text'>
        <strong>Codice:</strong> {code_param}<br><br>
        Il numero di serie non esiste nel database A.L.C.I.<br>
        Possibile contraffazione.
    </div>
</div>
"""
                st.markdown(html_error, unsafe_allow_html=True)
                st.stop()
            
            staz = db.execute("SELECT ragione_sociale, citta FROM stazioni WHERE stazione_id=?", (cert['stazione_id'],)).fetchone()
            stazione_info = f"{staz['ragione_sociale']} ({staz['citta']})" if staz else cert['stazione_id']

            if cert["stato"] == "GENERATO":
                html_warning = f"""
<div class='verify-card'>
    <div class='warning-title'>⚠️ CERTIFICATO NON ATTIVATO</div>
    <div class='warning-text'>
        <strong>Codice:</strong> {cert['code']}<br>
        <strong>Stazione:</strong> {stazione_info}<br>
        <strong>Lotto:</strong> {cert['lotto']}<br><br>
        Questo certificato non è ancora stato attivato dalla stazione di lavaggio.
    </div>
</div>
"""
                st.markdown(html_warning, unsafe_allow_html=True)
            
            elif cert["stato"] == "ATTIVO":
                data_att = datetime.fromisoformat(cert["data_uso"])
                data_att_str = data_att.strftime("%d/%m/%Y alle ore %H:%M")
                giorni_fa = (datetime.now() - data_att).days
                targa_info = cert['targa'] if cert['targa'] else 'Non specificata'
                
                alert_html = ""
                if giorni_fa > 7:
                    alert_html = f"""
<div class='alert-old'>
    <div class='alert-old-title'>⚠️ ATTENZIONE: Certificato attivato {giorni_fa} giorni fa</div>
    <div class='alert-old-text'>Verificare che il lavaggio sia recente. Possibile riutilizzo improprio.</div>
</div>
"""
                
                html_success = f"""
<div class='verify-card'>
    <div class='result-title'>✅ CERTIFICATO VALIDO E ATTIVO</div>
    <div class='info-item'>
        <div class='info-label'>Codice Certificato</div>
        <div class='info-value'>{cert['code']}</div>
    </div>
    <div class='info-item'>
        <div class='info-label'>Stazione di Lavaggio</div>
        <div class='info-value'>{stazione_info}</div>
    </div>
    <div class='info-item'>
        <div class='info-label'>Data e Ora Attivazione</div>
        <div class='info-value' style='font-weight:600;'>{data_att_str}</div>
    </div>
    <div class='info-item'>
        <div class='info-label'>Targa Veicolo</div>
        <div class='info-value'>{targa_info}</div>
    </div>
    <div class='info-item'>
        <div class='info-label'>Lotto</div>
        <div class='info-value'>{cert['lotto']}</div>
    </div>
    {alert_html}
</div>
"""
                st.markdown(html_success, unsafe_allow_html=True)

        except Exception as e:
            st.markdown(f"""
<div class='verify-card'>
    <div class='error-title'>❌ ERRORE DI SISTEMA</div>
    <div class='error-text'>Si è verificato un errore tecnico:<br>{str(e)}</div>
</div>
""", unsafe_allow_html=True)

else:
    st.info("📱 Scansiona il QR code sul certificato per verificarne l'autenticità")
