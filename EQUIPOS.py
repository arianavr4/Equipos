import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
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

        ("fecha_ocurrencia", "TEXT")
    ]

    for nombre_columna, tipo in nuevas_columnas:

        if nombre_columna not in columnas_existentes:

            cursor.execute(
                f"""
                ALTER TABLE equipos
                ADD COLUMN {nombre_columna} {tipo}
                """
            )

    conn.commit()

    conn.close()


crear_tablas()


# ============================================================
# LEER EXCEL DE EQUIPOS
# ============================================================

@st.cache_data
def cargar_listado_excel():

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


listado_excel = cargar_listado_excel()


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


def guardar_equipo(
    codigo,
    tipo,
    estado,
    fecha_uso,
    fecha_mantenimiento_preventivo,
    fecha_lavado,
    fecha_ocurrencia,
    observacion
):

    conn = conectar_db()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO equipos
        (
            codigo,
            tipo,
            estado,
            fecha_uso,
            fecha_mantenimiento_preventivo,
            fecha_lavado,
            fecha_ocurrencia,
            observacion
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        codigo,

        tipo,

        estado,

        fecha_uso,

        fecha_mantenimiento_preventivo,

        fecha_lavado,

        fecha_ocurrencia,

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

    "De baja",

    "Lavado integral",

    "Mantenimiento preventivo",

    "Ocurrencias"
]


def obtener_icono_estado(
    estado
):

    iconos = {

        "Operativo": "🟢",

        "En uso": "🔵",

        "De baja": "⚫",

        "Lavado integral": "🧼",

        "Mantenimiento preventivo": "🔧",

        "Ocurrencias": "⚠️"
    }

    return iconos.get(
        estado,
        "⚪"
    )


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
# DATOS ACTUALES
# ============================================================

equipos = obtener_equipos()

usos = obtener_usos()


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

            "Mantenimentos",

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

    baja = len(
        equipos[
            equipos["estado"]
            == "De baja"
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
            "DE BAJA",
            baja
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
                        equipo.get(
                            "ultimo_mantenimiento"
                        )
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
                                f"{estado}"
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

                observacion
            )


            st.success(
                f"✓ Información de {codigo} "
                "guardada correctamente."
            )


            st.rerun()


# ============================================================
# INFORMACIÓN SOBRE MANTENIMIENTOS
# ============================================================

elif pagina == "Información sobre mantenimentos":

    st.subheader(
        "🔧 Información sobre mantenimentos"
    )

    st.info(
        "Esta sección será desarrollada posteriormente."
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
                "ultimo_mantenimiento"
            ]
        ].copy()


        estados_db = estados_db.rename(
            columns={
                "codigo": "CÓDIGO",
                "estado": "ESTADO ACTUAL",
                "ultimo_mantenimiento":
                    "ÚLTIMO MANTENIMIENTO"
            }
        )


        listado = listado.merge(
            estados_db,
            on="CÓDIGO",
            how="left"
        )

    else:

        listado["ESTADO ACTUAL"] = (
            "No registrado"
        )

        listado["ÚLTIMO MANTENIMIENTO"] = (
            None
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
    # ORDENAR COLUMNAS
    # --------------------------------------------------------

    columnas_sistema = [

        "ESTADO ACTUAL",

        "ÚLTIMO USO",

        "DÍAS SIN USO",

        "ÚLTIMO MANTENIMIENTO"
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
                formatear_fecha(
                    ultimo_mantenimiento
                )
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


