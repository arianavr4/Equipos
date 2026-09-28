import streamlit as st
import pandas as pd
import sqlite3
from datetime import date


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Equipment Monitoring Dashboard",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "equipment_dashboard.db"


# ============================================================
# ESTILO VISUAL
# ============================================================

st.markdown("""
<style>

    /* Fondo general */
    .stApp {
        background-color: #F4F7FA;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #003B5C;
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Títulos */
    h1, h2, h3 {
        color: #003B5C !important;
    }

    /* Métricas */
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

    /* Botones */
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

    /* Contenedores */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 12px;
        border: 1px solid #DCE5EC;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border-radius: 10px;
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_equipo TEXT NOT NULL,
            fecha TEXT NOT NULL,
            tipo_registro TEXT NOT NULL,
            observacion TEXT
        )
    """)

    conn.commit()
    conn.close()


crear_tablas()


# ============================================================
# FUNCIONES BASE DE DATOS
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


def registrar_uso(
    codigo,
    fecha,
    tipo_registro,
    observacion
):

    conn = conectar_db()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usos
        (
            codigo_equipo,
            fecha,
            tipo_registro,
            observacion
        )
        VALUES (?, ?, ?, ?)
    """, (
        codigo,
        str(fecha),
        tipo_registro,
        observacion
    ))

    conn.commit()
    conn.close()


def agregar_equipo(
    codigo,
    tipo,
    estado,
    ubicacion,
    ultimo_mantenimiento,
    proximo_mantenimiento,
    observacion
):

    conn = conectar_db()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO equipos
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        codigo,
        tipo,
        estado,
        ubicacion,
        ultimo_mantenimiento,
        proximo_mantenimiento,
        observacion
    ))

    conn.commit()
    conn.close()


# ============================================================
# FUNCIONES DE CÁLCULO
# ============================================================

def calcular_ultimo_uso(codigo, usos):

    registros = usos[
        (usos["codigo_equipo"] == codigo)
        &
        (usos["tipo_registro"] == "Uso")
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


def calcular_dias_sin_uso(codigo, usos):

    ultimo_uso = calcular_ultimo_uso(
        codigo,
        usos
    )

    if ultimo_uso is None:
        return None

    return (
        date.today() - ultimo_uso
    ).days


def determinar_alerta(dias):

    if dias is None:
        return "⚪ Sin información"

    if dias <= 7:
        return "🟢 Uso reciente"

    if dias <= 14:
        return "🟡 Revisar"

    return "🔴 Sin uso prolongado"


def obtener_icono_estado(estado):

    if estado == "Operativo":
        return "🟢"

    if estado == "En uso":
        return "🔵"

    if estado == "En mantenimiento":
        return "🟡"

    if estado == "Fuera de servicio":
        return "🔴"

    if estado == "De baja":
        return "⚫"

    return "⚪"


# ============================================================
# CARGAR INFORMACIÓN
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
        "## MONITOREO DIGITAL DE EQUIPOS"
    )

    st.caption(
        "Equipment management"
    )

    st.divider()

    pagina = st.radio(
        "NAVEGACIÓN",
        [
            "Dashboard",
            "Equipos",
            "Registrar uso",
            "Administración"
        ]
    )

    st.divider()

    st.caption(
        "Prototype v0.2"
    )


# ============================================================
# ENCABEZADO
# ============================================================

st.title(
    "Monitoreo de equipos"
)

st.caption(
    "Monitoreo de estado, utilización y alertas de equipos"
)

st.divider()


# ============================================================
# DASHBOARD
# ============================================================

if pagina == "Dashboard":

    st.subheader(
        "📊 Resumen general"
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    total = len(equipos)

    operativos = len(
        equipos[
            equipos["estado"] == "Operativo"
        ]
    )

    en_uso = len(
        equipos[
            equipos["estado"] == "En uso"
        ]
    )

    baja = len(
        equipos[
            equipos["estado"] == "De baja"
        ]
    )

    sin_uso = 0

    for codigo in equipos["codigo"]:

        dias = calcular_dias_sin_uso(
            codigo,
            usos
        )

        if dias is not None and dias > 14:
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


    # --------------------------------------------------------
    # ALERTAS
    # --------------------------------------------------------

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

        if dias is not None and dias > 14:

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


    # --------------------------------------------------------
    # TABLA
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "🖥️ Estado de equipos"
    )

    if equipos.empty:

        st.info(
            "Todavía no hay equipos registrados."
        )

    else:

        datos_dashboard = []

        for _, equipo in equipos.iterrows():

            codigo = equipo["codigo"]

            ultimo_uso = calcular_ultimo_uso(
                codigo,
                usos
            )

            dias = calcular_dias_sin_uso(
                codigo,
                usos
            )

            if ultimo_uso:

                ultimo_uso_texto = (
                    ultimo_uso.strftime(
                        "%d/%m/%Y"
                    )
                )

            else:

                ultimo_uso_texto = "Sin registro"


            datos_dashboard.append({

                "Código": codigo,

                "Tipo": equipo["tipo"],

                "Estado": (
                    f"{obtener_icono_estado(equipo['estado'])} "
                    f"{equipo['estado']}"
                ),

                "Ubicación": (
                    equipo["ubicacion"]
                    if equipo["ubicacion"]
                    else "-"
                ),

                "Último uso": ultimo_uso_texto,

                "Días sin uso": (
                    dias
                    if dias is not None
                    else "-"
                ),

                "Alerta": determinar_alerta(
                    dias
                )

            })


        df_dashboard = pd.DataFrame(
            datos_dashboard
        )

        st.dataframe(
            df_dashboard,
            use_container_width=True,
            hide_index=True
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
            "No hay equipos registrados todavía."
        )

    else:

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        col1, col2, col3 = st.columns(3)

        with col1:

            estados = (
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
                estados
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


        # ----------------------------------------------------
        # TARJETAS
        # ----------------------------------------------------

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


                    if ultimo_uso:

                        ultimo_uso_texto = (
                            ultimo_uso.strftime(
                                "%d/%m/%Y"
                            )
                        )

                    else:

                        ultimo_uso_texto = (
                            "Sin registro"
                        )


                    with columna:

                        with st.container(
                            border=True
                        ):

                            st.markdown(
                                f"### {obtener_icono_estado(estado)} {codigo}"
                            )

                            st.caption(
                                equipo["tipo"]
                            )

                            st.write(
                                f"**Estado:** {estado}"
                            )

                            st.write(
                                f"**Último uso:** "
                                f"{ultimo_uso_texto}"
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

                            ubicacion = (
                                equipo["ubicacion"]
                                if equipo["ubicacion"]
                                else "No registrada"
                            )

                            st.write(
                                f"**Ubicación:** "
                                f"{ubicacion}"
                            )


# ============================================================
# REGISTRAR USO
# ============================================================

elif pagina == "Registrar uso":

    st.subheader(
        "📝 Registrar uso"
    )

    st.info(
        "El registro digital complementa el "
        "registro físico del cuadernillo."
    )


    if equipos.empty:

        st.warning(
            "Primero debes registrar los equipos."
        )

    else:

        lista_equipos = (
            equipos["codigo"].tolist()
        )


        with st.form(
            "formulario_uso"
        ):

            codigo = st.selectbox(
                "Equipo",
                lista_equipos
            )

            fecha = st.date_input(
                "Fecha",
                value=date.today()
            )

            tipo_registro = st.selectbox(
                "Tipo de registro",
                [
                    "Uso",
                    "Mantenimiento",
                    "Fuera de servicio",
                    "Otro"
                ]
            )

            observacion = st.text_area(
                "Observación",
                placeholder="Opcional..."
            )

            guardar = st.form_submit_button(
                "💾 Guardar registro"
            )


            if guardar:

                registrar_uso(
                    codigo,
                    fecha,
                    tipo_registro,
                    observacion
                )

                st.success(
                    f"✓ Registro guardado para {codigo}"
                )

                st.rerun()


# ============================================================
# ADMINISTRACIÓN
# ============================================================

elif pagina == "Administración":

    st.subheader(
        "⚙️ Administración"
    )

    st.info(
        "Esta sección permite agregar o actualizar "
        "la información de los equipos."
    )


    with st.form(
        "formulario_equipo"
    ):

        st.markdown(
            "### Agregar / actualizar equipo"
        )


        col1, col2 = st.columns(2)


        with col1:

            codigo = st.text_input(
                "Código del equipo",
                placeholder="Ej. OPT-001"
            )

            tipo = st.text_input(
                "Tipo",
                value="HPLC"
            )

            estado = st.selectbox(
                "Estado",
                [
                    "Operativo",
                    "En uso",
                    "En mantenimiento",
                    "Fuera de servicio",
                    "De baja"
                ]
            )


        with col2:

            ubicacion = st.text_input(
                "Ubicación",
                placeholder="Ej. Laboratorio 1"
            )

            ultimo_mantenimiento = st.date_input(
                "Último mantenimiento",
                value=date.today()
            )

            proximo_mantenimiento = st.date_input(
                "Próximo mantenimiento",
                value=date.today()
            )


        observacion = st.text_area(
            "Observación"
        )


        guardar_equipo = st.form_submit_button(
            "💾 Guardar equipo"
        )


        if guardar_equipo:

            if not codigo:

                st.error(
                    "Debes ingresar el código del equipo."
                )

            else:

                agregar_equipo(
                    codigo,
                    tipo,
                    estado,
                    ubicacion,
                    str(
                        ultimo_mantenimiento
                    ),
                    str(
                        proximo_mantenimiento
                    ),
                    observacion
                )

                st.success(
                    f"✓ Equipo {codigo} guardado correctamente."
                )

                st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Dasboard de monitoreo de equipos"
)