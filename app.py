"""
Asistente Legal Online
Aplicación web para estudios jurídicos: gestión de expedientes,
control de plazos procesales y redacción rápida de reportes de estado.
Stack: Python 3.10+, Streamlit
"""

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import io

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------

st.set_page_config(
    page_title="Asistente Legal Online",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
    .main { background-color: #f7f8fa; }
    .titulo-app {
        font-size: 2rem;
        font-weight: 700;
        color: #1a2b4c;
        margin-bottom: 0.2rem;
    }
    .subtitulo-app {
        color: #5a6472;
        margin-bottom: 1.5rem;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.7rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
    }
    .badge-rojo { background-color: #e0433c; }
    .badge-amarillo { background-color: #e0a800; }
    .badge-verde { background-color: #2ca86a; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO DE SESIÓN (persistencia mientras dura la sesión del navegador)
# ------------------------------------------------------------------

if "expedientes" not in st.session_state:
    st.session_state.expedientes = []  # lista de dicts

if "plazos" not in st.session_state:
    st.session_state.plazos = []  # lista de dicts

if "reportes" not in st.session_state:
    st.session_state.reportes = []  # lista de dicts


# ------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------------

def sumar_dias_habiles(fecha_inicio: date, dias: int) -> date:
    """Suma días hábiles (lunes a viernes) a una fecha, sin contar feriados."""
    fecha = fecha_inicio
    contados = 0
    while contados < dias:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:  # 0=lunes ... 4=viernes
            contados += 1
    return fecha


def calcular_estado_alerta(fecha_vencimiento: date) -> tuple:
    """Devuelve (texto, clase_css) según la proximidad del vencimiento."""
    hoy = date.today()
    dias_restantes = (fecha_vencimiento - hoy).days
    try:
        if dias_restantes < 0:
            return f"Vencido hace {abs(dias_restantes)} día(s)", "badge-rojo"
        elif dias_restantes <= 3:
            return f"Vence en {dias_restantes} día(s)", "badge-rojo"
        elif dias_restantes <= 7:
            return f"Vence en {dias_restantes} día(s)", "badge-amarillo"
        else:
            return f"Vence en {dias_restantes} día(s)", "badge-verde"
    except Exception:
        return "Sin datos", "badge-amarillo"


def generar_borrador_expediente(expediente: dict) -> str:
    """Genera el texto de un borrador de escrito básico a partir de un expediente."""
    try:
        texto = f"""BORRADOR DE ESCRITO

Carátula: {expediente.get('caratula', '-')}
Juzgado: {expediente.get('juzgado', '-')}
Cliente: {expediente.get('cliente', '-')}
N° de Expediente: {expediente.get('numero', '-')}
Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}

--------------------------------------------------
PRESENTA ESCRITO - DEJA CONSTANCIA
--------------------------------------------------

Señor Juez:

{expediente.get('cliente', '[CLIENTE]')}, en autos caratulados "{expediente.get('caratula', '[CARÁTULA]')}",
tramitados por ante el {expediente.get('juzgado', '[JUZGADO]')}, a V.S. respetuosamente digo:

[Desarrollar el contenido del escrito aquí]

Por lo expuesto, a V.S. solicito:

1) Se tenga por presentado en tiempo y forma.
2) [Petitorio específico]

Proveer de conformidad,
SERÁ JUSTICIA.
"""
        return texto
    except Exception as e:
        return f"Error al generar el borrador: {e}"


def generar_reporte_texto(reporte: dict) -> str:
    """Genera el texto formal de un reporte de estado para el cliente."""
    try:
        texto = f"""REPORTE DE ESTADO DE EXPEDIENTE

Fecha: {datetime.now().strftime('%d/%m/%Y')}
Cliente: {reporte.get('cliente', '-')}
Expediente / Carátula: {reporte.get('expediente', '-')}

Estimado/a {reporte.get('cliente', '-')},

Le informamos el estado actual de su expediente:

{reporte.get('detalle', '')}

Quedamos a su disposición ante cualquier consulta.

Saludos cordiales.
"""
        return texto
    except Exception as e:
        return f"Error al generar el reporte: {e}"


# ------------------------------------------------------------------
# ENCABEZADO Y NAVEGACIÓN
# ------------------------------------------------------------------

st.markdown('<div class="titulo-app">⚖️ Asistente Legal Online</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-app">Gestión de expedientes, plazos procesales y reportes para clientes</div>', unsafe_allow_html=True)

seccion = st.sidebar.radio(
    "Navegación",
    ["📁 Expedientes", "⏰ Plazos procesales", "📝 Reportes de estado"],
)

st.sidebar.markdown("---")
st.sidebar.caption(f"Expedientes cargados: {len(st.session_state.expedientes)}")
st.sidebar.caption(f"Plazos activos: {len(st.session_state.plazos)}")
st.sidebar.caption(f"Reportes generados: {len(st.session_state.reportes)}")


# ------------------------------------------------------------------
# SECCIÓN 1: EXPEDIENTES
# ------------------------------------------------------------------

if seccion == "📁 Expedientes":
    st.markdown("### Cargar nuevo expediente")

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("form_expediente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cliente = st.text_input("Cliente")
                numero = st.text_input("N° de Expediente (opcional)")
            with col2:
                caratula = st.text_input("Carátula")
                juzgado = st.text_input("Juzgado")

            enviado = st.form_submit_button("Guardar expediente")

            if enviado:
                try:
                    if not cliente or not caratula or not juzgado:
                        st.error("Por favor completá Cliente, Carátula y Juzgado.")
                    else:
                        nuevo = {
                            "cliente": cliente,
                            "caratula": caratula,
                            "juzgado": juzgado,
                            "numero": numero,
                            "fecha_carga": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }
                        st.session_state.expedientes.append(nuevo)
                        st.success("Expediente guardado correctamente.")
                except Exception as e:
                    st.error(f"Ocurrió un error al guardar el expediente: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Expedientes cargados")

    if not st.session_state.expedientes:
        st.info("Todavía no cargaste ningún expediente.")
    else:
        for i, exp in enumerate(st.session_state.expedientes):
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{exp['caratula']}**")
                    st.caption(f"Cliente: {exp['cliente']} · Juzgado: {exp['juzgado']} · Nº: {exp['numero'] or '-'}")
                    st.caption(f"Cargado el {exp['fecha_carga']}")
                with col2:
                    try:
                        borrador = generar_borrador_expediente(exp)
                        st.download_button(
                            "⬇️ Borrador",
                            data=borrador,
                            file_name=f"borrador_{exp['cliente'].replace(' ', '_')}.txt",
                            mime="text/plain",
                            key=f"descarga_exp_{i}",
                        )
                    except Exception as e:
                        st.error(f"No se pudo generar el borrador: {e}")
                st.markdown('</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------
# SECCIÓN 2: PLAZOS PROCESALES
# ------------------------------------------------------------------

elif seccion == "⏰ Plazos procesales":
    st.markdown("### Cargar nuevo plazo")

    nombres_expedientes = [exp["caratula"] for exp in st.session_state.expedientes]

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("form_plazo", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                if nombres_expedientes:
                    expediente_sel = st.selectbox("Expediente", nombres_expedientes)
                else:
                    expediente_sel = st.text_input("Expediente (carátula)")
            with col2:
                fecha_notificacion = st.date_input("Fecha de notificación", value=date.today())
            with col3:
                dias_plazo = st.number_input("Días de plazo (hábiles)", min_value=1, max_value=180, value=5)

            descripcion = st.text_input("Descripción del plazo (opcional)", placeholder="Ej: Contestar demanda")

            enviado = st.form_submit_button("Calcular y guardar plazo")

            if enviado:
                try:
                    vencimiento = sumar_dias_habiles(fecha_notificacion, int(dias_plazo))
                    nuevo_plazo = {
                        "expediente": expediente_sel,
                        "descripcion": descripcion or "-",
                        "fecha_notificacion": fecha_notificacion,
                        "dias_plazo": dias_plazo,
                        "vencimiento": vencimiento,
                    }
                    st.session_state.plazos.append(nuevo_plazo)
                    st.success(f"Plazo guardado. Vencimiento calculado: {vencimiento.strftime('%d/%m/%Y')}")
                except Exception as e:
                    st.error(f"Ocurrió un error al calcular el plazo: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Plazos activos")

    if not st.session_state.plazos:
        st.info("Todavía no cargaste ningún plazo.")
    else:
        plazos_ordenados = sorted(st.session_state.plazos, key=lambda p: p["vencimiento"])
        for i, plazo in enumerate(plazos_ordenados):
            texto_alerta, clase = calcular_estado_alerta(plazo["vencimiento"])
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{plazo['expediente']}** — {plazo['descripcion']}")
                    st.caption(
                        f"Notificado el {plazo['fecha_notificacion'].strftime('%d/%m/%Y')} · "
                        f"Plazo: {plazo['dias_plazo']} día(s) hábiles · "
                        f"Vence el {plazo['vencimiento'].strftime('%d/%m/%Y')}"
                    )
                with col2:
                    st.markdown(f'<span class="badge {clase}">{texto_alerta}</span>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------
# SECCIÓN 3: REPORTES DE ESTADO
# ------------------------------------------------------------------

elif seccion == "📝 Reportes de estado":
    st.markdown("### Redactar reporte de estado")

    nombres_expedientes = [exp["caratula"] for exp in st.session_state.expedientes]

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        with st.form("form_reporte", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cliente_reporte = st.text_input("Cliente")
            with col2:
                if nombres_expedientes:
                    expediente_reporte = st.selectbox("Expediente relacionado", nombres_expedientes)
                else:
                    expediente_reporte = st.text_input("Expediente relacionado")

            detalle = st.text_area(
                "Detalle del estado actual",
                placeholder="Ej: Se presentó el escrito de contestación de demanda. Próxima audiencia el...",
                height=150,
            )

            enviado = st.form_submit_button("Generar reporte")

            if enviado:
                try:
                    if not cliente_reporte or not detalle:
                        st.error("Completá al menos el Cliente y el Detalle del estado.")
                    else:
                        nuevo_reporte = {
                            "cliente": cliente_reporte,
                            "expediente": expediente_reporte,
                            "detalle": detalle,
                            "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        }
                        st.session_state.reportes.append(nuevo_reporte)
                        st.success("Reporte generado correctamente.")
                except Exception as e:
                    st.error(f"Ocurrió un error al generar el reporte: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Reportes generados")

    if not st.session_state.reportes:
        st.info("Todavía no generaste ningún reporte.")
    else:
        for i, rep in enumerate(reversed(st.session_state.reportes)):
            with st.container():
                st.markdown('<div class="card">', unsafe_allow_html=True)
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{rep['cliente']}** — {rep['expediente']}")
                    st.caption(f"Generado el {rep['fecha']}")
                    with st.expander("Ver contenido"):
                        st.text(generar_reporte_texto(rep))
                with col2:
                    try:
                        texto_reporte = generar_reporte_texto(rep)
                        st.download_button(
                            "⬇️ Descargar",
                            data=texto_reporte,
                            file_name=f"reporte_{rep['cliente'].replace(' ', '_')}.txt",
                            mime="text/plain",
                            key=f"descarga_rep_{i}",
                        )
                    except Exception as e:
                        st.error(f"No se pudo generar el archivo: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
