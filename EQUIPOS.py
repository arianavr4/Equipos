import streamlit as st
import pandas as pd
import sqlite3
import re
from datetime import date, datetime
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(page_title="AMEL", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "equipment_dashboard.db"
EXCEL_NAME = BASE_DIR / "Listado equipos.xlsx"
CERTIFICADOS_DIR = BASE_DIR / "certificados"
DIAS_LAVADO_HPLC = 7

st.markdown("""
<style>
.stApp{background-color:#F4F7FA}
[data-testid="stSidebar"]{background-color:#003B5C}
[data-testid="stSidebar"] *{color:white!important}
h1,h2,h3{color:#003B5C!important}
[data-testid="stMetric"]{background-color:white;border:1px solid #DCE5EC;border-radius:12px;padding:15px;box-shadow:0 2px 8px rgba(0,59,92,.07)}
[data-testid="stMetricLabel"]{color:#64748B!important}
[data-testid="stMetricValue"]{color:#003B5C!important}
.stButton>button{background-color:#0072CE;color:white;border:none;border-radius:7px;font-weight:600}
.stButton>button:hover{background-color:#005B9F;color:white}
</style>
""", unsafe_allow_html=True)

# ============================================================
# BASE DE DATOS
# ============================================================
def conectar_db(): return sqlite3.connect(DB_NAME)

def crear_tablas():
    conn=conectar_db(); c=conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS equipos(
        codigo TEXT PRIMARY KEY,tipo TEXT NOT NULL,estado TEXT NOT NULL,
        ubicacion TEXT,ultimo_mantenimiento TEXT,proximo_mantenimiento TEXT,observacion TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS usos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,codigo_equipo TEXT NOT NULL,
        fecha TEXT NOT NULL,tipo_registro TEXT NOT NULL,observacion TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS mantenimientos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,codigo_equipo TEXT NOT NULL,
        tipo_mantenimiento TEXT NOT NULL,proveedor TEXT,fecha TEXT NOT NULL,
        observacion TEXT,certificado_nombre TEXT,certificado_ruta TEXT)""")
    c.execute("PRAGMA table_info(equipos)")
    cols={r[1] for r in c.fetchall()}
    for name in ["fecha_uso","fecha_mantenimiento_preventivo","fecha_lavado","fecha_ocurrencia","personal_uso","personal_lavado"]:
        if name not in cols: c.execute(f"ALTER TABLE equipos ADD COLUMN {name} TEXT")
    c.execute("UPDATE equipos SET estado='Inoperativo' WHERE estado='De baja'")
    c.execute("""INSERT INTO usos(codigo_equipo,fecha,tipo_registro,observacion)
        SELECT e.codigo,e.fecha_uso,'Uso','Registro automático desde Administración'
        FROM equipos e WHERE e.fecha_uso IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM usos u WHERE u.codigo_equipo=e.codigo AND u.fecha=e.fecha_uso AND u.tipo_registro='Uso')""")
    conn.commit(); conn.close()
crear_tablas()

# ============================================================
# EXCEL
# ============================================================
def obtener_fecha_modificacion_excel(): return EXCEL_NAME.stat().st_mtime if EXCEL_NAME.exists() else None

@st.cache_data
def cargar_listado_excel(fecha_modificacion):
    if not EXCEL_NAME.exists(): return None
    try: df=pd.read_excel(EXCEL_NAME,sheet_name="Table 1")
    except Exception as e:
        st.error(f"No se pudo leer 'Listado equipos.xlsx'. Error: {e}"); return None
    if "CÓDIGO" in df.columns:
        df=df[df["CÓDIGO"].notna()].copy(); df["CÓDIGO"]=df["CÓDIGO"].astype(str).str.strip()
    return df.dropna(how="all")
listado_excel=cargar_listado_excel(obtener_fecha_modificacion_excel())

# ============================================================
# CONSULTAS
# ============================================================
def obtener_equipos():
    conn=conectar_db(); df=pd.read_sql_query("SELECT * FROM equipos",conn); conn.close(); return df

def obtener_usos():
    conn=conectar_db(); df=pd.read_sql_query("SELECT * FROM usos",conn); conn.close(); return df

def obtener_mantenimientos():
    conn=conectar_db(); df=pd.read_sql_query("SELECT * FROM mantenimientos",conn); conn.close(); return df

# ============================================================
# EQUIPOS / USOS
# ============================================================
def guardar_equipo(codigo,tipo,estado,fecha_uso,fecha_lavado,fecha_ocurrencia,personal_uso,personal_lavado,observacion):
    conn=conectar_db(); c=conn.cursor()
    c.execute("""INSERT INTO equipos(codigo,tipo,estado,fecha_uso,fecha_lavado,fecha_ocurrencia,personal_uso,personal_lavado,observacion)
        VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(codigo) DO UPDATE SET
        tipo=excluded.tipo,estado=excluded.estado,
        fecha_uso=COALESCE(excluded.fecha_uso,equipos.fecha_uso),
        fecha_lavado=COALESCE(excluded.fecha_lavado,equipos.fecha_lavado),
        fecha_ocurrencia=COALESCE(excluded.fecha_ocurrencia,equipos.fecha_ocurrencia),
        personal_uso=COALESCE(excluded.personal_uso,equipos.personal_uso),
        personal_lavado=COALESCE(excluded.personal_lavado,equipos.personal_lavado),
        observacion=excluded.observacion""",
        (codigo,tipo,estado,fecha_uso,fecha_lavado,fecha_ocurrencia,personal_uso,personal_lavado,observacion))
    if fecha_uso:
        c.execute("SELECT 1 FROM usos WHERE codigo_equipo=? AND fecha=? AND tipo_registro='Uso'",(codigo,fecha_uso))
        if c.fetchone() is None: c.execute("INSERT INTO usos(codigo_equipo,fecha,tipo_registro,observacion) VALUES(?,?,'Uso',?)",(codigo,fecha_uso,observacion))
    conn.commit(); conn.close()

def calcular_ultimo_uso(codigo,usos):
    if usos.empty:return None
    x=usos[(usos.codigo_equipo==codigo)&(usos.tipo_registro=="Uso")]
    if x.empty:return None
    f=pd.to_datetime(x.fecha,errors="coerce").dropna()
    return f.max().date() if not f.empty else None

def calcular_dias_sin_uso(codigo,usos):
    u=calcular_ultimo_uso(codigo,usos); return (date.today()-u).days if u else None

def formatear_fecha(fecha):
    if fecha is None:return "Sin registro"
    try:
        if pd.isna(fecha):return "Sin registro"
    except: pass
    try:return pd.to_datetime(fecha).strftime("%d/%m/%Y")
    except:return str(fecha)

# ============================================================
# ESTADOS / LAVADO
# ============================================================
ESTADOS=["Operativo","En uso","Inoperativo","Lavado integral","Ocurrencias"]
PERSONAL=["Adriana Meza","Ricardo Briceño","Leonor Cortez","Cristian Condori","Gregorio Reyes","Anghela Rodriguez"]
TIPOS_MANTENIMIENTO=["Preventivo","Correctivo"]
ICONOS={"Operativo":"🟢","En uso":"🔵","Inoperativo":"⚫","Lavado integral":"🧼","Mantenimiento preventivo":"🔧","Ocurrencias":"⚠️"}

def texto_estado(estado,personal):
    return f"En uso por {personal}" if estado=="En uso" and personal is not None and not pd.isna(personal) and str(personal).strip() else estado

def es_hplc(tipo):return "HPLC" in str(tipo).upper()

def estado_lavado_hplc(fecha_lavado):
    if fecha_lavado is None:return "⚪ Sin lavado registrado","gris"
    try:
        if pd.isna(fecha_lavado):return "⚪ Sin lavado registrado","gris"
    except:pass
    f=pd.to_datetime(fecha_lavado,errors="coerce")
    if pd.isna(f):return "⚪ Sin lavado registrado","gris"
    d=(date.today()-f.date()).days
    if d>DIAS_LAVADO_HPLC:return f"🔴 Lavado vencido: ya pasó la semana ({d} días sin lavar).","rojo"
    if d==DIAS_LAVADO_HPLC:return "🟡 Toca lavar hoy: se cumple la semana desde el último lavado.","amarillo"
    return f"🟢 Dentro del plazo: último lavado hace {d} día(s), faltan {DIAS_LAVADO_HPLC-d} para el próximo.","verde"

# ============================================================
# MANTENIMIENTOS - FUENTE OFICIAL DEL ÚLTIMO MANTENIMIENTO
# ============================================================
def obtener_fila_equipo(codigo,equipos):
    if equipos.empty:return None
    x=equipos[equipos.codigo.astype(str).str.strip()==str(codigo).strip()]
    return None if x.empty else x.iloc[0]

def obtener_ultimo_mantenimiento(codigo,equipos=None,mantenimientos=None):
    if mantenimientos is None:mantenimientos=obtener_mantenimientos()
    fechas=[]
    if not mantenimientos.empty:
        x=mantenimientos[mantenimientos.codigo_equipo.astype(str).str.strip()==str(codigo).strip()]
        if not x.empty:
            fechas.extend(pd.to_datetime(x.fecha,errors="coerce").dropna().tolist())
    # Compatibilidad con datos antiguos, pero los nuevos registros salen de mantenimientos.
    if equipos is not None and not equipos.empty:
        fila=obtener_fila_equipo(codigo,equipos)
        if fila is not None:
            for campo in ("ultimo_mantenimiento","fecha_mantenimiento_preventivo"):
                if campo in fila.index and fila.get(campo) is not None:
                    try:
                        if pd.isna(fila.get(campo)):continue
                    except:pass
                    f=pd.to_datetime(fila.get(campo),errors="coerce")
                    if not pd.isna(f):fechas.append(f)
    return max(fechas).date() if fechas else None

def guardar_mantenimiento(codigo,tipo,proveedor,fecha,observacion,archivo_pdf):
    nombre=ruta=None
    if archivo_pdf is not None:
        CERTIFICADOS_DIR.mkdir(exist_ok=True)
        nombre_archivo=re.sub(r"[^A-Za-z0-9._-]","_",f"{codigo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo_pdf.name}")
        ruta_completa=CERTIFICADOS_DIR/nombre_archivo
        with open(ruta_completa,"wb") as f:f.write(archivo_pdf.getbuffer())
        nombre=archivo_pdf.name; ruta=f"certificados/{nombre_archivo}"
    conn=conectar_db(); c=conn.cursor()
    c.execute("""INSERT INTO mantenimientos(codigo_equipo,tipo_mantenimiento,proveedor,fecha,observacion,certificado_nombre,certificado_ruta)
        VALUES(?,?,?,?,?,?,?)""",(codigo,tipo,proveedor,fecha,observacion,nombre,ruta))
    conn.commit(); conn.close()

def mostrar_tabla_mantenimientos(df,sufijo):
    if df.empty:st.info("No hay mantenimientos registrados.");return
    x=df.copy(); x["_orden"]=pd.to_datetime(x.fecha,errors="coerce");x=x.sort_values("_orden",ascending=False)
    tabla=pd.DataFrame({"ID":x.id,"Equipo":x.codigo_equipo,"Tipo":x.tipo_mantenimiento,"Proveedor":x.proveedor,"Fecha":[formatear_fecha(v) for v in x.fecha],"Observación":x.observacion,"Certificado":[v if isinstance(v,str) and v else "Sin certificado" for v in x.certificado_nombre]})
    st.dataframe(tabla,use_container_width=True,hide_index=True)
    con=x[x.certificado_ruta.notna()&(x.certificado_ruta!="")]
    if not con.empty:
        opciones={f"#{r.id} — {r.codigo_equipo} — {formatear_fecha(r.fecha)} — {r.tipo_mantenimiento}":r for _,r in con.iterrows()}
        elegido=st.selectbox("📎 Descargar certificado",list(opciones),key=f"cert_sel_{sufijo}")
        r=BASE_DIR/opciones[elegido].certificado_ruta
        if r.exists():
            st.download_button("⬇️ Descargar PDF",r.read_bytes(),file_name=opciones[elegido].certificado_nombre,mime="application/pdf",key=f"cert_btn_{sufijo}")
        else:st.warning("No se encontró el archivo del certificado.")

# Datos iniciales
equipos=obtener_equipos(); usos=obtener_usos(); mantenimientos=obtener_mantenimientos()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("# 🧪");st.markdown("## Monitoreo de equipos");st.divider()
    pagina=st.radio("NAVEGACIÓN",["Dashboard","Equipos","Administración","Mantenimientos","Listado de equipos"])

st.title("AMEL");st.caption("Abbott Monitoring & Equipment Log");st.divider()

# ============================================================
# DASHBOARD
# ============================================================
if pagina=="Dashboard":
    st.subheader("📊 Resumen general")
    total=len(listado_excel) if listado_excel is not None else len(equipos)
    operativos=len(equipos[equipos.estado=="Operativo"]);en_uso=len(equipos[equipos.estado=="En uso"]);inoperativos=len(equipos[equipos.estado=="Inoperativo"])
    sin_uso=sum(1 for c in equipos.codigo if (calcular_dias_sin_uso(c,usos) or -1)>14)
    a,b,c,d,e=st.columns(5)
    a.metric("TOTAL EQUIPOS",total);b.metric("OPERATIVOS",operativos);c.metric("EN USO",en_uso);d.metric("SIN USO",sin_uso);e.metric("INOPERATIVOS",inoperativos)
    st.divider();st.subheader("📈 Porcentajes")
    if total:
        a,b,c=st.columns(3)
        for col,label,val in [(a,"% EN USO",en_uso),(b,"% OPERATIVOS",operativos),(c,"% INOPERATIVOS",inoperativos)]:
            pct=val/total*100;col.metric(label,f"{pct:.1f}%");col.progress(min(pct/100,1))
    st.divider();st.subheader("⚠️ Alertas")
    alertas=[(c,calcular_dias_sin_uso(c,usos)) for c in equipos.codigo if calcular_dias_sin_uso(c,usos) is not None and calcular_dias_sin_uso(c,usos)>14]
    if alertas:
        for c,d in alertas:st.error(f"🔴 {c} — {d} días sin registrar uso.")
    else:st.success("✓ No hay equipos con más de 14 días sin registrar uso.")
    st.divider();st.subheader("🧼 Lavado semanal de HPLC")
    hay=False
    for _,eq in equipos.iterrows():
        if not es_hplc(eq.tipo) or eq.estado=="Inoperativo":continue
        hay=True;msg,nivel=estado_lavado_hplc(eq.get("fecha_lavado"));texto=f"**{eq.codigo}** — {msg}"
        if nivel=="rojo":st.error(texto)
        elif nivel in ("amarillo","gris"):st.warning(texto)
        else:st.success(texto)
    if not hay:st.info("No hay equipos HPLC registrados.")

# ============================================================
# EQUIPOS
# ============================================================
elif pagina=="Equipos":
    st.subheader("🖥️ Equipos registrados")
    if equipos.empty:st.info("No hay equipos registrados en el sistema todavía.")
    else:
        a,b,c=st.columns(3)
        estados=["Todos"]+sorted(equipos.estado.dropna().unique().tolist());filtro_estado=a.selectbox("Estado",estados)
        tipos=["Todos"]+sorted(equipos.tipo.dropna().unique().tolist());filtro_tipo=b.selectbox("Tipo de equipo",tipos)
        busqueda=c.text_input("Buscar equipo",placeholder="Ej. OPT-001")
        filtrados=equipos.copy()
        if filtro_estado!="Todos":filtrados=filtrados[filtrados.estado==filtro_estado]
        if filtro_tipo!="Todos":filtrados=filtrados[filtrados.tipo==filtro_tipo]
        if busqueda:filtrados=filtrados[filtrados.codigo.astype(str).str.contains(busqueda,case=False,na=False)]
        st.divider()
        if filtrados.empty:st.warning("No se encontraron equipos.")
        for inicio in range(0,len(filtrados),3):
            cols=st.columns(3)
            for col,(_,eq) in zip(cols,filtrados.iloc[inicio:inicio+3].iterrows()):
                codigo=eq.codigo;ultimo_uso=calcular_ultimo_uso(codigo,usos);dias=calcular_dias_sin_uso(codigo,usos)
                ultimo_mant=obtener_ultimo_mantenimiento(codigo,equipos,mantenimientos)
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {ICONOS.get(eq.estado,'⚪')} {codigo}");st.caption(eq.tipo)
                        st.write(f"**Estado:** {texto_estado(eq.estado,eq.get('personal_uso'))}")
                        st.write(f"**Último uso:** {formatear_fecha(ultimo_uso)}")
                        st.write(f"**Días sin uso:** {dias if dias is not None else 'Sin registro'}")
                        st.write(f"**Último mantenimiento:** {formatear_fecha(ultimo_mant)}")
                        fl=eq.get("fecha_lavado");pl=eq.get("personal_lavado")
                        texto= formatear_fecha(fl)
                        if texto!="Sin registro" and pl is not None and not pd.isna(pl) and str(pl).strip():texto=f"{texto} por {pl}"
                        st.write(f"**Último lavado:** {texto}")
                        if es_hplc(eq.tipo) and eq.estado!="Inoperativo":
                            msg,nivel=estado_lavado_hplc(fl)
                            if nivel=="rojo":st.error(msg)
                            elif nivel in ("amarillo","gris"):st.warning(msg)
                            else:st.success(msg)

# ============================================================
# ADMINISTRACIÓN - SIN MANTENIMIENTO
# ============================================================
elif pagina=="Administración":
    st.subheader("⚙️ Administración")
    st.info("Registra o actualiza información operativa. Los mantenimientos se registran únicamente en la sección Mantenimientos.")
    st.markdown("### Datos del equipo");a,b=st.columns(2)
    codigo=a.text_input("Código del equipo",placeholder="Ej. OPT-001");tipo=b.text_input("Tipo",value="HPLC")
    st.markdown("### Estado del equipo");estado=st.selectbox("Selecciona el estado",ESTADOS)
    fecha_uso=fecha_lavado=fecha_ocurrencia=None;personal_uso=personal_lavado=None
    if estado=="En uso":fecha_uso=st.date_input("📅 Fecha de uso",value=date.today(),format="DD/MM/YYYY",key="fecha_uso_admin")
    elif estado=="Lavado integral":fecha_lavado=st.date_input("📅 Fecha de lavado",value=date.today(),format="DD/MM/YYYY",key="fecha_lavado_admin")
    elif estado=="Ocurrencias":fecha_ocurrencia=st.date_input("📅 Fecha de ocurrencia",value=date.today(),format="DD/MM/YYYY",key="fecha_ocurrencia_admin")
    if estado=="En uso":personal_uso=st.selectbox("👤 Personal que usa el equipo",PERSONAL,index=None,placeholder="Selecciona al trabajador",key="personal_uso_admin")
    elif estado=="Lavado integral":personal_lavado=st.selectbox("👤 Personal que realizó el lavado",PERSONAL,index=None,placeholder="Selecciona al trabajador",key="personal_lavado_admin")
    st.markdown("### Observaciones");observacion=st.text_area("Observación",placeholder="Agregar información adicional...")
    if st.button("💾 Guardar información",type="primary"):
        if not codigo.strip():st.error("Debes ingresar el código del equipo.")
        elif estado=="En uso" and not personal_uso:st.error("Debes seleccionar quién está usando el equipo.")
        elif estado=="Lavado integral" and not personal_lavado:st.error("Debes seleccionar quién realizó el lavado.")
        else:
            guardar_equipo(codigo.strip(),tipo.strip(),estado,str(fecha_uso) if fecha_uso else None,str(fecha_lavado) if fecha_lavado else None,str(fecha_ocurrencia) if fecha_ocurrencia else None,personal_uso,personal_lavado,observacion)
            st.success(f"✓ Información de {codigo} guardada correctamente.");st.rerun()

# ============================================================
# MANTENIMIENTOS
# ============================================================
elif pagina=="Mantenimientos":
    st.subheader("🔧 Mantenimientos")
    st.info("Registra aquí los mantenimientos. La fecha más reciente se mostrará automáticamente como 'Último mantenimiento' en Equipos y Listado de equipos.")
    if "mant_form_id" not in st.session_state:st.session_state.mant_form_id=0
    fid=st.session_state.mant_form_id
    mensaje=st.session_state.pop("mant_mensaje_ok",None)
    if mensaje:st.success(mensaje)
    st.markdown("### ➕ Registrar mantenimiento")
    codigos=set(equipos.codigo.astype(str).tolist())
    if listado_excel is not None and "CÓDIGO" in listado_excel.columns:codigos|=set(listado_excel["CÓDIGO"].astype(str).tolist())
    codigos=sorted(codigos)
    if not codigos:st.info("No hay equipos disponibles todavía.")
    else:
        a,b=st.columns(2)
        codigo_mant=a.selectbox("Equipo",codigos,key=f"mant_codigo_{fid}")
        tipo_mant=a.selectbox("Tipo de mantenimiento",TIPOS_MANTENIMIENTO,key=f"mant_tipo_{fid}")
        proveedor_mant=b.text_input("Proveedor",placeholder="Ej. Nombre de la empresa",key=f"mant_proveedor_{fid}")
        fecha_mant=b.date_input("📅 Fecha del mantenimiento",value=date.today(),format="DD/MM/YYYY",key=f"mant_fecha_{fid}")
        obs_mant=st.text_area("Observaciones",placeholder="Detalle del mantenimiento realizado...",key=f"mant_obs_{fid}")
        certificado=st.file_uploader("📎 Informe / certificado técnico (PDF)",type=["pdf"],key=f"mant_certificado_{fid}")
        if st.button("💾 Guardar mantenimiento",type="primary",key="btn_guardar_mant"):
            if not proveedor_mant.strip():st.error("Debes ingresar el proveedor.")
            else:
                guardar_mantenimiento(codigo_mant,tipo_mant,proveedor_mant.strip(),str(fecha_mant),obs_mant,certificado)
                st.session_state.mant_mensaje_ok=f"✓ Mantenimiento {tipo_mant.lower()} de {codigo_mant} guardado correctamente. La fecha se actualizará en Equipos."
                st.session_state.mant_form_id+=1
                st.rerun()
    st.divider();st.markdown("### 📋 Historial de mantenimientos")
    buscar=st.text_input("Buscar por equipo",placeholder="Ej. OPT-002",key="mant_buscar")
    historial=obtener_mantenimientos()
    if buscar:historial=historial[historial.codigo_equipo.astype(str).str.contains(buscar,case=False,na=False)]
    t1,t2,t3=st.tabs(["Todos","🛠️ Preventivos","🔧 Correctivos"])
    with t1:mostrar_tabla_mantenimientos(historial,"todos")
    with t2:mostrar_tabla_mantenimientos(historial[historial.tipo_mantenimiento=="Preventivo"],"prev")
    with t3:mostrar_tabla_mantenimientos(historial[historial.tipo_mantenimiento=="Correctivo"],"corr")

# ============================================================
# LISTADO DE EQUIPOS
# ============================================================
elif pagina=="Listado de equipos":
    st.subheader("📋 Listado de equipos")
    if listado_excel is None:st.error("No se encontró 'Listado equipos.xlsx'.");st.info("Coloca el archivo en la misma carpeta de EQUIPOS.py.");st.stop()
    listado=listado_excel.copy();listado["CÓDIGO"]=listado["CÓDIGO"].astype(str).str.strip()
    if not equipos.empty:
        ed=equipos[["codigo","estado","personal_uso"]].copy();ed["estado"]=[texto_estado(a,b) for a,b in zip(ed.estado,ed.personal_uso)];ed=ed[["codigo","estado"]].rename(columns={"codigo":"CÓDIGO","estado":"ESTADO ACTUAL"});listado=listado.merge(ed,on="CÓDIGO",how="left");listado["ESTADO ACTUAL"]=listado["ESTADO ACTUAL"].fillna("No registrado")
    else:listado["ESTADO ACTUAL"]="No registrado"
    listado["ÚLTIMO USO"]=[formatear_fecha(calcular_ultimo_uso(c,usos)) for c in listado["CÓDIGO"]]
    listado["DÍAS SIN USO"]=[calcular_dias_sin_uso(c,usos) if calcular_dias_sin_uso(c,usos) is not None else "-" for c in listado["CÓDIGO"]]
    listado["ÚLTIMO MANTENIMIENTO"]=[formatear_fecha(obtener_ultimo_mantenimiento(c,equipos,mantenimientos)) for c in listado["CÓDIGO"]]
    lav=[]
    for c in listado["CÓDIGO"]:
        f=obtener_fila_equipo(c,equipos)
        if f is None:lav.append("Sin registro");continue
        t=formatear_fecha(f.get("fecha_lavado"));p=f.get("personal_lavado")
        lav.append(f"{t} por {p}" if t!="Sin registro" and p is not None and not pd.isna(p) and str(p).strip() else t)
    listado["ÚLTIMO LAVADO"]=lav
    cols_orig=[c for c in listado_excel.columns if c in listado.columns];cols_sys=["ESTADO ACTUAL","ÚLTIMO USO","DÍAS SIN USO","ÚLTIMO MANTENIMIENTO","ÚLTIMO LAVADO"];listado=listado[cols_orig+[c for c in cols_sys if c in listado.columns]]
    st.markdown("### 🔎 Buscar y filtrar");a,b,c=st.columns(3);bus=a.text_input("Buscar por código",placeholder="Ej. OPT-023")
    marcas=["Todas"]+sorted(listado.MARCA.dropna().astype(str).unique().tolist()) if "MARCA" in listado.columns else ["Todas"];fm=b.selectbox("Marca",marcas)
    desc=["Todos"]+sorted(listado.DESCRIPCIÓN.dropna().astype(str).unique().tolist()) if "DESCRIPCIÓN" in listado.columns else ["Todos"];fd=c.selectbox("Descripción",desc)
    lf=listado.copy()
    if bus:lf=lf[lf.CÓDIGO.astype(str).str.contains(bus,case=False,na=False)]
    if fm!="Todas" and "MARCA" in lf.columns:lf=lf[lf.MARCA.astype(str)==fm]
    if fd!="Todos" and "DESCRIPCIÓN" in lf.columns:lf=lf[lf.DESCRIPCIÓN.astype(str)==fd]
    st.markdown(f"**{len(lf)} equipos encontrados**");st.dataframe(lf,use_container_width=True,hide_index=True,height=550);st.divider();st.markdown("### 🔍 Ficha del equipo")
    if len(lf)>0:
        sel=st.selectbox("Selecciona un equipo",lf.CÓDIGO.astype(str).tolist());eq=lf[lf.CÓDIGO.astype(str)==sel].iloc[0];st.markdown(f"## 🧪 {sel}")
        a,b,c=st.columns(3)
        campos=[("Descripción","DESCRIPCIÓN"),("Marca","MARCA")];
        for titulo,col in campos:
            if col in eq.index:a.write(f"**{titulo}**");a.write(eq[col])
        for titulo,col in [("Modelo / módulos","MODELO/MÓDULOS"),("Serie / serie módulos / lote","SERIE/SERIE MÓDULOS/LOTE")]:
            if col in eq.index:b.write(f"**{titulo}**");b.write(eq[col])
        for titulo,col in [("Equipo móvil","EQUIPO MÓVIL"),("Categorización","CATEGORIZACIÓN DE EQUIPO")]:
            if col in eq.index:c.write(f"**{titulo}**");c.write(eq[col])
        st.divider();st.markdown("### 📊 Información del sistema");a,b,c,d=st.columns(4);a.metric("Estado actual",eq.get("ESTADO ACTUAL","No registrado"));b.metric("Último uso",eq.get("ÚLTIMO USO","Sin registro"));b2=eq.get("DÍAS SIN USO","-");c.metric("Días sin uso",b2);d.metric("Último mantenimiento",eq.get("ÚLTIMO MANTENIMIENTO","Sin registro"));st.write(f"**Último lavado:** {eq.get('ÚLTIMO LAVADO','Sin registro')}")
        st.divider();st.markdown("### 📋 Información completa del equipo");det=[]
        for col in cols_orig:
            v=eq[col]
            if pd.isna(v):v="Sin registro"
            elif isinstance(v,pd.Timestamp):v=v.strftime("%d/%m/%Y")
            det.append({"Campo":col,"Información":str(v)})
        st.dataframe(pd.DataFrame(det),use_container_width=True,hide_index=True,height=500)
    else:st.warning("No hay equipos que coincidan con los filtros seleccionados.")
