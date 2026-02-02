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
    .result-box {
        background: #f0fdf4; 
        border: 2px solid #86efac; 
        border-radius: 12px;
        padding: 28px; 
        margin: 24px 0;
    }
    .result-title {
        color: #16a34a; 
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 24px 0;
        text-align: center;
    }
    .info-item {
        margin: 16px 0;
        padding: 12px 0;
        border-bottom: 1px solid #d1fae5;
    }
    .info-item:last-child {
        border-bottom: none;
    }
    .info-label {
        color: #14532d; 
        font-weight: 600;
        font-size: 14px;
        display: block;
        margin-bottom: 6px;
    }
    .info-value {
        background: white; 
        padding: 10px 14px; 
        border-radius: 6px;
        font-size: 16px;
        color: #1e293b;
        display: block;
    }
    .error-box {
        background: #fef2f2; 
        border: 2px solid #fecaca; 
        border-radius: 12px;
        padding: 28px; 
        margin: 24px 0;
    }
    .error-title {
        color: #dc2626; 
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 16px 0;
        text-align: center;
    }
    .error-text {
        color: #7f1d1d; 
        margin: 0;
        line-height: 1.8;
        text-align: center;
    }
    .warning-box {
        background: #fffbeb; 
        border: 2px solid #fde68a; 
        border-radius: 12px;
        padding: 28px; 
        margin: 24px 0;
    }
    .warning-title {
        color: #d97706; 
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 16px 0;
        text-align: center;
    }
    .warning-text {
        color: #78350f;
        line-height: 1.8;
        text-align: center;
    }
    .alert-old {
        background: #fee; 
        border-left: 4px solid #dc2626; 
        padding: 16px; 
        border-radius: 8px; 
        margin-top: 24px;
    }
    .alert-old-title {
        color: #dc2626; 
        margin: 0 0 8px 0; 
        font-weight: 700;
        font-size: 16px;
    }
    .alert-old-text {
        color: #7f1d1d; 
        margin: 0; 
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

params = st.query_params
code_param = params.get("c", "")

# Spinner durante la verifica
if code_param:
    with st.spinner("🔍 Verifica certificato in corso..."):
        time.sleep(0.8)
        
        try:
            cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_param,)).fetchone()
            
            if not cert:
                # CERTIFICATO NON TROVATO
                st.markdown(f"""
                    <div class='verify-card'>
                        <div class='logo-title'>🔍 A.L.C.I.</div>
                        <div class='subtitle'>Verifica Certificato Lavaggio Cisterna</div>
                        
                        <div class='error-box'>
                            <div class='error-title'>❌ CERTIFICATO NON VALIDO</div>
                            <div class='error-text'>
                                <strong>Codice:</strong> {code_param}<br><br>
                                Il numero di serie non esiste nel database A.L.C.I.<br>
                                Possibile contraffazione.
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                st.stop()
            
            staz = db.execute("SELECT ragione_sociale, citta FROM stazioni WHERE stazione_id=?", (cert['stazione_id'],)).fetchone()
            
            if cert["stato"] == "GENERATO":
                # CERTIFICATO NON ATTIVATO
                stazione_info = f"{staz['ragione_sociale']} ({staz['citta']})" if staz else cert['stazione_id']
                
                st.markdown(f"""
                    <div class='verify-card'>
                        <div class='logo-title'>🔍 A.L.C.I.</div>
                        <div class='subtitle'>Verifica Certificato Lavaggio Cisterna</div>
                        
                        <div class='warning-box'>
                            <div class='warning-title'>⚠️ CERTIFICATO NON ATTIVATO</div>
                            <div class='warning-text'>
                                <strong>Codice:</strong> {cert['code']}<br>
                                <strong>Stazione:</strong> {stazione_info}<br>
                                <strong>Lotto:</strong> {cert['lotto']}<br><br>
                                Questo certificato non è ancora stato attivato dalla stazione di lavaggio.
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            elif cert["stato"] == "ATTIVO":
                # CERTIFICATO ATTIVO
                data_att = datetime.fromisoformat(cert["data_uso"])
                data_att_str = data_att.strftime("%d/%m/%Y alle ore %H:%M")
                giorni_fa = (datetime.now() - data_att).days
                
                stazione_info = f"{staz['ragione_sociale']} ({staz['citta']})" if staz else cert['stazione_id']
                targa_info = cert['targa'] if cert['targa'] else 'Non specificata'
                
                # Alert se vecchio
                alert_html = ""
                if giorni_fa > 7:
                    alert_html = f"""
                    <div class='alert-old'>
                        <div class='alert-old-title'>⚠️ ATTENZIONE: Certificato attivato {giorni_fa} giorni fa</div>
                        <div class='alert-old-text'>Verificare che il lavaggio sia recente. Possibile riutilizzo improprio.</div>
                    </div>
                    """
                
                st.markdown(f"""
                    <div class='verify-card'>
                        <div class='logo-title'>🔍 A.L.C.I.</div>
                        <div class='subtitle'>Verifica Certificato Lavaggio Cisterna</div>
                        
                        <div class='result-box'>
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
                                <div class='info-value' style='font-weight:600; font-size:18px;'>{data_att_str}</div>
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
                    </div>
                """, unsafe_allow_html=True)

        except Exception as e:
            st.markdown(f"""
                <div class='verify-card'>
                    <div class='logo-title'>🔍 A.L.C.I.</div>
                    <div class='subtitle'>Verifica Certificato Lavaggio Cisterna</div>
                    
                    <div class='error-box'>
                        <div class='error-title'>❌ ERRORE</div>
                        <div class='error-text'>Si è verificato un errore durante la verifica:<br>{str(e)}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

else:
    # NESSUN CODICE FORNITO
    st.markdown("""
        <div class='verify-card'>
            <div class='logo-title'>🔍 A.L.C.I.</div>
            <div class='subtitle'>Verifica Certificato Lavaggio Cisterna</div>
        </div>
    """, unsafe_allow_html=True)
    st.info("📱 Scansiona il QR code sul certificato per verificarne l'autenticità")
