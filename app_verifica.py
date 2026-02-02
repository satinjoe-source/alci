# app_verifica.py
import streamlit as st
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="ALCI Verifica", page_icon="🔍", layout="centered")

@st.cache_resource
def get_db():
    conn = sqlite3.connect("alci.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

db = get_db()

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); }
    .verify-card {
        background: white; padding: 32px; border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12); max-width: 600px; margin: 40px auto;
    }
    .success-box {
        background: #f0fdf4; border: 1px solid #86efac; border-left: 4px solid #22c55e;
        padding: 20px; border-radius: 12px; margin: 20px 0;
    }
    .error-box {
        background: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444;
        padding: 20px; border-radius: 12px; margin: 20px 0;
    }
    .warning-box {
        background: #fffbeb; border: 1px solid #fde68a; border-left: 4px solid #f59e0b;
        padding: 20px; border-radius: 12px; margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

params = st.query_params
code_param = params.get("c", "")

st.markdown("""
    <div class='verify-card'>
        <h1 style='text-align:center; color:#2563eb; margin-bottom:8px;'>🔍 ALCI</h1>
        <p style='text-align:center; color:#64748b; margin-bottom:32px;'>Verifica Certificato Lavaggio Cisterna</p>
    </div>
""", unsafe_allow_html=True)

if not code_param:
    st.info("📱 Scansiona il QR code sul certificato per verificarne l'autenticità")
    st.stop()

try:
    cert = db.execute("SELECT * FROM certificati WHERE code=?", (code_param,)).fetchone()
    
    if not cert:
        st.markdown(f"""
            <div class='error-box'>
                <h2 style='color:#dc2626; margin:0 0 12px;'>❌ CERTIFICATO NON VALIDO</h2>
                <p style='color:#7f1d1d; margin:0;'><strong>Codice:</strong> {code_param}<br><br>
                Il numero di serie non esiste nel database ALCI.<br>
                Possibile contraffazione.</p>
            </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    staz = db.execute("SELECT ragione_sociale, citta FROM stazioni WHERE stazione_id=?", (cert['stazione_id'],)).fetchone()
    
    if cert["stato"] == "GENERATO":
        st.markdown(f"""
            <div class='warning-box'>
                <h2 style='color:#d97706; margin:0 0 12px;'>⚠️ CERTIFICATO NON ATTIVATO</h2>
                <p style='color:#78350f;'><strong>Codice:</strong> {cert['code']}<br>
                <strong>Stazione:</strong> {staz['ragione_sociale']} ({staz['citta']}) if staz else cert['stazione_id']<br>
                <strong>Lotto:</strong> {cert['lotto']}<br><br>
                Questo certificato non è ancora stato attivato dalla stazione di lavaggio.</p>
            </div>
        """, unsafe_allow_html=True)
    
    elif cert["stato"] == "ATTIVO":
        data_att = datetime.fromisoformat(cert["data_uso"])
        data_att_str = data_att.strftime("%d/%m/%Y alle ore %H:%M")
        giorni_fa = (datetime.now() - data_att).days
        
        # Alert se certificato vecchio (>7 giorni)
        alert_vecchio = ""
        if giorni_fa > 7:
            alert_vecchio = f"""
            <div style='background:#fef2f2; border:1px solid #fecaca; padding:12px; border-radius:8px; margin-top:16px;'>
                <p style='color:#dc2626; margin:0; font-weight:600;'>
                    ⚠️ ATTENZIONE: Certificato attivato {giorni_fa} giorni fa
                </p>
                <p style='color:#7f1d1d; margin:8px 0 0; font-size:14px;'>
                    Verificare che il lavaggio sia recente. Possibile riutilizzo improprio.
                </p>
            </div>
            """
        
        st.markdown(f"""
            <div class='success-box'>
                <h2 style='color:#16a34a; margin:0 0 16px;'>✅ CERTIFICATO VALIDO E ATTIVO</h2>
                <div style='color:#14532d; line-height:1.8;'>
                    <p style='margin:8px 0;'><strong>Codice Certificato:</strong><br>
                    <code style='background:#fff; padding:4px 8px; border-radius:4px; font-size:16px;'>{cert['code']}</code></p>
                    
                    <p style='margin:8px 0;'><strong>Stazione di Lavaggio:</strong><br>
                    {staz['ragione_sociale']} ({staz['citta']}) if staz else cert['stazione_id']</p>
                    
                    <p style='margin:8px 0;'><strong>Data e Ora Attivazione:</strong><br>
                    <span style='font-size:18px; font-weight:600;'>{data_att_str}</span></p>
                    
                    <p style='margin:8px 0;'><strong>Targa Veicolo:</strong><br>
                    {cert['targa'] or 'Non specificata'}</p>
                    
                    <p style='margin:8px 0;'><strong>Lotto:</strong><br>{cert['lotto']}</p>
                </div>
                {alert_vecchio}
            </div>
        """, unsafe_allow_html=True)
        
        if giorni_fa <= 7:
            st.balloons()

except Exception as e:
    st.error(f"Errore: {e}")