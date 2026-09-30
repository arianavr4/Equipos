import streamlit as st

import pandas as pd

import sqlite3

import re

from datetime import date, datetime

from pathlib import Path

# ============================================================

# CONFIGURACIÓN

# ============================================================

st.set_page_config(

    page_title="AMEL",

    page_icon="🧪",

    layout="wide",

    initial_sidebar_state="expanded"

)

# Carpeta donde está EQUIPOS.py

BASE_DIR = Path(__file__).resolve().parent

DB_NAME = BASE_DIR / "equipment_dashboard.db"

EXCEL_NAME = BASE_DIR / "Listado equipos.xlsx"

# Carpeta donde se guardan los certificados PDF de mantenimiento

CERTIFICADOS_DIR = BASE_DIR / "certificados"

# Días máximos entre lavados del HPLC

DIAS_LAVADO_HPLC = 7

# ============================================================

# ESTILO VISUAL

# ============================================================

st.markdown("""

<style>

.stApp {

    background-color: #F4F7FA;

}

[data-testid="stSidebar"] {

    background-color: #003B5C;

}

[data-testid="stSidebar"] * {

    color: white !important;

}

h1, h2, h3 {

    color: #003B5C !important;

}

[data-testid="stMetric"] {

    background-color: white;

    border: 1px solid #DCE5EC;

    border-radius: 12px;

    padding: 15px;

    box-shadow: 0px 2px 8px rgba(0, 59, 92, 0.07);

}

[data-testid="stMetricLabel"] {

    color: #64748B !important;

}

[data-testid="stMetricValue"] {

    color: #003B5C !important;

}

.stButton > button {

    background-color: #0072CE;

    color: white;

    border: none;

    border-radius: 7px;

    font-weight: 600;

}

.stButton > button:hover {

    background-color: #005B9F;

    color: white;

}

</style>

""", unsafe_allow_html=True)

# ============================================================

# BASE DE DATOS

# ============================================================

def conectar_db():

    return sqlite3.connect(DB_NAME)

def crear_tablas():

    conn = conectar_db()

    cursor = conn.cursor()

    # --------------------------------------------------------

    # TABLA DE EQUIPOS

    # --------------------------------------------------------

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS equipos (

            codigo TEXT PRIMARY KEY,

            tipo TEXT NOT NULL,

            estado TEXT NOT NULL,

            ubicacion TEXT,

            ultimo_mantenimiento TEXT,

            proximo_mantenimiento TEXT,

            observacion TEXT

        )

    """)

    # --------------------------------------------------------

    # TABLA DE REGISTROS

    # --------------------------------------------------------

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS usos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            codigo_equipo TEXT NOT NULL,

            fecha TEXT NOT NULL,

            tipo_registro TEXT NOT NULL,

            observacion TEXT

        )

    """)

    # --------------------------------------------------------

    # TABLA DE MANTENIMIENTOS

    # --------------------------------------------------------

    cursor.execute("""

        CREATE TABLE IF NOT EXISTS mantenimientos (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            codigo_equipo TEXT NOT NULL,

            tipo_mantenimiento TEXT NOT NULL,

            proveedor TEXT,

            fecha TEXT NOT NULL,

            observacion TEXT,

            certificado_nombre TEXT,

            certificado_ruta TEXT

        )

    """)

    # --------------------------------------------------------

    # REVISAR COLUMNAS

    # --------------------------------------------------------

    cursor.execute(

        "PRAGMA table_info(equipos)"

    )

    columnas_existentes = [

        fila[1]

        for fila in cursor.fetchall()

    ]

    nuevas_columnas = [

        ("fecha_uso", "TEXT"),

        (

            "fecha_mantenimiento_preventivo",

            "TEXT"

        ),

        ("fecha_lavado", "TEXT"),

        ("fecha_ocurrencia", "TEXT"),

        ("personal_uso", "TEXT"),

        ("personal_lavado", "TEXT")

    ]

    for nombre_columna, tipo in nuevas_columnas:

        if nombre_columna not in columnas_existentes:

            cursor.execute(

                f"""

                ALTER TABLE equipos

                ADD COLUMN {nombre_columna} {tipo}

                """

            )

    # --------------------------------------------------------

    # "De baja" ahora se llama "Inoperativo"

    # --------------------------------------------------------

    cursor.execute("""

        UPDATE equipos

        SET estado = 'Inoperativo'

        WHERE estado = 'De baja'

    """)

    # --------------------------------------------------------

    # PASAR LAS FECHAS DE USO YA GUARDADAS A LA TABLA usos

    # (así "Último uso" y "Días sin uso" se actualizan)

    # --------------------------------------------------------

    cursor.execute("""

        INSERT INTO usos (

            codigo_equipo,

            fecha,

            tipo_registro,

            observacion

        )

        SELECT

            e.codigo,

            e.fecha_uso,

            'Uso',

            'Registro automático desde Administración'

        FROM equipos e

        WHERE e.fecha_uso IS NOT NULL

        AND NOT EXISTS (

            SELECT 1 FROM usos u

            WHERE u.codigo_equipo = e.codigo

            AND u.fecha = e.fecha_uso

            AND u.tipo_registro = 'Uso'

        )

    """)

    conn.commit()

    conn.close()

crear_tablas()

# ============================================================

# LEER EXCEL DE EQUIPOS

# ============================================================

def obtener_fecha_modificacion_excel():

    if EXCEL_NAME.exists():

        return EXCEL_NAME.stat().st_mtime

    return None

# El parámetro fecha_modificacion hace que el caché se renueve

# automáticamente cada vez que cambias el Excel

@st.cache_data

def cargar_listado_excel(fecha_modificacion):

    if not EXCEL_NAME.exists():

        return None

    try:

        df = pd.read_excel(

            EXCEL_NAME,

            sheet_name="Table 1"

        )

    except Exception as e:

        st.error(

            f"No se pudo leer el archivo "

            f"'Listado equipos.xlsx'.\n\n"

            f"Error: {e}"

        )

        return None

    # --------------------------------------------------------

    # Eliminar filas que no tengan código

    # --------------------------------------------------------

    if "CÓDIGO" in df.columns:

        df = df[

            df["CÓDIGO"].notna()

        ].copy()

    # --------------------------------------------------------

    # Limpiar códigos

    # --------------------------------------------------------

    if "CÓDIGO" in df.columns:

        df["CÓDIGO"] = (

            df["CÓDIGO"]

            .astype(str)

            .str.strip()

        )

    # --------------------------------------------------------

    # Eliminar filas completamente vacías

    # --------------------------------------------------------

    df = df.dropna(

        how="all"

    )

    return df

