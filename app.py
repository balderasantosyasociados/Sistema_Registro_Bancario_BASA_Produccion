import os
import json
import uuid
import hashlib
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Sistema de Registro Bancario BASA",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "Sistema de Registro Bancario BASA"
AUDIT_NAME = "Audit Intelligence USA"
COMPANY_NAME = "Baldera Santos & Asociados SRL"
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "basa_banking_registry.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

st.markdown("""
<style>
.main { background:#f5f7fa; }
.block-container { max-width:1500px; padding-top:1.5rem; }
.basa-header { padding:24px 30px; border-radius:16px; background:linear-gradient(135deg,#0b1f33,#123b5d); color:#fff; margin-bottom:20px; }
.basa-header h1 { margin:0; font-size:30px; }
.metric-card { background:#fff; padding:18px; border-radius:14px; border:1px solid #e4e8ed; }
.footer { margin-top:40px; padding:20px; text-align:center; color:#667085; border-top:1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"{salt}${digest.hex()}"

def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
        calculated = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
        return secrets.compare_digest(calculated, digest)
    except Exception:
        return False

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        full_name TEXT, role TEXT DEFAULT 'Operador', active INTEGER DEFAULT 1, created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS customers (
        id TEXT PRIMARY KEY, customer_code TEXT UNIQUE NOT NULL, full_name TEXT NOT NULL,
        document_number TEXT, customer_type TEXT DEFAULT 'Persona', email TEXT, phone TEXT,
        address TEXT, risk_level TEXT DEFAULT 'Bajo', status TEXT DEFAULT 'Activo', created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS accounts (
        id TEXT PRIMARY KEY, account_number TEXT UNIQUE NOT NULL, customer_id TEXT NOT NULL,
        account_type TEXT DEFAULT 'Cuenta Corriente', currency TEXT DEFAULT 'DOP',
        balance REAL DEFAULT 0, status TEXT DEFAULT 'Activa', created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id TEXT PRIMARY KEY, transaction_code TEXT UNIQUE NOT NULL, account_id TEXT NOT NULL,
        transaction_type TEXT NOT NULL, amount REAL NOT NULL, description TEXT, reference TEXT,
        risk_score INTEGER DEFAULT 0, created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS audit_events (
        id TEXT PRIMARY KEY, username TEXT, action TEXT NOT NULL, entity_type TEXT,
        entity_id TEXT, details TEXT, previous_hash TEXT, event_hash TEXT NOT NULL, created_at TEXT NOT NULL)""")
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.execute("""INSERT INTO users
            (id,username,password_hash,full_name,role,created_at)
            VALUES (?,?,?,?,?,?)""",
            (str(uuid.uuid4()), "admin", hash_password("BASA_ADMIN_2026"),
             "Administrador BASA", "Administrador Global", datetime.now().isoformat()))
    conn.commit()
    conn.close()

def last_hash():
    conn = get_connection()
    row = conn.execute("SELECT event_hash FROM audit_events ORDER BY created_at DESC LIMIT 1").fetchone()
    conn.close()
    return row["event_hash"] if row else ""

def log_event(action, entity_type="", entity_id="", details=None):
    ts = datetime.now().isoformat()
    username = st.session_state.get("username", "SYSTEM")
    prev = last_hash()
    payload = username + action + entity_type + entity_id + json.dumps(details or {}, sort_keys=True) + prev + ts
    event_hash = hashlib.sha256(payload.encode()).hexdigest()
    conn = get_connection()
    conn.execute("""INSERT INTO audit_events
        (id,username,action,entity_type,entity_id,details,previous_hash,event_hash,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (str(uuid.uuid4()), username, action, entity_type, entity_id,
         json.dumps(details or {}, ensure_ascii=False), prev, event_hash, ts))
    conn.commit()
    conn.close()

def login():
    st.markdown("""<div class="basa-header">
    <h1>🏦 Sistema de Registro Bancario BASA</h1>
    <p>Registro, control, trazabilidad y análisis · Audit Intelligence USA</p>
    </div>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.2,1])
    with col:
        st.subheader("Acceso seguro")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("🔐 Iniciar sesión", use_container_width=True):
            conn = get_connection()
            user = conn.execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
            conn.close()
            if user and verify_password(password, user["password_hash"]):
                st.session_state.update(authenticated=True, username=user["username"],
                                        full_name=user["full_name"], role=user["role"])
                log_event("LOGIN", "USER", user["id"])
                st.rerun()
            st.error("Usuario o contraseña incorrectos.")
        st.info("Acceso inicial: usuario `admin` / contraseña `BASA_ADMIN_2026`. Cambie la contraseña antes de uso real.")

