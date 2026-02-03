import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import time
import base64

st.set_page_config(page_title="A.L.C.I. Verifica", page_icon="🔍", layout="centered")

# --- SUPABASE CONNECTION ---
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        return None

supabase: Client = init_supabase()

# --- FUNZIONE PER LEGGERE L'IMMAGINE IN HTML ---
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

# Convertiamo il logo per l'HTML
logo_b64 = get_img_as_base64("logo alci.jpg")

# --- CSS STYLES ---
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); }
    
    /* Stili Card */
    .verify-card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.12); max-width: 700px; margin: 30px auto; }
    .result-title { color: #16a34a; font-size: 28px; font-weight: 700; margin: 0 0 30px 0; text-align: center; }
    .info-item { margin: 20px 0; padding-bottom: 20px; border-bottom: 1px solid #e5e7eb; }
    .info-item:last-child { border-bottom: none; padding-bottom: 0; }
    .info-label { color: #6b7280; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
    .info-value { color: #1e293b; font-size: 18px; font-weight: 500; }
    
    /* Stili Messaggi */
    .error-title { color: #dc2626; font-size: 28px; font-weight: 700; margin: 0 0 20px 0; text-align: center; }
    .error-text { color: #7f1d1d; line-height: 1.8; text-align: center; font-size: 16px; }
    .warning-title { color: #d97706; font-size: 28px; font-weight: 700; margin: 0 0 20px 0; text-align: center; }
    .warning-text { color: #78350f; line-height: 1.8; text-align: center; font-size: 16px; }
    .alert-old { background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; border-radius: 8px; margin-top: 24px; }
    .alert-old-title { color: #dc2626; margin: 0 0 8px 0; font-weight: 700; font-size: 16px; }
    .alert-old-text { color: #7f1d1d; margin: 0; font-size: 14px; }

    /* HEADER PERSONALIZZATO (FLEXBOX) */
    .header-container {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px; /* Spazio tra logo e testo */
        padding: 20px 0;
    }
    .header-logo {
        width: 80px; /* Dimensione fissa logo */
        height: auto;
        flex-shrink: 0; /* Impedisce al logo di schiacciarsi */
    }
    .header-text {
        display: flex;
        flex-direction: column;
    }
    .header-title {
        color: #2563eb; 
        font-size: 38px; /* Un po' più piccolo per stare nel mobile */
        font-weight: 900; 
        letter-spacing: 2px; 
        line-height: 1;
        margin: 0;
    }
    .header-subtitle {
        color: #64748b; 
        font-size: 14px; 
        font-weight: 500;
        margin-top: 5px;
        line-height: 1.2;
    }
    
    /* Media query per schermi molto piccoli */
    @media (max-width: 400px) {
        .header-title { font-size: 32px; }
        .header-logo { width: 60px; }
    }
</style>
""", unsafe_allow_html=True)

# --- INTESTAZIONE HTML (FORZA RIGA UNICA) ---
# Se l'immagine c'è, la mostriamo, altrimenti mostriamo solo testo
img_tag = f'<img src="data:image/jpeg;base64,{logo_b64}" class="header-logo">' if logo_b64 else ''

st.markdown(f"""
<div class="header-container">
    {img_tag}
    <div class="header-text">
        <div class="header-title">A.L.C.I.</div>
        <div class="header-subtitle">Verifica Certificato<br>Lavaggio Cisterna</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- LOGICA DI VERIFICA ---
query_params = st.query_params
code_param = query_params.get("c", "")

if code_param:
    if not supabase:
         st.error("Errore connessione database")
         st.stop()

    with st.spinner("🔍 Verifica in corso..."):
        time.sleep(0.5)
        
        try:
            # Query Supabase
            response = supabase.table("certificati").select("*").eq("code", code_param).execute()
            cert = response.data[0] if response.data else None
            
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
            
            # Recupero info stazione
            staz_resp = supabase.table("stazioni").select("ragione_sociale, citta").eq("stazione_id", cert['stazione_id']).execute()
            staz = staz_resp.data[0] if staz_resp.data else None
            
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
                # Gestione formato data ISO da Supabase
                try:
                    data_att = datetime.fromisoformat(cert["data_uso"].replace('Z', '+00:00'))
                except:
                    try:
                        data_att = datetime.fromisoformat(cert["data_uso"])
                    except:
                        data_att = datetime.now() # Fallback

                data_att_str = data_att.strftime("%d/%m/%Y alle ore %H:%M")
                
                # Calcolo giorni
                try:
                    now_naive = datetime.now().replace(tzinfo=None)
                    data_att_naive = data_att.replace(tzinfo=None)
                    giorni_fa = (now_naive - data_att_naive).days
                except:
                    giorni_fa = 0

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