listado_excel = cargar_listado_excel(

    obtener_fecha_modificacion_excel()

)

# ============================================================

# FUNCIONES DE BASE DE DATOS

# ============================================================

def obtener_equipos():

    conn = conectar_db()

    df = pd.read_sql_query(

        "SELECT * FROM equipos",

        conn

    )

    conn.close()

    return df

def obtener_usos():

    conn = conectar_db()

    df = pd.read_sql_query(

        "SELECT * FROM usos",

        conn

    )

    conn.close()

    return df

def obtener_mantenimientos():

    conn = conectar_db()

    df = pd.read_sql_query(

        "SELECT * FROM mantenimientos",

        conn

    )

    conn.close()

    return df

def guardar_equipo(

    codigo,

    tipo,

    estado,

    fecha_uso,

    fecha_mantenimiento_preventivo,

    fecha_lavado,

    fecha_ocurrencia,

    personal_uso,

    personal_lavado,

    observacion

):

    conn = conectar_db()

    cursor = conn.cursor()

    cursor.execute("""

        INSERT INTO equipos

        (

            codigo,

            tipo,

            estado,

            fecha_uso,

            fecha_mantenimiento_preventivo,

            fecha_lavado,

            fecha_ocurrencia,

            personal_uso,

            personal_lavado,

            observacion

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(codigo) DO UPDATE SET

            tipo = excluded.tipo,

            estado = excluded.estado,

            fecha_uso = COALESCE(

                excluded.fecha_uso,

                equipos.fecha_uso

            ),

            fecha_mantenimiento_preventivo = COALESCE(

                excluded.fecha_mantenimiento_preventivo,

                equipos.fecha_mantenimiento_preventivo

            ),

            fecha_lavado = COALESCE(

                excluded.fecha_lavado,

                equipos.fecha_lavado

            ),

            fecha_ocurrencia = COALESCE(

                excluded.fecha_ocurrencia,

                equipos.fecha_ocurrencia

            ),

            personal_uso = COALESCE(

                excluded.personal_uso,

                equipos.personal_uso

            ),

            personal_lavado = COALESCE(

                excluded.personal_lavado,

                equipos.personal_lavado

            ),

            observacion = excluded.observacion

    """, (

        codigo,

        tipo,

        estado,

        fecha_uso,

        fecha_mantenimiento_preventivo,

        fecha_lavado,

        fecha_ocurrencia,

        personal_uso,

        personal_lavado,

        observacion

    ))

    # --------------------------------------------------------

    # Si se registró un uso, también se guarda en la tabla usos

    # --------------------------------------------------------

    if fecha_uso:

        cursor.execute("""

            SELECT 1 FROM usos

            WHERE codigo_equipo = ?

            AND fecha = ?

            AND tipo_registro = 'Uso'

        """, (

            codigo,

            fecha_uso

        ))

        if cursor.fetchone() is None:

            cursor.execute("""

                INSERT INTO usos

                (

                    codigo_equipo,

                    fecha,

                    tipo_registro,

                    observacion

                )

                VALUES (?, ?, 'Uso', ?)

            """, (

                codigo,

                fecha_uso,

                observacion

            ))

    conn.commit()

    conn.close()

# ============================================================

# FUNCIONES DE USO

# ============================================================

def calcular_ultimo_uso(

    codigo,

    usos

):

    if usos.empty:

        return None

    registros = usos[

        (

            usos["codigo_equipo"]

            == codigo

        )

        &

        (

            usos["tipo_registro"]

            == "Uso"

        )

    ]

    if registros.empty:

        return None

    fechas = pd.to_datetime(

        registros["fecha"],

        errors="coerce"

    )

    if fechas.dropna().empty:

        return None

    return fechas.max().date()

def calcular_dias_sin_uso(

    codigo,

    usos

):

    ultimo_uso = calcular_ultimo_uso(

        codigo,

        usos

    )

    if ultimo_uso is None:

        return None

    return (

        date.today()

        - ultimo_uso

    ).days

def determinar_alerta(dias):

    if dias is None:

        return "⚪ Sin información"

    if dias <= 7:

        return "🟢 Uso reciente"

    if dias <= 14:

        return "🟡 Revisar"

    return "🔴 Sin uso prolongado"

# ============================================================

# ESTADOS

# ============================================================

ESTADOS = [

    "Operativo",

    "En uso",

    "Inoperativo",

    "Lavado integral",

    "Mantenimiento preventivo",

    "Ocurrencias"

]

PERSONAL = [

    "Adriana Meza",

    "Ricardo Briceño",

    "Leonor Cortez",

    "Cristian Condori",

    "Gregorio Reyes",

    "Anghela Rodriguez"

]

TIPOS_MANTENIMIENTO = [

    "Preventivo",

    "Correctivo"

]

def obtener_icono_estado(

    estado

):

    iconos = {

        "Operativo": "🟢",

        "En uso": "🔵",

        "Inoperativo": "⚫",

        "Lavado integral": "🧼",

        "Mantenimiento preventivo": "🔧",

        "Ocurrencias": "⚠️"

    }

    return iconos.get(

        estado,

        "⚪"

    )

def texto_estado(

    estado,

    personal_uso

):

    # Si está en uso, muestra "En uso por nombre"

    if (

        estado == "En uso"

        and personal_uso is not None

        and not pd.isna(personal_uso)

        and str(personal_uso).strip() != ""

    ):

        return f"En uso por {personal_uso}"

    return estado

# ============================================================

# FORMATEAR FECHAS

# ============================================================

def formatear_fecha(

    fecha

):

    if fecha is None:

        return "Sin registro"

    try:

        if pd.isna(fecha):

            return "Sin registro"

    except:

        pass

    texto = str(

        fecha

    ).strip()

    if texto == "":

        return "Sin registro"

    try:

        return pd.to_datetime(

            texto

        ).strftime(

            "%d/%m/%Y"

        )

    except:

        return texto

