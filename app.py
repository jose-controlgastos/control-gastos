import streamlit as st
import pandas as pd
import libsql  # Usamos libsql en lugar de sqlite3 para conectar con Turso en la nube
import hashlib
from datetime import datetime
import os

try:
    import google.generativeai as genai
    IA_DISPONIBLE = True
except ImportError:
    IA_DISPONIBLE = False

# Configuración de página con diseño profesional
st.set_page_config(page_title="Control de Obra PRO", layout="wide")

# --- INYECCIÓN DE DISEÑO AVANZADO (Balance de colores neutros y formas) ---
st.markdown("""
    <style>
        /* Fondo general de la aplicación */
        .stApp {
            background-color: #f8fafc !important;
        }
        
        /* Barra lateral (Sidebar) estilo ejecutivo */
        section[data-testid="stSidebar"] {
            background-color: #0f172a !important;
        }
        section[data-testid="stSidebar"] __sub-container__ * {
            color: #f1f5f9 !important;
        }
        section[data-testid="stSidebar"] input {
            background-color: #1e293b !important;
            border: 1px solid #334155 !important;
            color: #f1f5f9 !important;
        }

        /* Tipografías y títulos limpios */
        h1 {
            color: #0f172a !important;
            font-weight: 700 !important;
            font-family: 'Inter', sans-serif;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 12px;
            margin-bottom: 25px;
        }
        h2, h3, h4 {
            color: #1e293b !important;
            font-weight: 600 !important;
            font-family: 'Inter', sans-serif;
        }

        /* Transformar formularios en contenedores tipo Tarjeta (Cards) */
        div[data-testid="stForm"] {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            padding: 24px !important;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
            margin-bottom: 20px;
        }

        /* Botones estilizados con azul ejecutivo */
        div.stButton > button {
            background-color: #0284c7 !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            border: none !important;
            padding: 8px 20px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            transition: background-color 0.2s ease;
        }
        div.stButton > button:hover {
            background-color: #0369a1 !important;
        }

        /* Pestañas (Tabs) más corporativas */
        button[data-baseweb="tab"] {
            font-weight: 600 !important;
            color: #64748b !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #0284c7 !important;
            border-bottom-color: #0284c7 !important;
        }

        /* Bloques de información y alertas */
        div[data-testid="stNotification"] {
            border-radius: 6px !important;
        }
    </style>
""", unsafe_allow_html=True)


# --- CONEXIÓN AUTOMÁTICA A TU BASE DE DATOS EN LA NUBE ---
def conectar():
    url = st.secrets["TURSO_URL"]
    token = st.secrets["TURSO_TOKEN"]
    return libsql.connect(database=url, auth_token=token)