def dashboard():
    st.markdown("""<div class="basa-header"><h1>🏦 Sistema de Registro Bancario BASA</h1>
    <p>Centro de control · Audit Intelligence USA</p></div>""", unsafe_allow_html=True)
    conn = get_connection()
    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    transactions = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    balance = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts").fetchone()[0]
    high = conn.execute("SELECT COUNT(*) FROM customers WHERE risk_level='Alto'").fetchone()[0]
    conn.close()
    a,b,c,d,e = st.columns(5)
    a.metric("Clientes", customers); b.metric("Cuentas", accounts); c.metric("Operaciones", transactions)
    d.metric("Balance registrado", f"RD$ {balance:,.2f}"); e.metric("Alto riesgo", high)
    st.divider()
    conn = get_connection()
    df = pd.read_sql_query("""SELECT transaction_type, COUNT(*) operaciones, SUM(amount) monto
                              FROM transactions GROUP BY transaction_type""", conn)
    conn.close()
    if df.empty:
        st.info("No existen operaciones registradas.")
    else:
        x,y = st.columns(2)
        x.dataframe(df, use_container_width=True, hide_index=True)
        y.bar_chart(df.set_index("transaction_type")["monto"])

def customers_module():
    st.header("👥 Registro de clientes")
    t1,t2 = st.tabs(["Nuevo cliente","Consulta"])
    with t1:
        with st.form("customer_form"):
            a,b = st.columns(2)
            with a:
                name=st.text_input("Nombre completo / Razón social")
                doc=st.text_input("Documento / RNC")
                ctype=st.selectbox("Tipo",["Persona","Empresa","Entidad"])
                email=st.text_input("Correo electrónico")
            with b:
                phone=st.text_input("Teléfono"); address=st.text_area("Dirección")
                risk=st.selectbox("Nivel de riesgo",["Bajo","Medio","Alto"])
            if st.form_submit_button("💾 Registrar cliente"):
                if not name.strip(): st.error("Debe indicar el nombre."); return
                cid=str(uuid.uuid4()); code="BASA-"+datetime.now().strftime("%Y%m%d")+"-"+secrets.token_hex(3).upper()
                conn=get_connection()
                try:
                    conn.execute("""INSERT INTO customers
                    (id,customer_code,full_name,document_number,customer_type,email,phone,address,risk_level,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",(cid,code,name,doc,ctype,email,phone,address,risk,datetime.now().isoformat()))
                    conn.commit()
                    log_event("CREATE_CUSTOMER","CUSTOMER",cid,{"customer_code":code,"risk":risk})
                    st.success(f"Cliente registrado: {code}")
                except sqlite3.IntegrityError: st.error("No fue posible registrar el cliente.")
                finally: conn.close()
    with t2:
        conn=get_connection()
        df=pd.read_sql_query("SELECT customer_code,full_name,document_number,customer_type,email,phone,risk_level,status,created_at FROM customers ORDER BY created_at DESC",conn)
        conn.close(); st.dataframe(df,use_container_width=True,hide_index=True)

def accounts_module():
    st.header("💳 Registro de cuentas")
    conn=get_connection()
    customers=pd.read_sql_query("SELECT id,customer_code,full_name FROM customers ORDER BY full_name",conn); conn.close()
    if customers.empty: st.warning("Debe registrar primero un cliente."); return
    with st.form("account_form"):
        label=st.selectbox("Cliente",customers["customer_code"]+" — "+customers["full_name"])
        code=label.split(" — ")[0]; cid=customers.loc[customers.customer_code==code,"id"].iloc[0]
        atype=st.selectbox("Tipo de cuenta",["Cuenta Corriente","Cuenta de Ahorros","Cuenta Empresarial","Cuenta de Registro"])
        currency=st.selectbox("Moneda",["DOP","USD","EUR"])
        opening=st.number_input("Balance inicial",min_value=0.0,value=0.0,step=100.0)
        if st.form_submit_button("💾 Crear cuenta"):
            aid=str(uuid.uuid4()); number="BASA-"+datetime.now().strftime("%Y%m%d")+"-"+secrets.token_hex(4).upper()
            conn=get_connection()
            conn.execute("""INSERT INTO accounts
            (id,account_number,customer_id,account_type,currency,balance,created_at)
            VALUES (?,?,?,?,?,?,?)""",(aid,number,cid,atype,currency,opening,datetime.now().isoformat()))
            conn.commit(); conn.close()
            log_event("CREATE_ACCOUNT","ACCOUNT",aid,{"account_number":number,"currency":currency})
            st.success(f"Cuenta creada: {number}")
    conn=get_connection()
    df=pd.read_sql_query("""SELECT a.account_number,c.customer_code,c.full_name,a.account_type,a.currency,a.balance,a.status,a.created_at
                            FROM accounts a JOIN customers c ON c.id=a.customer_id ORDER BY a.created_at DESC""",conn)
    conn.close(); st.dataframe(df,use_container_width=True,hide_index=True)

def risk_score(amount, tx_type):
    score=50 if amount>=500000 else 30 if amount>=250000 else 15 if amount>=100000 else 0
    if tx_type in ["TRANSFERENCIA","RETIRO","PAGO"]: score += 10
    return min(score,100)

def transactions_module():
    st.header("💰 Registro de operaciones")
    conn=get_connection()
    accounts=pd.read_sql_query("SELECT id,account_number,currency,balance FROM accounts WHERE status='Activa' ORDER BY account_number",conn); conn.close()
    if accounts.empty: st.warning("No existen cuentas disponibles."); return
    with st.form("tx_form"):
        number=st.selectbox("Cuenta",accounts["account_number"])
        acc=accounts[accounts.account_number==number].iloc[0]
        typ=st.selectbox("Tipo",["DEPÓSITO","RETIRO","TRANSFERENCIA","PAGO","AJUSTE"])
        amount=st.number_input("Monto",min_value=0.01,step=100.0)
        desc=st.text_input("Descripción"); ref=st.text_input("Referencia")
        if st.form_submit_button("Registrar operación"):
            current=float(acc.balance)
            if typ in ["RETIRO","TRANSFERENCIA","PAGO"] and amount>current:
                st.error("Fondos insuficientes en el registro."); return
            new=current-amount if typ in ["RETIRO","TRANSFERENCIA","PAGO"] else current+amount
            tid=str(uuid.uuid4()); code="TX-"+datetime.now().strftime("%Y%m%d%H%M%S")+"-"+secrets.token_hex(2).upper()
            score=risk_score(amount,typ); conn=get_connection()
            conn.execute("UPDATE accounts SET balance=? WHERE id=?",(new,acc.id))
            conn.execute("""INSERT INTO transactions
            (id,transaction_code,account_id,transaction_type,amount,description,reference,risk_score,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",(tid,code,acc.id,typ,amount,desc,ref,score,datetime.now().isoformat()))
            conn.commit(); conn.close()
            log_event("CREATE_TRANSACTION","TRANSACTION",tid,{"transaction_code":code,"amount":amount,"risk_score":score})
            st.success(f"Operación registrada: {code}")
            if score>=70: st.warning("⚠️ Operación clasificada como de alto riesgo.")

def audit_intelligence():
    st.header("🔎 Audit Intelligence USA")
    conn=get_connection()
    df=pd.read_sql_query("""SELECT t.transaction_code,t.transaction_type,t.amount,t.description,t.reference,t.risk_score,
                            t.created_at,a.account_number,c.customer_code,c.full_name
                            FROM transactions t JOIN accounts a ON a.id=t.account_id JOIN customers c ON c.id=a.customer_id
                            ORDER BY t.created_at DESC""",conn); conn.close()
    if df.empty: st.info("No existen operaciones para analizar."); return
    high=int((df.risk_score>=70).sum()); medium=int(((df.risk_score>=30)&(df.risk_score<70)).sum())
    a,b,c,d=st.columns(4); a.metric("Operaciones",len(df)); b.metric("Alto riesgo",high); c.metric("Riesgo medio",medium); d.metric("Riesgo bajo",len(df)-high-medium)
    st.divider(); st.subheader("🚨 Operaciones con riesgo")
    st.dataframe(df[df.risk_score>0],use_container_width=True,hide_index=True)
    st.subheader("📊 Montos por tipo"); st.bar_chart(df.groupby("transaction_type")["amount"].sum())
    st.subheader("🧠 Motor ampliable")
    st.markdown("- Benford\n- Fraccionamiento\n- Duplicados\n- Anomalías temporales\n- Concentración\n- Redes de operaciones\n- KYC/AML\n- Scoring y expedientes")

def audit_log_module():
    st.header("🔐 Bitácora de auditoría")
    conn=get_connection()
    df=pd.read_sql_query("SELECT created_at,username,action,entity_type,entity_id,details,previous_hash,event_hash FROM audit_events ORDER BY created_at DESC",conn)
    conn.close()
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button("⬇️ Exportar auditoría CSV",df.to_csv(index=False).encode("utf-8"),"basa_audit_log.csv","text/csv")

def reports_module():
    st.header("📑 Reportes")
    conn=get_connection()
    tables={"Clientes":"SELECT * FROM customers","Cuentas":"SELECT * FROM accounts","Operaciones":"SELECT * FROM transactions"}
    data={}
    for title,q in tables.items():
        data[title]=pd.read_sql_query(q,conn); st.subheader(title); st.dataframe(data[title],use_container_width=True,hide_index=True)
    conn.close()
    for title,df in data.items():
        st.download_button(f"⬇️ {title} CSV",df.to_csv(index=False).encode("utf-8"),f"basa_{title.lower()}.csv","text/csv")

def settings_module():
    st.header("⚙️ Configuración")
    st.info("Esta entrega es un núcleo de registro interno. Para operación bancaria real deben añadirse autorización regulatoria, MFA, RBAC avanzado, cifrado, PostgreSQL, backups, monitoreo, KMS/HSM, AML/KYC, pruebas de penetración y conexiones API formalmente autorizadas.")
    st.json({"Sistema":APP_NAME,"Empresa":COMPANY_NAME,"Plataforma":AUDIT_NAME,"Modo":"DEMO / REGISTRO INTERNO","Versión":"1.0.0"})

def profile_module():
    st.header("👤 Perfil")
    st.write(f"**Usuario:** {st.session_state.get('username','')}")
    st.write(f"**Nombre:** {st.session_state.get('full_name','')}")
    st.write(f"**Rol:** {st.session_state.get('role','')}")
    st.warning("Cambie la contraseña inicial antes de utilizar el sistema en un entorno real.")

def main():
    init_db()
    if not st.session_state.get("authenticated",False):
        login(); return
    st.sidebar.markdown("## 🏦 BASA\n**Sistema de Registro Bancario**\n\nAudit Intelligence USA")
    st.sidebar.write(f"👤 {st.session_state.get('full_name','')}")
    menu=st.sidebar.radio("Módulos",["📊 Dashboard","👥 Clientes","💳 Cuentas","💰 Operaciones","🔎 Audit Intelligence","🔐 Bitácora","📑 Reportes","👤 Perfil","⚙️ Configuración"])
    if menu=="📊 Dashboard": dashboard()
    elif menu=="👥 Clientes": customers_module()
    elif menu=="💳 Cuentas": accounts_module()
    elif menu=="💰 Operaciones": transactions_module()
    elif menu=="🔎 Audit Intelligence": audit_intelligence()
    elif menu=="🔐 Bitácora": audit_log_module()
    elif menu=="📑 Reportes": reports_module()
    elif menu=="👤 Perfil": profile_module()
    elif menu=="⚙️ Configuración": settings_module()
    st.sidebar.divider()
    if st.sidebar.button("🚪 Cerrar sesión",use_container_width=True):
        log_event("LOGOUT")
        st.session_state.clear()
        st.rerun()
    st.markdown("""<div class="footer"><strong>Sistema de Registro Bancario BASA</strong><br>
    Audit Intelligence USA · Baldera Santos & Asociados SRL<br>
    Plataforma independiente de registro, control, trazabilidad y análisis.<br><small>Versión 1.0.0 · Demo / Registro Interno</small></div>""",unsafe_allow_html=True)

if __name__=="__main__":
    main()