# ============================================================

# FUNCIONES DE LAVADO SEMANAL (HPLC)

# ============================================================

def es_hplc(

    tipo

):

    return "HPLC" in str(

        tipo

    ).upper()

def calcular_dias_desde_lavado(

    fecha_lavado

):

    if fecha_lavado is None:

        return None

    try:

        if pd.isna(fecha_lavado):

            return None

    except:

        pass

    fecha = pd.to_datetime(

        fecha_lavado,

        errors="coerce"

    )

    if pd.isna(fecha):

        return None

    return (

        date.today()

        - fecha.date()

    ).days

def estado_lavado_hplc(

    fecha_lavado

):

    dias = calcular_dias_desde_lavado(

        fecha_lavado

    )

    if dias is None:

        return (

            "⚪ Sin lavado registrado: ",

            "gris"

        )

    if dias > DIAS_LAVADO_HPLC:

        return (

            f"🔴 Lavado vencido: ya pasó la semana "

            f"({dias} días sin lavar).",

            "rojo"

        )

    if dias == DIAS_LAVADO_HPLC:

        return (

            "🟡 Toca lavar hoy: se cumple la semana "

            "desde el último lavado.",

            "amarillo"

        )

    restantes = DIAS_LAVADO_HPLC - dias

    return (

        f"🟢 Dentro del plazo: último lavado hace "

        f"{dias} día(s), faltan {restantes} "

        f"para el próximo.",

        "verde"

    )

# ============================================================

# FUNCIONES DE MANTENIMIENTO

# ============================================================

def obtener_fila_equipo(

    codigo,

    equipos

):

    fila = equipos[

        equipos["codigo"]

        == codigo

    ]

    if fila.empty:

        return None

    return fila.iloc[0]

def obtener_ultimo_mantenimiento(

    codigo,

    fila_equipo,

    mantenimientos

):

    fechas = []

    # Mantenimientos registrados en la sección Mantenimientos

    if not mantenimientos.empty:

        registros = mantenimientos[

            mantenimientos["codigo_equipo"]

            == codigo

        ]

        fechas += pd.to_datetime(

            registros["fecha"],

            errors="coerce"

        ).dropna().tolist()

    # Fechas guardadas en la tabla de equipos

    if fila_equipo is not None:

        for campo in (

            "ultimo_mantenimiento",

            "fecha_mantenimiento_preventivo"

        ):

            valor = fila_equipo.get(

                campo

            )

            if (

                valor is None

                or pd.isna(valor)

            ):

                continue

            fecha = pd.to_datetime(

                valor,

                errors="coerce"

            )

            if not pd.isna(fecha):

                fechas.append(

                    fecha

                )

    if not fechas:

        return None

    return max(

        fechas

    ).date()

def guardar_mantenimiento(

    codigo,

    tipo_mantenimiento,

    proveedor,

    fecha,

    observacion,

    archivo_pdf

):

    certificado_nombre = None

    certificado_ruta = None

    # --------------------------------------------------------

    # Guardar el PDF en la carpeta "certificados"

    # --------------------------------------------------------

    if archivo_pdf is not None:

        CERTIFICADOS_DIR.mkdir(

            exist_ok=True

        )

        marca_tiempo = datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        nombre_archivo = re.sub(

            r"[^A-Za-z0-9._-]",

            "_",

            f"{codigo}_{marca_tiempo}_"

            f"{archivo_pdf.name}"

        )

        ruta_completa = (

            CERTIFICADOS_DIR

            / nombre_archivo

        )

        with open(

            ruta_completa,

            "wb"

        ) as archivo:

            archivo.write(

                archivo_pdf.getbuffer()

            )

        certificado_nombre = archivo_pdf.name

        certificado_ruta = (

            f"certificados/{nombre_archivo}"

        )

    # --------------------------------------------------------

    # Guardar el registro en la base de datos

    # --------------------------------------------------------

    conn = conectar_db()

    cursor = conn.cursor()

    cursor.execute("""

        INSERT INTO mantenimientos

        (

            codigo_equipo,

            tipo_mantenimiento,

            proveedor,

            fecha,

            observacion,

            certificado_nombre,

            certificado_ruta

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)

    """, (

        codigo,

        tipo_mantenimiento,

        proveedor,

        fecha,

        observacion,

        certificado_nombre,

        certificado_ruta

    ))

    conn.commit()

    conn.close()

def mostrar_tabla_mantenimientos(

    df,

    sufijo

):

    if df.empty:

        st.info(

            "No hay mantenimientos registrados."

        )

        return

    df = df.copy()

    df["_fecha_orden"] = pd.to_datetime(

        df["fecha"],

        errors="coerce"

    )

    df = df.sort_values(

        "_fecha_orden",

        ascending=False

    )

    tabla = pd.DataFrame({

        "ID": df["id"].tolist(),

        "Equipo": df["codigo_equipo"].tolist(),

        "Tipo": df["tipo_mantenimiento"].tolist(),

        "Proveedor": df["proveedor"].tolist(),

        "Fecha": [

            formatear_fecha(f)

            for f in df["fecha"]

        ],

        "Observación": df["observacion"].tolist(),

        "Certificado": [

            nombre

            if isinstance(nombre, str)

            and nombre != ""

            else "Sin certificado"

            for nombre in df["certificado_nombre"]

        ]

    })

    st.dataframe(

        tabla,

        use_container_width=True,

        hide_index=True

    )

    # --------------------------------------------------------

    # Descargar certificados

    # --------------------------------------------------------

    con_certificado = df[

        df["certificado_ruta"].notna()

        &

        (df["certificado_ruta"] != "")

    ]

    if not con_certificado.empty:

        opciones = {}

        for _, fila in con_certificado.iterrows():

            etiqueta = (

                f"#{fila['id']} — "

                f"{fila['codigo_equipo']} — "

                f"{formatear_fecha(fila['fecha'])} — "

                f"{fila['tipo_mantenimiento']}"

            )

            opciones[etiqueta] = fila

        elegido = st.selectbox(

            "📎 Descargar certificado",

            list(opciones.keys()),

            key=f"cert_sel_{sufijo}"

        )

        fila_elegida = opciones[elegido]

        ruta_pdf = (

            BASE_DIR

            / fila_elegida["certificado_ruta"]

        )

        if ruta_pdf.exists():

            with open(

                ruta_pdf,

                "rb"

            ) as archivo:

                contenido_pdf = archivo.read()

            st.download_button(

                "⬇️ Descargar PDF",

                data=contenido_pdf,

                file_name=fila_elegida[

                    "certificado_nombre"

                ],

                mime="application/pdf",

                key=f"cert_btn_{sufijo}"

            )

        else:

            st.warning(

                "No se encontró el archivo del "

                "certificado en la carpeta "

                "'certificados'."

            )

