# app_verifica.py
import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="A.L.C.I. Verifica", page_icon="🔍", layout="centered")

@st.cache_resource
def get_db():
    conn = sqlite3.connect("alci.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db = get_db()

st.markdown("""
<style>
    .stApp { 
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); 
    }
    .verify-card {
        background: white; 
        padding: 40px; 
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12); 
        max-width: 700px; 
        margin: 60px auto;
    }
    .logo-title {
        text-align: center; 
        color: #2563eb; 
        font-size: 48px;
        font-weight: 900;
        margin-bottom: 8px;
        letter-spacing: 4px;
    }
    .subtitle {
        text-align: center; 
        color: #64748b; 
        font-size: 16px;
        margin-bottom: 40px;
    }
    .success-box {
        background: #f0fdf4; 
        border: 2px solid #86efac; 
        border-radius: 12px;
        padding: 24px; 
        margin: 20px 0;
    }
    .success-title {
        color: #16a34a; 
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 16px 0;
    }
    .info-row {
        color: #14532d; 
        line-height: 2;
        margin: 12px 0;
    }
    .info-label {
        font-weight: 600;
        display: block;
        margin-bottom: 4px;
    }
    .info-value {
        background: #fff; 
        padding: 8px 12px; 
        border-radius: 6px;
        font-size: 16px;
        display: inline-block;
    }
    .error-box {
        background: #fef2f2; 
        border: 2px solid #fecaca; 
        border-radius: 12px;
        padding: 24px; 
        margin: 20px 0;
    }
    .error-title {
        color: #dc2626; 
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 12px 0;
    }
    .error-text {
        color: #7f1d1d; 
        margin: 0;
        line-height: 1.6;
    }
    .warning-box {
        background: #fffbeb; 
        border: 2px solid #fde68a; 
        border-radius: 12px;
        padding: 24px; 
        margin: 20px 0;
    }
    .warning-title {
        color: #d97706; 
        font-size: 24px;
        font-weight: 700;
        margin: 0 0 12px 0;
    }
    .warning-text {
        color: #78350f;
        line-height: 1.6;
    }
    .alert-old {
        background: #fef2f2; 
        border: 1px solid #fecaca; 
        padding: 16px; 
        border-radius: 8px; 
        margin-top: 20px;
    }
    .alert-old-title {
        color: #dc2626; 
        margin: 0; 
        font-weight: 600;
        font-size: 16px;
    }
    .alert-old-text {
        color: #7f1d1d; 
        margin: 8px 0 0; 
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

params = st.query_params
code_param = params.get("c", "")

# Header
st.markdown('<div class="verify-card">', unsafe_allow_html=True)
st.markdown('<div class="logo-title">🔍 A.L.C.I.</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Verifica Certificato Lavaggio Cisterna</div>', unsafe_allow_html=True)

if not code_param:
    st.info("📱 Scansiona il QR code sul certificato per verificarne l'autenticità")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Spinner durante la verifica
with st.spinner("🔍 Verifica in corso..."):
    time.sleep(0.5)  # Simula caricamento per UX migliore
    
    try:
        cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_param,)).fetchone()
        
        if not cert:
            st.markdown(f"""
                <div class='error-box'>
                    <div class='error-title'>❌ CERTIFICATO NON VALIDO</div>
                    <div class='error-text'>
                        <strong>Codice:</strong> {code_param}<br><br>
                        Il numero di serie non esiste nel database A.L.C.I.<br>
                        Possibile contraffazione.
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.stop()
        
        staz = db.execute("SELECT ragione_sociale, citta FROM stazioni WHERE stazione_id=?", (cert['stazione_id'],)).fetchone()
        
        if cert["stato"] == "GENERATO":
            stazione_info = f"{staz['ragione_sociale']} ({staz['citta']})" if staz else cert['stazione_id']
            
            st.markdown(f"""
                <div class='warning-box'>
                    <div class='warning-title'>⚠️ CERTIFICATO NON ATTIVATO</div>
                    <div class='warning-text'>
                        <div style='margin-bottom:12px;'><strong>Codice:</strong> <code style='background:#fff; padding:4px 8px; border-radius:4px;'>{cert['code']}</code></div>
                        <div style='margin-bottom:12px;'><strong>Stazione:</strong> {stazione_info}</div>
                        <div style='margin-bottom:12px;'><strong>Lotto:</strong> {cert['lotto']}</div>
                        <div style='margin-top:20px;'>Questo certificato non è ancora stato attivato dalla stazione di lavaggio.</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        
        elif cert["stato"] == "ATTIVO":
            data_att = datetime.fromisoformat(cert["data_uso"])
            data_att_str = data_att.strftime("%d/%m/%Y alle ore %H:%M")
            giorni_fa = (datetime.now() - data_att).days
            
            stazione_info = f"{staz['ragione_sociale']} ({staz['citta']})" if staz else cert['stazione_id']
            
            # Alert se vecchio
            alert_vecchio = ""
            if giorni_fa > 7:
                alert_vecchio = f"""
                <div class='alert-old'>
                    <div class='alert-old-title'>⚠️ ATTENZIONE: Certificato attivato {giorni_fa} giorni fa</div>
                    <div class='alert-old-text'>Verificare che il lavaggio sia recente. Possibile riutilizzo improprio.</div>
                </div>
                """
            
            st.markdown(f"""
                <div class='success-box'>
                    <div class='success-title'>✅ CERTIFICATO VALIDO E ATTIVO</div>
                    
                    <div class='info-row'>
                        <span class='info-label'>Codice Certificato:</span>
                        <code class='info-value'>{cert['code']}</code>
                    </div>
                    
                    <div class='info-row'>
                        <span class='info-label'>Stazione di Lavaggio:</span>
                        <span class='info-value'>{stazione_info}</span>
                    </div>
                    
                    <div class='info-row'>
                        <span class='info-label'>Data e Ora Attivazione:</span>
                        <span class='info-value' style='font-weight:600; font-size:18px;'>{data_att_str}</span>
                    </div>
                    
                    <div class='info-row'>
                        <span class='info-label'>Targa Veicolo:</span>
                        <span class='info-value'>{cert['targa'] or 'Non specificata'}</span>
                    </div>
                    
                    <div class='info-row'>
                        <span class='info-label'>Lotto:</span>
                        <span class='info-value'>{cert['lotto']}</span>
                    </div>
                    
                    {alert_vecchio}
                </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"""
            <div class='error-box'>
                <div class='error-title'>❌ ERRORE</div>
                <div class='error-text'>Si è verificato un errore durante la verifica: {str(e)}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
