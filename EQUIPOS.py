import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# CONFIGURACIÓN

st.set_page_config(
    page_title="Dashboard de monitoreo de equipos",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "equipment_dashboard.db"


# THEME
st.markdown("""
<style>

    /* COLORES PRINCIPALES */

    :root {
        --blue-dark: #003B5C;
        --blue: #0072CE;
        --blue-light: #EAF4FB;
        --blue-soft: #F4F8FB;
        --text-dark: #243746;
        --text-gray: #64748B;
        --border: #D9E2EA;
        --white: #FFFFFF;
    }


    /* FONDO GENERAL */

    .stApp {
        background-color: #F4F7FA;
    }


    /* SIDEBAR */

    [data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #003B5C 0%,
            #005B82 100%
        );
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        padding: 8px 4px;
        border-radius: 6px;
    }


    /*HEADER PRINCIPAL */

    .main-header {
        background: linear-gradient(
            135deg,
            #003B5C 0%,
            #006DAA 100%
        );

        padding: 28px 35px;
        border-radius: 14px;
        margin-bottom: 25px;

        box-shadow: 0 4px 12px rgba(0, 59, 92, 0.15);
    }

    .main-header h1 {
        color: white;
        font-size: 30px;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.3px;
    }

    .main-header p {
        color: #DCECF5;
        font-size: 14px;
        margin-top: 6px;
        margin-bottom: 0;
    }


    /* TÍTULOS DE SECCIÓN */

    .section-title {
        color: #003B5C;
        font-size: 21px;
        font-weight: 700;
        margin-top: 10px;
        margin-bottom: 15px;
    }


    /* TARJETAS KPI */

    .kpi-card {
        background-color: white;
        border: 1px solid #DCE5EC;
        border-radius: 12px;
        padding: 20px 22px;
        min-height: 125px;

        box-shadow: 0 2px 8px rgba(0, 59, 92, 0.06);
    }

    .kpi-label {
        color: #64748B;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .kpi-number {
        color: #003B5C;
        font-size: 32px;
        font-weight: 750;
        margin-top: 8px;
    }

    .kpi-description {
        color: #64748B;
        font-size: 12px;
        margin-top: 3px;
    }


    /* ALERTAS */

    .alert-box {
        background-color: white;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 10px;

        border-left: 5px solid #E53935;

        box-shadow: 0 2px 7px rgba(0,0,0,0.05);
    }

    .alert-box.warning {
        border-left: 5px solid #F4B400;
    }

    .alert-title {
        color: #243746;
        font-weight: 700;
        font-size: 15px;
    }

    .alert-text {
        color: #64748B;
        font-size: 13px;
        margin-top: 3px;
    }


    /*TARJETAS DE EQUIPOS */

    .equipment-card {
        background-color: white;
        border: 1px solid #DCE5EC;
        border-radius: 12px;
        padding: 18px;

        margin-bottom: 15px;

        box-shadow: 0 2px 8px rgba(0, 59, 92, 0.05);

        min-height: 175px;
    }

    .equipment-code {
        color: #003B5C;
        font-size: 19px;
        font-weight: 750;
    }

    .equipment-type {
        color: #64748B;
        font-size: 12px;
        margin-top: 2px;
    }

    .equipment-info {
        color: #475569;
        font-size: 13px;
        margin-top: 12px;
        line-height: 1.7;
    }


    /* BADGES DE ESTADO */

    .status {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;

        font-size: 11px;
        font-weight: 700;

        margin-top: 10px;
    }

    .status-operativo {
        background-color: #E7F6EC;
        color: #187A3D;
    }

    .status-uso {
        background-color: #E7F2FC;
        color: #0067A5;
    }

    .status-mantenimiento {
        background-color: #FFF4D6;
        color: #986F00;
    }

    .status-fuera {
        background-color: #FDECEC;
        color: #B42318;
    }

    .status-baja {
        background-color: #E9EDF1;
        color: #52616B;
    }


    /* SEPARADORES */

    hr {
        border: none;
        border-top: 1px solid #DCE5EC;
        margin: 25px 0;
    }


    /*BOTONES */

    .stButton > button {
        border-radius: 7px;
        border: none;
        background-color: #0072CE;
        color: white;
        font-weight: 600;
    }

    .stButton > button:hover {
        background-color: #005B9F;
        color: white;
    }


    /* DATAFRAMES / TABLAS */

    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }


    /* PIE */

    .footer {
        text-align: center;
        color: #94A3B8;
        font-size: 11px;
        padding: 25px 0 10px 0;
    }

</style>
""", unsafe_allow_html=True)


# BASE DE DATOS
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

# FUNCIONES DE BASE DE DATOS
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
        (codigo_equipo, fecha, tipo_registro, observacion)
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

# FUNCIONES DE CÁLCULO
def calcular_ultimo_uso(codigo, usos):

    registros = usos[
        (usos["codigo_equipo"] == codigo) &
        (usos["tipo_registro"] == "Uso")
    ]

    if registros.empty:
        return None

    fechas = pd.to_datetime(
        registros["fecha"],
        errors="coerce"
    )

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

    elif dias <= 14:
        return "🟡 Revisar"

    else:
        return "🔴 Sin uso prolongado"


def obtener_clase_estado(estado):

    if estado == "Operativo":
        return "status-operativo"

    if estado == "En uso":
        return "status-uso"

    if estado == "En mantenimiento":
        return "status-mantenimiento"

    if estado == "Fuera de servicio":
        return "status-fuera"

    if estado == "De baja":
        return "status-baja"

    return "status-baja"


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

# DATOS
equipos = obtener_equipos()
usos = obtener_usos()

# SIDEBAR
with st.sidebar:

    st.markdown(
        """
        <div style="
            text-align:center;
            padding: 15px 5px 25px 5px;
        ">
            <div style="
                font-size:35px;
                margin-bottom:8px;
            ">
                🧪
            </div>

            <div style="
                font-size:18px;
                font-weight:700;
            ">
                EQUIPMENT
            </div>

            <div style="
                font-size:18px;
                font-weight:700;
            ">
                MONITORING
            </div>

            <div style="
                font-size:11px;
                opacity:0.75;
                margin-top:5px;
            ">
                Equipment management
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    pagina = st.radio(
        "NAVEGACIÓN",
        [
            "Dashboard",
            "Equipos",
            "Registrar uso",
            "Administración"
        ]
    )

    st.markdown("---")

    st.caption(
        "Prototype v0.2"
    )

# HEADER
st.markdown(
    """
    <div class="main-header">

        <h1>
            Equipment Monitoring Dashboard
        </h1>

        <p>
            Monitoreo de estado, utilización y alertas de equipos
        </p>

    </div>
    """,
    unsafe_allow_html=True
)

# DASHBOARD
if pagina == "Dashboard":

    # CÁLCULO DE KPIs

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

    # KPIs
    st.markdown(
        '<div class="section-title">Resumen general</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Total equipos
                </div>

                <div class="kpi-number">
                    {total}
                </div>

                <div class="kpi-description">
                    Equipos registrados
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with col2:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Operativos
                </div>

                <div class="kpi-number">
                    {operativos}
                </div>

                <div class="kpi-description">
                    Disponibles
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with col3:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    En uso
                </div>

                <div class="kpi-number">
                    {en_uso}
                </div>

                <div class="kpi-description">
                    Uso actual
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with col4:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    Sin uso
                </div>

                <div class="kpi-number">
                    {sin_uso}
                </div>

                <div class="kpi-description">
                    Más de 14 días
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )


    with col5:

        st.markdown(
            f"""
            <div class="kpi-card">

                <div class="kpi-label">
                    De baja
                </div>

                <div class="kpi-number">
                    {baja}
                </div>

                <div class="kpi-description">
                    No disponibles
                </div>

            </div>
            """,
            unsafe_allow_html=True
        )

    # ALERTAS
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">⚠️ Alertas</div>',
        unsafe_allow_html=True
    )

    alertas = []

    for _, equipo in equipos.iterrows():

        codigo = equipo["codigo"]

        dias = calcular_dias_sin_uso(
            codigo,
            usos
        )

        if dias is not None and dias > 14:

            alertas.append({
                "codigo": codigo,
                "dias": dias
            })


    if alertas:

        for alerta in alertas:

            st.markdown(
                f"""
                <div class="alert-box">

                    <div class="alert-title">
                        🔴 {alerta["codigo"]}
                    </div>

                    <div class="alert-text">
                        El equipo lleva
                        <b>{alerta["dias"]} días</b>
                        sin registrar uso.
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    else:

        st.success(
            "No hay alertas de equipos sin uso prolongado."
        )

    # ESTADO DE EQUIPOS
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        '<div class="section-title">Estado de equipos</div>',
        unsafe_allow_html=True
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

            datos_dashboard.append({

                "Código": codigo,

                "Tipo": equipo["tipo"],

                "Estado": equipo["estado"],

                "Ubicación": equipo["ubicacion"],

                "Último uso": (
                    ultimo_uso
                    if ultimo_uso
                    else "Sin registro"
                ),

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

# EQUIPOS
elif pagina == "Equipos":

    st.markdown(
        '<div class="section-title">🖥️ Equipos registrados</div>',
        unsafe_allow_html=True
    )


    if equipos.empty:

        st.info(
            "No hay equipos registrados todavía."
        )

    else:
        # FILTROS
        col1, col2, col3 = st.columns(3)


        with col1:

            estados = [
                "Todos"
            ] + sorted(
                equipos["estado"]
                .dropna()
                .unique()
                .tolist()
            )

            filtro_estado = st.selectbox(
                "Estado",
                estados
            )


        with col2:

            tipos = [
                "Todos"
            ] + sorted(
                equipos["tipo"]
                .dropna()
                .unique()
                .tolist()
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

        # APLICAR FILTROS
        filtrados = equipos.copy()


        if filtro_estado != "Todos":

            filtrados = filtrados[
                filtrados["estado"] == filtro_estado
            ]


        if filtro_tipo != "Todos":

            filtrados = filtrados[
                filtrados["tipo"] == filtro_tipo
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


        st.markdown("<br>", unsafe_allow_html=True)

        # TARJETAS
        if filtrados.empty:

            st.warning(
                "No se encontraron equipos."
            )

        else:

            filas = [
                filtrados.iloc[i:i+3]
                for i in range(
                    0,
                    len(filtrados),
                    3
                )
            ]


            for fila in filas:

                columnas = st.columns(3)


                for columna, (_, equipo) in zip(
                    columnas,
                    fila.iterrows()
                ):

                    codigo = equipo["codigo"]

                    estado = equipo["estado"]

                    icono = obtener_icono_estado(
                        estado
                    )

                    clase = obtener_clase_estado(
                        estado
                    )

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

                        ultimo_uso_texto = (
                            "Sin registro"
                        )


                    dias_texto = (
                        str(dias)
                        if dias is not None
                        else "-"
                    )


                    with columna:

                        st.markdown(
                            f"""
                            <div class="equipment-card">

                                <div class="equipment-code">
                                    {codigo}
                                </div>

                                <div class="equipment-type">
                                    {equipo["tipo"]}
                                </div>

                                <div>
                                    <span class="
                                        status
                                        {clase}
                                    ">
                                        {icono} {estado}
                                    </span>
                                </div>

                                <div class="equipment-info">

                                    📅 Último uso:
                                    <b>{ultimo_uso_texto}</b>

                                    <br>

                                    ⏱️ Días sin uso:
                                    <b>{dias_texto}</b>

                                    <br>

                                    📍 Ubicación:
                                    <b>
                                        {equipo["ubicacion"]
                                        if equipo["ubicacion"]
                                        else "No registrada"}
                                    </b>

                                </div>

                            </div>
                            """,
                            unsafe_allow_html=True
                        )

# REGISTRAR USO
elif pagina == "Registrar uso":

    st.markdown(
        '<div class="section-title">📝 Registrar uso</div>',
        unsafe_allow_html=True
    )

    st.info(
        "El registro digital complementa el registro físico "
        "del cuadernillo."
    )


    if equipos.empty:

        st.warning(
            "Primero debes registrar los equipos."
        )

    else:

        lista_equipos = equipos[
            "codigo"
        ].tolist()


        with st.form("formulario_uso"):

            col1, col2 = st.columns(2)


            with col1:

                codigo = st.selectbox(
                    "Equipo",
                    lista_equipos
                )


            with col2:

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
                "Guardar registro"
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

# ADMINISTRACIÓN
elif pagina == "Administración":

    st.markdown(
        '<div class="section-title">⚙️ Administración</div>',
        unsafe_allow_html=True
    )

    st.warning(
        "Sección destinada a la administración de información "
        "de los equipos."
    )


    with st.form("formulario_equipo"):

        st.subheader(
            "Agregar / actualizar equipo"
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
                value=None
            )


            proximo_mantenimiento = st.date_input(
                "Próximo mantenimiento",
                value=None
            )


        observacion = st.text_area(
            "Observación"
        )


        guardar_equipo = st.form_submit_button(
            "Guardar equipo"
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


# PIE DE PÁGINA
st.markdown(
    """
    <div class="footer">
        Dashboard de monitoreo de equipos 
    </div>
    """,
    unsafe_allow_html=True
)