# ============================================================

# DATOS ACTUALES

# ============================================================

equipos = obtener_equipos()

usos = obtener_usos()

mantenimientos = obtener_mantenimientos()

# ============================================================

# SIDEBAR

# ============================================================

with st.sidebar:

    st.markdown(

        "# 🧪"

    )

    st.markdown(

        "## Monitoreo de equipos"

    )

    st.divider()

    pagina = st.radio(

        "NAVEGACIÓN",

        [

            "Dashboard",

            "Equipos",

            "Administración",

            "Mantenimientos",

            "Listado de equipos"

        ]

    )

# ============================================================

# TÍTULO GENERAL

# ============================================================

st.title(

    "AMEL"

)

st.caption(

    "Abbott Monitoring & Equipment Log"

)

st.divider()

# ============================================================

# DASHBOARD

# ============================================================

if pagina == "Dashboard":

    st.subheader(

        "📊 Resumen general"

    )

    total = len(

        listado_excel

    ) if listado_excel is not None else len(

        equipos

    )

    operativos = len(

        equipos[

            equipos["estado"]

            == "Operativo"

        ]

    )

    en_uso = len(

        equipos[

            equipos["estado"]

            == "En uso"

        ]

    )

    inoperativos = len(

        equipos[

            equipos["estado"]

            == "Inoperativo"

        ]

    )

    sin_uso = 0

    for codigo in equipos["codigo"]:

        dias = calcular_dias_sin_uso(

            codigo,

            usos

        )

        if (

            dias is not None

            and dias > 14

        ):

            sin_uso += 1

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(

            "TOTAL EQUIPOS",

            total

        )

    with col2:

        st.metric(

            "OPERATIVOS",

            operativos

        )

    with col3:

        st.metric(

            "EN USO",

            en_uso

        )

    with col4:

        st.metric(

            "SIN USO",

            sin_uso

        )

    with col5:

        st.metric(

            "INOPERATIVOS",

            inoperativos

        )

    st.divider()

    # --------------------------------------------------------

    # PORCENTAJES

    # --------------------------------------------------------

    st.subheader(

        "📈 Porcentajes"

    )

    if total > 0:

        pct_en_uso = en_uso / total * 100

        pct_operativos = operativos / total * 100

        pct_inoperativos = inoperativos / total * 100

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(

                "% EN USO",

                f"{pct_en_uso:.1f}%"

            )

            st.progress(

                min(pct_en_uso / 100, 1.0)

            )

        with col2:

            st.metric(

                "% OPERATIVOS",

                f"{pct_operativos:.1f}%"

            )

            st.progress(

                min(pct_operativos / 100, 1.0)

            )

        with col3:

            st.metric(

                "% INOPERATIVOS",

                f"{pct_inoperativos:.1f}%"

            )

            st.progress(

                min(pct_inoperativos / 100, 1.0)

            )

        st.caption(

            f"Porcentajes calculados sobre el total "

            f"de {total} equipos."

        )

    else:

        st.info(

            "No hay equipos para calcular porcentajes."

        )

    st.divider()

    st.subheader(

        "⚠️ Alertas"

    )

    alertas = []

    for _, equipo in equipos.iterrows():

        codigo = equipo["codigo"]

        dias = calcular_dias_sin_uso(

            codigo,

            usos

        )

        if (

            dias is not None

            and dias > 14

        ):

            alertas.append(

                (

                    codigo,

                    dias

                )

            )

    if alertas:

        for codigo, dias in alertas:

            st.error(

                f"🔴 {codigo} — "

                f"{dias} días sin registrar uso."

            )

    else:

        st.success(

            "✓ No hay equipos con más de "

            "14 días sin registrar uso."

        )

    st.divider()

    # --------------------------------------------------------

    # LAVADO SEMANAL DE HPLC

    # --------------------------------------------------------

    st.subheader(

        "🧼 Lavado semanal de HPLC"

    )

    hay_hplc = False

    for _, equipo in equipos.iterrows():

        if (

            not es_hplc(equipo["tipo"])

            or equipo["estado"] == "Inoperativo"

        ):

            continue

        hay_hplc = True

        texto_lavado, nivel_lavado = (

            estado_lavado_hplc(

                equipo.get(

                    "fecha_lavado"

                )

            )

        )

        mensaje = (

            f"**{equipo['codigo']}** — "

            f"{texto_lavado}"

        )

        if nivel_lavado == "rojo":

            st.error(

                mensaje

            )

        elif nivel_lavado in (

            "amarillo",

            "gris"

        ):

            st.warning(

                mensaje

            )

        else:

            st.success(

                mensaje

            )

    if not hay_hplc:

        st.info(

            "No hay equipos HPLC registrados."

        )

# ============================================================

# EQUIPOS

# ============================================================

