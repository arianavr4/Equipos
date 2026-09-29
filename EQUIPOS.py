import streamlit as st
import pandas as pd
import sqlite3
from datetime import date


# CONFIGURACIÓN
st.set_page_config(
    page_title="Monitoreo de equipos",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_NAME = "equipment_dashboard.db"


# ESTILO VISUAL
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
    # TABLA DE USOS
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

    # VERIFICAR COLUMNAS EXISTENTES
    cursor.execute(
        "PRAGMA table_info(equipos)"
    )

    columnas_existentes = [
        fila[1]
        for fila in cursor.fetchall()
    ]

    # NUEVAS COLUMNAS
    nuevas_columnas = [
        ("fecha_uso", "TEXT"),
        ("fecha_mantenimiento_preventivo", "TEXT"),
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

# FUNCIONES DE USO
def calcular_ultimo_uso(codigo, usos):

    if usos.empty:
        return None

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

# ESTADOS
ESTADOS = [
    "Operativo",
    "En uso",
    "De baja",
    "Lavado integral",
    "Mantenimiento preventivo",
    "Ocurrencias"
]


def obtener_icono_estado(estado):

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

# FUNCIONES DE FECHAS
def formatear_fecha(fecha):

    if fecha is None:
        return "Sin registro"

    if pd.isna(fecha):
        return "Sin registro"

    texto = str(fecha).strip()

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

# CARGAR DATOS
equipos = obtener_equipos()
usos = obtener_usos()

# SIDEBAR
with st.sidebar:

    st.markdown("# 🧪")

    st.markdown(
        "## Monitoreo de equipos"
    )

    st.caption(
        "Uso y estado"
    )

    st.divider()

    pagina = st.radio(
        "NAVEGACIÓN",
        [
            "Dashboard",
            "Equipos",
            "Administración",
            "Información sobre mantenimentos",
            "Listado de equipos"
        ]
    )

    st.divider()

# TÍTULO GENERAL
st.title(
    "MONITOREO DE EQUIPOS DE LABORATORIO"
)

st.caption(
    "Monitoreo de estado, utilización y alertas de equipos"
)

st.divider()

# DASHBOARD

if pagina == "Dashboard":

    st.subheader(
        "📊 Resumen general"
    )

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


    st.divider()

    # ALERTAS
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
                (codigo, dias)
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

    # TABLA
    st.subheader(
        "🖥️ Estado de equipos"
    )

    if equipos.empty:

        st.info(
            "Todavía no hay equipos registrados."
        )

    else:

        datos = []

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

            ultimo_mantenimiento = (
                equipo.get(
                    "ultimo_mantenimiento"
                )
            )

            datos.append({

                "Código": codigo,

                "Tipo": equipo["tipo"],

                "Estado": (
                    f"{obtener_icono_estado(equipo['estado'])} "
                    f"{equipo['estado']}"
                ),

                "Último uso": (
                    formatear_fecha(
                        ultimo_uso
                    )
                ),

                "Días sin uso": (
                    dias
                    if dias is not None
                    else "-"
                ),

                "Último mantenimiento": (
                    formatear_fecha(
                        ultimo_mantenimiento
                    )
                ),

                "Alerta": (
                    determinar_alerta(
                        dias
                    )
                )
            })


        st.dataframe(
            pd.DataFrame(datos),
            use_container_width=True,
            hide_index=True
        )

# EQUIPOS
elif pagina == "Equipos":

    st.subheader(
        "🖥️ Equipos registrados"
    )


    if equipos.empty:

        st.info(
            "No hay equipos registrados todavía."
        )

    else:
        # FILTROS
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

        # TARJETAS
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

                    ultimo_uso = calcular_ultimo_uso(
                        codigo,
                        usos
                    )

                    dias = calcular_dias_sin_uso(
                        codigo,
                        usos
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

# ADMINISTRACIÓN
elif pagina == "Administración":

    st.subheader(
        "⚙️ Administración"
    )

    st.info(
        "Registra o actualiza la información del equipo."
    )

    # DATOS DEL EQUIPO
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

    # ESTADO
    st.markdown(
        "### Estado del equipo"
    )


    estado = st.selectbox(
        "Selecciona el estado",
        ESTADOS
    )

    # FECHAS DINÁMICAS

    fecha_uso = None

    fecha_mantenimiento_preventivo = None

    fecha_lavado = None

    fecha_ocurrencia = None

    # EN USO
    if estado == "En uso":

        fecha_uso = st.date_input(
            "📅 Fecha de uso",
            value=date.today(),
            format="DD/MM/YYYY",
            key="fecha_uso_admin"
        )

    # LAVADO INTEGRAL
    elif estado == "Lavado integral":

        fecha_lavado = st.date_input(
            "📅 Fecha de lavado",
            value=date.today(),
            format="DD/MM/YYYY",
            key="fecha_lavado_admin"
        )

    # MANTENIMIENTO PREVENTIVO
    elif estado == "Mantenimiento preventivo":

        fecha_mantenimiento_preventivo = st.date_input(
            "📅 Fecha de mantenimiento preventivo",
            value=date.today(),
            format="DD/MM/YYYY",
            key="fecha_mantenimiento_admin"
        )

    # OCURRENCIAS
    elif estado == "Ocurrencias":

        fecha_ocurrencia = st.date_input(
            "📅 Fecha de ocurrencia",
            value=date.today(),
            format="DD/MM/YYYY",
            key="fecha_ocurrencia_admin"
        )

    # OBSERVACIONES
    st.markdown(
        "### Observaciones"
    )


    observacion = st.text_area(
        "Observación",
        placeholder="Agregar información adicional..."
    )


    # GUARDAR
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

# INFORMACIÓN SOBRE MANTENIMENTOS
elif pagina == "Información sobre mantenimentos":

    st.subheader(
        "🔧 Información sobre mantenimentos"
    )

    st.info(
        "Después."
    )

# LISTADO DE EQUIPOS
elif pagina == "Listado de equipos":

    st.subheader(
        "📋 Listado de equipos"
    )

    st.info(
        "Después."
    )