def inicializar_base_de_datos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            contrasena TEXT,
            nombre TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            tipo TEXT,
            telefono TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            categoria TEXT,
            contacto_id INTEGER,
            concepto TEXT,
            importe REAL,
            usuario_registro TEXT,
            FOREIGN KEY(contacto_id) REFERENCES contactos(id)
        )
    ''')
    cursor.execute("SELECT * FROM usuarios WHERE usuario='admin'")
    if not cursor.fetchone():
        hash_pass = hashlib.sha256("1234".encode()).hexdigest()
        cursor.execute("INSERT INTO usuarios (usuario, contrasena, nombre) VALUES (?, ?, ?)", ("admin", hash_pass, "Jose (Administrador)"))
    conn.commit()
    conn.close()

inicializar_base_de_datos()
# --------------------------------------------------------

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
    st.session_state['usuario'] = ""

def check_login(user, password):
    hash_pass = hashlib.sha256(password.encode()).hexdigest()
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre FROM usuarios WHERE usuario=? AND contrasena=?", (user, hash_pass))
    resultado = cursor.fetchone()
    conn.close()
    return resultado

if not st.session_state['autenticado']:
    st.title("Acceso al Control de Costes de Obra")
    with st.form("Login"):
        usuario_input = st.text_input("Usuario")
        clave_input = st.text_input("Contraseña", type="password")
        boton_login = st.form_submit_button("Entrar al Sistema")
        
        if boton_login:
            usuario_valido = check_login(usuario_input, clave_input)
            if usuario_valido:
                st.session_state['autenticado'] = True
                st.session_state['usuario'] = usuario_input
                st.session_state['nombre_usuario'] = usuario_valido[0]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop()

api_key = st.sidebar.text_input("Google Gemini API Key (Para leer fotos/PDFs)", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
if api_key and IA_DISPONIBLE:
    genai.configure(api_key=api_key)

st.sidebar.write(f"Bienvenido: **{st.session_state['nombre_usuario']}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state['autenticado'] = False
    st.rerun()

def obtener_contactos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, tipo FROM contactos")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(rows, columns=columns)
    conn.close()
    return df

contactos_df = obtener_contactos()

tab_registro, tab_diario, tab_informes, tab_ajustes = st.tabs([
    "Registrar Gasto / Factura", "Gasto Diario y Semanal", "Informes Mensuales y Anuales", "Proveedores y Personal"
])

with tab_ajustes:
    st.subheader("Registrar Nuevo Trabajador o Empresa Proveedora")
    with st.form("nuevo_contacto"):
        col1, col2 = st.columns(2)
        with col1:
            nom_contacto = st.text_input("Nombre de la Empresa o Trabajador")
            tel_contacto = st.text_input("Teléfono (Opcional)")
        with col2:
            tipo_contacto = st.selectbox("Tipo", ["Trabajador", "Proveedor"])
        
        guardar_c = st.form_submit_button("Añadir a la Agenda")
        if guardar_c and nom_contacto:
            try:
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO contactos (nombre, tipo, telefono) VALUES (?, ?, ?)", (nom_contacto, tipo_contacto, tel_contacto))
                conn.commit()
                conn.close()
                st.success(f"{tipo_contacto} guardado correctamente.")
                st.rerun()
            except:
                st.error("Ese nombre ya existe en el sistema.")

with tab_registro:
    st.subheader("Introduce un gasto manual o sube un documento para procesarlo con IA")
    factura_subida = st.file_uploader("Sube la foto de la factura o el recibo en PDF", type=["png", "jpg", "jpeg", "pdf"])
    
    def_fecha = datetime.now()
    def_categoria = "Materiales"
    def_concepto = ""
    def_importe = 0.0

    if factura_subida and api_key and IA_DISPONIBLE:
        with st.spinner("Analizando factura con Inteligencia Artificial..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                bytes_data = factura_subida.read()
                
                prompt = """
                Analiza este documento de gasto y extrae EXCLUSIVAMENTE un objeto JSON con el siguiente formato:
                {
                  "importe": valor_numerico_del_total,
                  "concepto": "Breve descripcion del gasto",
                  "categoria": "Elegir solo entre: 'Obreros por horas', 'Materiales', 'Alquiler de maquinaria', 'Otros gastos'",
                  "proveedor": "Nombre de la empresa o emisor"
                }
                No respondas nada más que el JSON raw.
                """
                
                mime_type = factura_subida.type
                response = model.generate_content([
                    {"mime_type": mime_type, "data": bytes_data},
                    prompt
                ])
                
                import json
                texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
                datos_ia = json.loads(texto_limpio)
                
                def_concepto = datos_ia.get("concepto", "")
                def_importe = float(datos_ia.get("importe", 0.0))
                def_categoria = datos_ia.get("categoria", "Materiales")
                st.info(f"IA detectó: {datos_ia.get('proveedor', 'Desconocido')} | {def_importe} €")
            except Exception as e:
                st.error(f"No se pudo procesar automáticamente: {e}")

    with st.form("formulario_gasto"):
        col1, col2 = st.columns(2)
        with col1:
            fecha_gasto = st.date_input("Fecha", def_fecha)
            categoria_gasto = st.selectbox("Partida / Categoría", ["Obreros por horas", "Materiales", "Alquiler de maquinaria", "Otros gastos"], index=["Obreros por horas", "Materiales", "Alquiler de maquinaria", "Otros gastos"].index(def_categoria))
            concepto_gasto = st.text_input("Concepto / Descripción", value=def_concepto)
        with col2:
            opciones_contactos = ["Ninguno / General"] + contactos_df['nombre'].tolist()
            contacto_gasto = st.selectbox("Asignar a Trabajador / Proveedor", opciones_contactos)
            importe_gasto = st.number_input("Importe Total (€)", min_value=0.0, value=def_importe, step=5.0, format="%.2f")
            
        guardar_gasto = st.form_submit_button("Validar y Guardar Gasto")
        
        if guardar_gasto and importe_gasto > 0:
            conn = conectar()
            cursor = conn.cursor()
            
            c_id = None
            if contacto_gasto != "Ninguno / General":
                c_id = int(contactos_df[contactos_df['nombre'] == contacto_gasto]['id'].values[0])
                
            cursor.execute(
                "INSERT INTO gastos (fecha, categoria, contacto_id, concepto, importe, usuario_registro) VALUES (?, ?, ?, ?, ?, ?)",
                (fecha_gasto.strftime("%Y-%m-%d"), categoria_gasto, c_id, concepto_gasto, importe_gasto, st.session_state['usuario'])
            )
            conn.commit()
            conn.close()
            st.success("Gasto anotado en los libros contables.")
            st.rerun()

conn = conectar()
cursor = conn.cursor()
query = """
SELECT g.id, g.fecha, g.categoria, g.concepto, g.importe, g.usuario_registro, c.nombre as asignado_a, c.tipo as tipo_contacto
FROM gastos g LEFT JOIN contactos c ON g.contacto_id = c.id
ORDER BY g.fecha DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
if rows:
    columns = [desc[0] for desc in cursor.description]
    df_gastos = pd.DataFrame(rows, columns=columns)
else:
    df_gastos = pd.DataFrame()
conn.close()

if not df_gastos.empty:
    df_gastos['fecha_dt'] = pd.to_datetime(df_gastos['fecha'])
    df_gastos['Año'] = df_gastos['fecha_dt'].dt.year
    df_gastos['Mes'] = df_gastos['fecha_dt'].dt.strftime('%Y-%m')
    df_gastos['Semana'] = df_gastos['fecha_dt'].dt.strftime('%Y - Semana %V')
    df_gastos['Día'] = df_gastos['fecha_dt'].dt.strftime('%Y-%m-%d')

    with tab_diario:
        st.subheader("Evolución del Coste Diario y Acumulado Semanal")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("**Gastos agrupados por Día**")
            g_diario = df_gastos.groupby('Día')['importe'].sum().reset_index()
            st.dataframe(g_diario.rename(columns={'importe': 'Total (€)'}), use_container_width=True)
        with col_m2:
            st.markdown("**Gastos agrupados por Semana**")
            g_semanal = df_gastos.groupby('Semana')['importe'].sum().reset_index()
            st.bar_chart(data=g_semanal, x='Semana', y='importe')
            st.dataframe(g_semanal.rename(columns={'importe': 'Total (€)'}), use_container_width=True)

    with tab_informes:
        st.subheader("Análisis de Partidas e Informes Ejecutivos")
        filtro_partida = st.multiselect("Filtrar por Partida/Categoría:", df_gastos['categoria'].unique(), default=df_gastos['categoria'].unique())
        df_filtrado = df_gastos[df_gastos['categoria'].isin(filtro_partida)]
        st.metric("Total de Selección Filtrada", f"{df_filtrado['importe'].sum():,.2f} €")
        
        st.markdown("### Cierre Mensual")
        g_mensual = df_filtrado.groupby(['Mes', 'categoria'])['importe'].sum().unstack(fill_value=0)
        st.dataframe(g_mensual, use_container_width=True)
        
        st.markdown("### Cierre Anual")
        g_anual = df_filtrado.groupby(['Año', 'categoria'])['importe'].sum().unstack(fill_value=0)
        st.dataframe(g_anual, use_container_width=True)
        
        st.markdown("### Registro de Auditoría")
        st.dataframe(df_filtrado[['fecha', 'categoria', 'asignado_a', 'concepto', 'importe', 'usuario_registro']], use_container_width=True)
else:
    with tab_diario:
        st.info("Aún no hay datos registrados en el sistema.")