elif pagina == "Equipos":

    st.subheader(

        "🖥️ Equipos registrados"

    )

    if equipos.empty:

        st.info(

            "No hay equipos registrados "

            "en el sistema todavía."

        )

    else:

        # ----------------------------------------------------

        # FILTROS

        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            estados_filtro = (

                ["Todos"]

                +

                sorted(

                    equipos["estado"]

                    .dropna()

                    .unique()

                    .tolist()

                )

            )

            filtro_estado = st.selectbox(

                "Estado",

                estados_filtro

            )

        with col2:

            tipos = (

                ["Todos"]

                +

                sorted(

                    equipos["tipo"]

                    .dropna()

                    .unique()

                    .tolist()

                )

            )

            filtro_tipo = st.selectbox(

                "Tipo de equipo",

                tipos

            )

        with col3:

            busqueda = st.text_input(

                "Buscar equipo",

                placeholder="Ej. OPT-001"

            )

        filtrados = equipos.copy()

        if filtro_estado != "Todos":

            filtrados = filtrados[

                filtrados["estado"]

                == filtro_estado

            ]

        if filtro_tipo != "Todos":

            filtrados = filtrados[

                filtrados["tipo"]

                == filtro_tipo

            ]

        if busqueda:

            filtrados = filtrados[

                filtrados["codigo"]

                .str.contains(

                    busqueda,

                    case=False,

                    na=False

                )

            ]

        st.divider()

        if filtrados.empty:

            st.warning(

                "No se encontraron equipos."

            )

        else:

            for inicio in range(

                0,

                len(filtrados),

                3

            ):

                fila = filtrados.iloc[

                    inicio:inicio + 3

                ]

                columnas = st.columns(3)

                for columna, (_, equipo) in zip(

                    columnas,

                    fila.iterrows()

                ):

                    codigo = equipo["codigo"]

                    estado = equipo["estado"]

                    ultimo_uso = (

                        calcular_ultimo_uso(

                            codigo,

                            usos

                        )

                    )

                    dias = (

                        calcular_dias_sin_uso(

                            codigo,

                            usos

                        )

                    )

                    ultimo_mantenimiento = (

                        obtener_ultimo_mantenimiento(

                            codigo,

                            equipo,

                            mantenimientos

                        )

                    )

                    personal_uso_eq = equipo.get(

                        "personal_uso"

                    )

                    with columna:

                        with st.container(

                            border=True

                        ):

                            st.markdown(

                                f"### "

                                f"{obtener_icono_estado(estado)} "

                                f"{codigo}"

                            )

                            st.caption(

                                equipo["tipo"]

                            )

                            st.write(

                                f"**Estado:** "

                                f"{texto_estado(estado, personal_uso_eq)}"

                            )

                            st.write(

                                f"**Último uso:** "

                                f"{formatear_fecha(ultimo_uso)}"

                            )

                            if dias is not None:

                                st.write(

                                    f"**Días sin uso:** "

                                    f"{dias}"

                                )

                            else:

                                st.write(

                                    "**Días sin uso:** "

                                    "Sin registro"

                                )

                            st.write(

                                f"**Último mantenimiento:** "

                                f"{formatear_fecha(ultimo_mantenimiento)}"

                            )

                            fecha_lavado_eq = equipo.get(

                                "fecha_lavado"

                            )

                            personal_lavado_eq = equipo.get(

                                "personal_lavado"

                            )

                            if pd.isna(fecha_lavado_eq):

                                st.write(

                                    "**Último lavado:** "

                                    "Sin registro"

                                )

                            elif pd.isna(personal_lavado_eq):

                                st.write(

                                    f"**Último lavado:** "

                                    f"{formatear_fecha(fecha_lavado_eq)}"

                                )

                            else:

                                st.write(

                                    f"**Último lavado:** "

                                    f"{formatear_fecha(fecha_lavado_eq)} "

                                    f"por {personal_lavado_eq}"

                                )

                            # --------------------------------

                            # LAVADO SEMANAL DEL HPLC

                            # --------------------------------

                            if (

                                es_hplc(equipo["tipo"])

                                and estado != "Inoperativo"

                            ):

                                texto_lavado, nivel_lavado = (

                                    estado_lavado_hplc(

                                        fecha_lavado_eq

                                    )

                                )

                                if nivel_lavado == "rojo":

                                    st.error(

                                        texto_lavado

                                    )

                                elif nivel_lavado in (

                                    "amarillo",

                                    "gris"

                                ):

                                    st.warning(

                                        texto_lavado

                                    )

                                else:

                                    st.success(

                                        texto_lavado

                                    )

# ============================================================

# ADMINISTRACIÓN

# ============================================================

elif pagina == "Administración":

    st.subheader(

        "⚙️ Administración"

    )

    st.info(

        "Registra o actualiza la información del equipo."

    )

    # --------------------------------------------------------

    # DATOS DEL EQUIPO

    # --------------------------------------------------------

    st.markdown(

        "### Datos del equipo"

    )

    col1, col2 = st.columns(2)

    with col1:

        codigo = st.text_input(

            "Código del equipo",

            placeholder="Ej. OPT-001"

        )

    with col2:

        tipo = st.text_input(

            "Tipo",

            value="HPLC"

        )

    # --------------------------------------------------------

    # ESTADO

    # --------------------------------------------------------

    st.markdown(

        "### Estado del equipo"

    )

    estado = st.selectbox(

        "Selecciona el estado",

        ESTADOS

    )

    # --------------------------------------------------------

    # FECHAS DINÁMICAS

    # --------------------------------------------------------

    fecha_uso = None

    fecha_mantenimiento_preventivo = None

    fecha_lavado = None

    fecha_ocurrencia = None

    personal_uso = None

    personal_lavado = None

    if estado == "En uso":

        fecha_uso = st.date_input(

            "📅 Fecha de uso",

            value=date.today(),

            format="DD/MM/YYYY",

            key="fecha_uso_admin"

        )

    elif estado == "Lavado integral":

        fecha_lavado = st.date_input(

            "📅 Fecha de lavado",

            value=date.today(),

            format="DD/MM/YYYY",

            key="fecha_lavado_admin"

        )

    elif estado == "Mantenimiento preventivo":

        fecha_mantenimiento_preventivo = st.date_input(

            "📅 Fecha de mantenimiento preventivo",

            value=date.today(),

            format="DD/MM/YYYY",

            key="fecha_mantenimiento_admin"

        )

    elif estado == "Ocurrencias":

        fecha_ocurrencia = st.date_input(

            "📅 Fecha de ocurrencia",

            value=date.today(),

            format="DD/MM/YYYY",

            key="fecha_ocurrencia_admin"

        )

    # --------------------------------------------------------

    # PERSONAL

    # --------------------------------------------------------

    if estado == "En uso":

        personal_uso = st.selectbox(

            "👤 Personal que usa el equipo",

            PERSONAL,

            index=None,

            placeholder="Selecciona al trabajador",

            key="personal_uso_admin"

        )

    elif estado == "Lavado integral":

        personal_lavado = st.selectbox(

            "👤 Personal que realizó el lavado",

            PERSONAL,

            index=None,

            placeholder="Selecciona al trabajador",

            key="personal_lavado_admin"

        )

    # --------------------------------------------------------

    # OBSERVACIÓN

    # --------------------------------------------------------

    st.markdown(

        "### Observaciones"

    )

    observacion = st.text_area(

        "Observación",

        placeholder="Agregar información adicional..."

    )

    # --------------------------------------------------------

    # GUARDAR

    # --------------------------------------------------------

    if st.button(

        "💾 Guardar información",

        type="primary"

    ):

        if not codigo.strip():

            st.error(

                "Debes ingresar el código del equipo."

            )

        elif estado == "En uso" and not personal_uso:

            st.error(

                "Debes seleccionar quién está usando el equipo."

            )

        elif estado == "Lavado integral" and not personal_lavado:

            st.error(

                "Debes seleccionar quién realizó el lavado."

            )

        else:

            guardar_equipo(

                codigo.strip(),

                tipo.strip(),

                estado,

                (

                    str(fecha_uso)

                    if fecha_uso

                    else None

                ),

                (

                    str(

                        fecha_mantenimiento_preventivo

                    )

                    if fecha_mantenimiento_preventivo

                    else None

                ),

                (

                    str(fecha_lavado)

                    if fecha_lavado

                    else None

                ),

                (

                    str(fecha_ocurrencia)

                    if fecha_ocurrencia

                    else None

                ),

                personal_uso,

                personal_lavado,

                observacion

            )

            st.success(

                f"✓ Información de {codigo} "

                "guardada correctamente."

            )

            st.rerun()

# ============================================================

# MANTENIMIENTOS

# ============================================================

elif pagina == "Mantenimientos":

    st.subheader(

        "🔧 Mantenimientos"

    )

    # Contador para limpiar el formulario después de guardar

    if "mant_form_id" not in st.session_state:

        st.session_state["mant_form_id"] = 0

    fid = st.session_state["mant_form_id"]

    mensaje_ok = st.session_state.pop(

        "mant_mensaje_ok",

        None

    )

    if mensaje_ok:

        st.success(

            mensaje_ok

        )

    # --------------------------------------------------------

    # REGISTRAR MANTENIMIENTO

    # --------------------------------------------------------

    st.markdown(

        "### ➕ Registrar mantenimiento"

    )

    codigos_mant = set(

        equipos["codigo"]

        .astype(str)

        .tolist()

    )

    if (

        listado_excel is not None

        and "CÓDIGO" in listado_excel.columns

    ):

        codigos_mant |= set(

            listado_excel["CÓDIGO"]

            .astype(str)

            .tolist()

        )

    codigos_mant = sorted(

        codigos_mant

    )

    if not codigos_mant:

        st.info(

            "No hay equipos disponibles todavía. "

            "Registra un equipo en Administración "

            "o revisa el archivo 'Listado equipos.xlsx'."

        )

    else:

        col1, col2 = st.columns(2)

        with col1:

            codigo_mant = st.selectbox(

                "Equipo",

                codigos_mant,

                key=f"mant_codigo_{fid}"

            )

            tipo_mant = st.selectbox(

                "Tipo de mantenimiento",

                TIPOS_MANTENIMIENTO,

                key=f"mant_tipo_{fid}"

            )

        with col2:

            proveedor_mant = st.text_input(

                "Proveedor",

                placeholder="Ej. Nombre de la empresa",

                key=f"mant_proveedor_{fid}"

            )

            fecha_mant = st.date_input(

                "📅 Fecha del mantenimiento",

                value=date.today(),

                format="DD/MM/YYYY",

                key=f"mant_fecha_{fid}"

            )

        obs_mant = st.text_area(

            "Observaciones",

            placeholder="Detalle del mantenimiento realizado...",

            key=f"mant_obs_{fid}"

        )

        certificado_mant = st.file_uploader(

            "📎 Certificado del mantenimiento (PDF)",

            type=["pdf"],

            key=f"mant_certificado_{fid}"

        )

        if st.button(

            "💾 Guardar mantenimiento",

            type="primary",

            key="btn_guardar_mant"

        ):

            if not proveedor_mant.strip():

                st.error(

                    "Debes ingresar el proveedor."

                )

            else:

                guardar_mantenimiento(

                    codigo_mant,

                    tipo_mant,

                    proveedor_mant.strip(),

                    str(fecha_mant),

                    obs_mant,

                    certificado_mant

                )

                st.session_state["mant_mensaje_ok"] = (

                    f"✓ Mantenimiento "

                    f"{tipo_mant.lower()} de "

                    f"{codigo_mant} guardado "

                    f"correctamente."

                )

                st.session_state["mant_form_id"] += 1

                st.rerun()

    st.divider()

    # --------------------------------------------------------

    # HISTORIAL

    # --------------------------------------------------------

    st.markdown(

        "### 📋 Historial de mantenimientos"

    )

    buscar_mant = st.text_input(

        "Buscar por equipo",

        placeholder="Ej. OPT-002",

        key="mant_buscar"

    )

    historial = mantenimientos.copy()

    if buscar_mant:

        historial = historial[

            historial["codigo_equipo"]

            .str.contains(

                buscar_mant,

                case=False,

                na=False

            )

        ]

    tab_todos, tab_prev, tab_corr = st.tabs(

        [

            "Todos",

            "🛠️ Preventivos",

            "🔧 Correctivos"

        ]

    )

    with tab_todos:

        mostrar_tabla_mantenimientos(

            historial,

            "todos"

        )

    with tab_prev:

        mostrar_tabla_mantenimientos(

            historial[

                historial["tipo_mantenimiento"]

                == "Preventivo"

            ],

            "prev"

        )

    with tab_corr:

        mostrar_tabla_mantenimientos(

            historial[

                historial["tipo_mantenimiento"]

                == "Correctivo"

            ],

            "corr"

        )

# ============================================================

# LISTADO DE EQUIPOS

# ============================================================

elif pagina == "Listado de equipos":

    st.subheader(

        "📋 Listado de equipos"

    )

    # --------------------------------------------------------

    # COMPROBAR EXCEL

    # --------------------------------------------------------

    if listado_excel is None:

        st.error(

            "No se encontró el archivo "

            "'Listado equipos.xlsx'."

        )

        st.info(

            "Coloca 'Listado equipos.xlsx' "

            "en la misma carpeta donde está "

            "EQUIPOS.py."

        )

        st.stop()

    # --------------------------------------------------------

    # RESUMEN

    # --------------------------------------------------------

    total_excel = len(

        listado_excel

    )

    st.info(

        f"📁 Inventario maestro: "

        f"{total_excel} equipos registrados "

        f"en el archivo de equipos."

    )

    # --------------------------------------------------------

    # PREPARAR LISTADO

    # --------------------------------------------------------

    listado = listado_excel.copy()

    # --------------------------------------------------------

    # AGREGAR INFORMACIÓN DEL SISTEMA

    # --------------------------------------------------------

    if "CÓDIGO" in listado.columns:

        listado["CÓDIGO"] = (

            listado["CÓDIGO"]

            .astype(str)

            .str.strip()

        )

    if not equipos.empty:

        estados_db = equipos[

            [

                "codigo",

                "estado",

                "personal_uso"

            ]

        ].copy()

        estados_db["estado"] = [

            texto_estado(

                estado_db,

                personal_db

            )

            for estado_db, personal_db in zip(

                estados_db["estado"],

                estados_db["personal_uso"]

            )

        ]

        estados_db = estados_db[

            [

                "codigo",

                "estado"

            ]

        ].rename(

            columns={

                "codigo": "CÓDIGO",

                "estado": "ESTADO ACTUAL"

            }

        )

        listado = listado.merge(

            estados_db,

            on="CÓDIGO",

            how="left"

        )

        listado["ESTADO ACTUAL"] = (

            listado["ESTADO ACTUAL"]

            .fillna("No registrado")

        )

    else:

        listado["ESTADO ACTUAL"] = (

            "No registrado"

        )

    # --------------------------------------------------------

    # ÚLTIMO USO

    # --------------------------------------------------------

    ultimos_usos = []

    for codigo in listado["CÓDIGO"]:

        ultimo = calcular_ultimo_uso(

            codigo,

            usos

        )

        ultimos_usos.append(

            formatear_fecha(

                ultimo

            )

        )

    listado["ÚLTIMO USO"] = (

        ultimos_usos

    )

    # --------------------------------------------------------

    # DÍAS SIN USO

    # --------------------------------------------------------

    dias_sin_uso = []

    for codigo in listado["CÓDIGO"]:

        dias = calcular_dias_sin_uso(

            codigo,

            usos

        )

        if dias is None:

            dias_sin_uso.append(

                "-"

            )

        else:

            dias_sin_uso.append(

                dias

            )

    listado["DÍAS SIN USO"] = (

        dias_sin_uso

    )

    # --------------------------------------------------------

    # ÚLTIMO MANTENIMIENTO

    # --------------------------------------------------------

    ultimos_mantenimientos = []

    for codigo in listado["CÓDIGO"]:

        ultimo_mant = obtener_ultimo_mantenimiento(

            codigo,

            obtener_fila_equipo(

                codigo,

                equipos

            ),

            mantenimientos

        )

        ultimos_mantenimientos.append(

            formatear_fecha(

                ultimo_mant

            )

        )

    listado["ÚLTIMO MANTENIMIENTO"] = (

        ultimos_mantenimientos

    )

    # --------------------------------------------------------

    # ÚLTIMO LAVADO

    # --------------------------------------------------------

    ultimos_lavados = []

    for codigo in listado["CÓDIGO"]:

        fila_eq = obtener_fila_equipo(

            codigo,

            equipos

        )

        if fila_eq is None:

            ultimos_lavados.append(

                "Sin registro"

            )

            continue

        texto_lavado = formatear_fecha(

            fila_eq.get(

                "fecha_lavado"

            )

        )

        if (

            texto_lavado != "Sin registro"

            and not pd.isna(

                fila_eq.get(

                    "personal_lavado"

                )

            )

        ):

            texto_lavado = (

                f"{texto_lavado} por "

                f"{fila_eq.get('personal_lavado')}"

            )

        ultimos_lavados.append(

            texto_lavado

        )

    listado["ÚLTIMO LAVADO"] = (

        ultimos_lavados

    )

    # --------------------------------------------------------

    # ORDENAR COLUMNAS

    # --------------------------------------------------------

    columnas_sistema = [

        "ESTADO ACTUAL",

        "ÚLTIMO USO",

        "DÍAS SIN USO",

        "ÚLTIMO MANTENIMIENTO",

        "ÚLTIMO LAVADO"

    ]

    columnas_originales = [

        columna

        for columna in listado_excel.columns

        if columna in listado.columns

    ]

    columnas_finales = (

        columnas_originales

        +

        [

            columna

            for columna in columnas_sistema

            if columna in listado.columns

        ]

    )

    listado = listado[

        columnas_finales

    ]

    # --------------------------------------------------------

    # FILTROS

    # --------------------------------------------------------

    st.markdown(

        "### 🔎 Buscar y filtrar"

    )

    col1, col2, col3 = st.columns(3)

    with col1:

        busqueda_codigo = st.text_input(

            "Buscar por código",

            placeholder="Ej. OPT-023"

        )

    with col2:

        if "MARCA" in listado.columns:

            marcas = [

                "Todas"

            ] + sorted(

                listado["MARCA"]

                .dropna()

                .astype(str)

                .unique()

                .tolist()

            )

            filtro_marca = st.selectbox(

                "Marca",

                marcas

            )

        else:

            filtro_marca = "Todas"

    with col3:

        if "DESCRIPCIÓN" in listado.columns:

            descripciones = [

                "Todos"

            ] + sorted(

                listado["DESCRIPCIÓN"]

                .dropna()

                .astype(str)

                .unique()

                .tolist()

            )

            filtro_tipo_equipo = st.selectbox(

                "Descripción",

                descripciones

            )

        else:

            filtro_tipo_equipo = "Todos"

    listado_filtrado = (

        listado.copy()

    )

    # --------------------------------------------------------

    # FILTRO CÓDIGO

    # --------------------------------------------------------

    if busqueda_codigo:

        listado_filtrado = (

            listado_filtrado[

                listado_filtrado["CÓDIGO"]

                .str.contains(

                    busqueda_codigo,

                    case=False,

                    na=False

                )

            ]

        )

    # --------------------------------------------------------

    # FILTRO MARCA

    # --------------------------------------------------------

    if (

        filtro_marca != "Todas"

        and "MARCA" in listado_filtrado.columns

    ):

        listado_filtrado = (

            listado_filtrado[

                listado_filtrado["MARCA"]

                .astype(str)

                == filtro_marca

            ]

        )

    # --------------------------------------------------------

    # FILTRO DESCRIPCIÓN

    # --------------------------------------------------------

    if (

        filtro_tipo_equipo != "Todos"

        and "DESCRIPCIÓN"

        in listado_filtrado.columns

    ):

        listado_filtrado = (

            listado_filtrado[

                listado_filtrado[

                    "DESCRIPCIÓN"

                ].astype(str)

                == filtro_tipo_equipo

            ]

        )

    # --------------------------------------------------------

    # RESULTADOS

    # --------------------------------------------------------

    st.markdown(

        f"**{len(listado_filtrado)} "

        f"equipos encontrados**"

    )

    # --------------------------------------------------------

    # TABLA COMPLETA

    # --------------------------------------------------------

    st.dataframe(

        listado_filtrado,

        use_container_width=True,

        hide_index=True,

        height=550

    )

    st.divider()

    # ========================================================

    # FICHA INDIVIDUAL

    # ========================================================

    st.markdown(

        "### 🔍 Ficha del equipo"

    )

    if len(listado_filtrado) > 0:

        codigos_disponibles = (

            listado_filtrado[

                "CÓDIGO"

            ]

            .astype(str)

            .tolist()

        )

        codigo_seleccionado = st.selectbox(

            "Selecciona un equipo",

            codigos_disponibles

        )

        equipo_seleccionado = (

            listado_filtrado[

                listado_filtrado["CÓDIGO"]

                == codigo_seleccionado

            ]

            .iloc[0]

        )

        st.markdown(

            f"## 🧪 {codigo_seleccionado}"

        )

        # ----------------------------------------------------

        # INFORMACIÓN PRINCIPAL

        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            if "DESCRIPCIÓN" in equipo_seleccionado.index:

                st.write(

                    "**Descripción**"

                )

                st.write(

                    equipo_seleccionado[

                        "DESCRIPCIÓN"

                    ]

                )

            if "MARCA" in equipo_seleccionado.index:

                st.write(

                    "**Marca**"

                )

                st.write(

                    equipo_seleccionado[

                        "MARCA"

                    ]

                )

        with col2:

            if "MODELO/MÓDULOS" in equipo_seleccionado.index:

                st.write(

                    "**Modelo / módulos**"

                )

                st.write(

                    equipo_seleccionado[

                        "MODELO/MÓDULOS"

                    ]

                )

            if "SERIE/SERIE MÓDULOS/LOTE" in equipo_seleccionado.index:

                st.write(

                    "**Serie / serie módulos / lote**"

                )

                st.write(

                    equipo_seleccionado[

                        "SERIE/SERIE MÓDULOS/LOTE"

                    ]

                )

        with col3:

            if "EQUIPO MÓVIL" in equipo_seleccionado.index:

                st.write(

                    "**Equipo móvil**"

                )

                st.write(

                    equipo_seleccionado[

                        "EQUIPO MÓVIL"

                    ]

                )

            if "CATEGORIZACIÓN DE EQUIPO" in equipo_seleccionado.index:

                st.write(

                    "**Categorización**"

                )

                st.write(

                    equipo_seleccionado[

                        "CATEGORIZACIÓN DE EQUIPO"

                    ]

                )

        st.divider()

        # ----------------------------------------------------

        # ESTADO DEL SISTEMA

        # ----------------------------------------------------

        st.markdown(

            "### 📊 Información del sistema"

        )

        col1, col2, col3, col4 = st.columns(4)

        estado_actual = equipo_seleccionado.get(

            "ESTADO ACTUAL"

        )

        if pd.isna(

            estado_actual

        ):

            estado_actual = (

                "No registrado"

            )

        with col1:

            st.metric(

                "Estado actual",

                estado_actual

            )

        with col2:

            st.metric(

                "Último uso",

                equipo_seleccionado.get(

                    "ÚLTIMO USO",

                    "Sin registro"

                )

            )

        with col3:

            st.metric(

                "Días sin uso",

                equipo_seleccionado.get(

                    "DÍAS SIN USO",

                    "-"

                )

            )

        with col4:

            ultimo_mantenimiento = (

                equipo_seleccionado.get(

                    "ÚLTIMO MANTENIMIENTO",

                    "Sin registro"

                )

            )

            if pd.isna(

                ultimo_mantenimiento

            ):

                ultimo_mantenimiento = (

                    "Sin registro"

                )

            st.metric(

                "Último mantenimiento",

                ultimo_mantenimiento

            )

        st.write(

            f"**Último lavado:** "

            f"{equipo_seleccionado.get('ÚLTIMO LAVADO', 'Sin registro')}"

        )

        st.divider()

        # ----------------------------------------------------

        # TODA LA INFORMACIÓN DEL EXCEL

        # ----------------------------------------------------

        st.markdown(

            "### 📋 Información completa del equipo"

        )

        datos_detalle = []

        for columna in columnas_originales:

            valor = (

                equipo_seleccionado[

                    columna

                ]

            )

            if pd.isna(valor):

                valor = "Sin registro"

            elif isinstance(

                valor,

                pd.Timestamp

            ):

                valor = valor.strftime(

                    "%d/%m/%Y"

                )

            datos_detalle.append({

                "Campo": columna,

                "Información": str(

                    valor

                )

            })

        st.dataframe(

            pd.DataFrame(

                datos_detalle

            ),

            use_container_width=True,

            hide_index=True,

            height=500

        )

    else:

        st.warning(

            "No hay equipos que coincidan "

            "con los filtros seleccionados."

        )