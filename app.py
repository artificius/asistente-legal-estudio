"""
Asistente Legal Online — v2
Plataforma LegalTech: carga de expedientes en PDF, buscador de términos,
asistente de consultas jurídicas (Q&A) y generador de escritos.
Stack: Python 3.10+, Streamlit, pypdf, anthropic
"""

import streamlit as st
from pypdf import PdfReader
import io
import re
from datetime import datetime

try:
    import anthropic
except ImportError:
    anthropic = None

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------

st.set_page_config(
    page_title="Asistente Legal Online",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODELO_IA = "claude-sonnet-5"          # Modelo Anthropic usado para Q&A y redacción
MAX_CARACTERES_CONTEXTO = 12000        # Límite de texto del expediente enviado a la IA

# ------------------------------------------------------------------
# ESTILO CORPORATIVO (azul marino / gris, sin elementos default de Streamlit)
# ------------------------------------------------------------------

CSS = """
<style>
    #MainMenu, header, footer {visibility: hidden;}
    .stDeployButton {display: none;}

    .main { background-color: #eef1f5; }

    :root {
        --azul-marino: #0b2545;
        --azul-medio: #13315c;
        --gris-texto: #3c4a5c;
        --gris-claro: #f4f6f8;
        --borde: #d6dce3;
    }

    .header-app {
        background-color: var(--azul-marino);
        padding: 1.4rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .header-app h1 {
        color: white;
        font-size: 1.7rem;
        font-weight: 700;
        margin: 0;
    }
    .header-app p {
        color: #c3ccd8;
        margin: 0.2rem 0 0 0;
        font-size: 0.95rem;
    }

    .card {
        background-color: white;
        border: 1px solid var(--borde);
        border-radius: 10px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: var(--gris-claro);
        padding: 0.3rem;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--gris-texto);
        font-weight: 600;
        border-radius: 6px;
        padding: 0.5rem 1rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--azul-marino) !important;
        color: white !important;
    }

    .stButton > button {
        background-color: var(--azul-marino);
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
    }
    .stButton > button:hover {
        background-color: var(--azul-medio);
        color: white;
    }

    .resultado-busqueda {
        background-color: var(--gris-claro);
        border-left: 4px solid var(--azul-marino);
        padding: 0.7rem 1rem;
        margin-bottom: 0.6rem;
        border-radius: 4px;
        font-size: 0.92rem;
        color: var(--gris-texto);
    }
    mark {
        background-color: #ffd873;
        padding: 0 2px;
        border-radius: 2px;
    }

    .chat-usuario, .chat-asistente {
        padding: 0.7rem 1rem;
        border-radius: 8px;
        margin-bottom: 0.6rem;
        font-size: 0.95rem;
    }
    .chat-usuario {
        background-color: var(--azul-marino);
        color: white;
        margin-left: 15%;
    }
    .chat-asistente {
        background-color: var(--gris-claro);
        color: var(--gris-texto);
        border: 1px solid var(--borde);
        margin-right: 15%;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO DE SESIÓN
# ------------------------------------------------------------------

defaults = {
    "texto_expediente": "",
    "nombre_expediente": "",
    "historial_chat": [],       # lista de {"rol": "usuario"/"asistente", "texto": str}
    "ultimo_escrito": "",
}
for clave, valor in defaults.items():
    if clave not in st.session_state:
        st.session_state[clave] = valor


# ------------------------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------------------------

def extraer_texto_pdf(archivo_subido) -> str:
    """Extrae el texto completo de un PDF subido por el usuario."""
    try:
        lector = PdfReader(io.BytesIO(archivo_subido.read()))
        paginas = []
        for i, pagina in enumerate(lector.pages):
            texto_pagina = pagina.extract_text() or ""
            paginas.append(f"\n--- Página {i + 1} ---\n{texto_pagina}")
        return "".join(paginas).strip()
    except Exception as e:
        st.error(f"No se pudo leer el PDF: {e}")
        return ""


def buscar_termino(texto: str, termino: str, contexto: int = 80) -> list:
    """Devuelve una lista de fragmentos donde aparece el término buscado."""
    if not texto or not termino:
        return []
    try:
        resultados = []
        patron = re.compile(re.escape(termino), re.IGNORECASE)
        for coincidencia in patron.finditer(texto):
            inicio = max(0, coincidencia.start() - contexto)
            fin = min(len(texto), coincidencia.end() + contexto)
            fragmento = texto[inicio:fin].replace("\n", " ")
            fragmento_resaltado = patron.sub(lambda m: f"<mark>{m.group(0)}</mark>", fragmento)
            resultados.append(fragmento_resaltado)
        return resultados
    except Exception as e:
        st.error(f"Error al buscar el término: {e}")
        return []


def obtener_cliente_ia():
    """
    Crea el cliente de Anthropic leyendo la API key de forma interna y segura
    desde st.secrets. El usuario final nunca ve ni ingresa esta clave: se
    configura una única vez como "Secret" en Streamlit Community Cloud
    (Settings → Secrets) con el formato ANTHROPIC_API_KEY = "sk-ant-...".
    """
    if anthropic is None:
        st.error("La librería 'anthropic' no está instalada. Agregala a requirements.txt.")
        return None
    try:
        clave = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        st.error(
            "No se encontró la API key en los secretos de la aplicación. "
            "El administrador debe configurar ANTHROPIC_API_KEY en Settings → Secrets."
        )
        return None
    try:
        return anthropic.Anthropic(api_key=clave)
    except Exception as e:
        st.error(f"No se pudo inicializar el cliente de IA: {e}")
        return None


def consultar_ia(system_prompt: str, mensaje_usuario: str) -> str:
    """Envía una consulta al modelo con el texto del expediente como contexto."""
    cliente = obtener_cliente_ia()
    if cliente is None:
        return ""
    try:
        contexto = st.session_state.texto_expediente[:MAX_CARACTERES_CONTEXTO]
        respuesta = cliente.messages.create(
            model=MODELO_IA,
            max_tokens=1500,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"EXPEDIENTE:\n{contexto}\n\nCONSULTA:\n{mensaje_usuario}",
                }
            ],
        )
        return respuesta.content[0].text
    except Exception as e:
        return f"Ocurrió un error al consultar la IA: {e}"


# ------------------------------------------------------------------
# ENCABEZADO
# ------------------------------------------------------------------

st.markdown(
    """
    <div class="header-app">
        <h1>⚖️ Asistente Legal Online</h1>
        <p>Plataforma de análisis de expedientes, consultas jurídicas y redacción asistida</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Estado")
    if st.session_state.nombre_expediente:
        st.success(f"Expediente activo:\n**{st.session_state.nombre_expediente}**")
        st.caption(f"{len(st.session_state.texto_expediente):,} caracteres extraídos")
    else:
        st.info("Todavía no cargaste ningún expediente.")

tab_carga, tab_buscador, tab_chat, tab_escritos = st.tabs(
    ["📂 Expedientes", "🔍 Buscador", "💬 Asistente Jurídico", "📝 Generador de Escritos"]
)


# ------------------------------------------------------------------
# TAB 1: CARGA DE EXPEDIENTES
# ------------------------------------------------------------------

with tab_carga:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("#### Cargar expediente judicial (PDF)")
    st.caption("Admite expedientes extensos. La extracción puede tardar unos segundos según el tamaño.")

    archivo = st.file_uploader("Seleccioná el archivo PDF", type=["pdf"])

    if archivo is not None:
        if st.button("Procesar expediente"):
            with st.spinner("Extrayendo texto del expediente..."):
                texto = extraer_texto_pdf(archivo)
            if texto:
                st.session_state.texto_expediente = texto
                st.session_state.nombre_expediente = archivo.name
                st.session_state.historial_chat = []
                st.session_state.ultimo_escrito = ""
                st.success(f"Expediente '{archivo.name}' procesado correctamente ({len(texto):,} caracteres).")
            else:
                st.error("No se pudo extraer texto del PDF. Puede ser un archivo escaneado sin OCR.")

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.texto_expediente:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Vista previa del texto extraído")
        st.text_area(
            "Contenido (solo lectura)",
            value=st.session_state.texto_expediente[:5000] + (
                "\n\n[...]" if len(st.session_state.texto_expediente) > 5000 else ""
            ),
            height=300,
            disabled=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# TAB 2: BUSCADOR DE TÉRMINOS
# ------------------------------------------------------------------

with tab_buscador:
    if not st.session_state.texto_expediente:
        st.info("Cargá un expediente en la pestaña 'Expedientes' para poder buscar términos.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        termino = st.text_input("Buscar palabra o término dentro del expediente")
        st.markdown("</div>", unsafe_allow_html=True)

        if termino:
            try:
                resultados = buscar_termino(st.session_state.texto_expediente, termino)
                if resultados:
                    st.markdown(f"**{len(resultados)} coincidencia(s) encontrada(s):**")
                    for fragmento in resultados:
                        st.markdown(f'<div class="resultado-busqueda">…{fragmento}…</div>', unsafe_allow_html=True)
                else:
                    st.warning("No se encontraron coincidencias.")
            except Exception as e:
                st.error(f"Error al realizar la búsqueda: {e}")


# ------------------------------------------------------------------
# TAB 3: ASISTENTE DE CONSULTAS JURÍDICAS (CHAT / Q&A)
# ------------------------------------------------------------------

with tab_chat:
    if not st.session_state.texto_expediente:
        st.info("Cargá un expediente en la pestaña 'Expedientes' para consultar sobre su contenido.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Consultá sobre el expediente cargado")
        st.caption("Ejemplos: '¿Cuál fue el último movimiento?' · '¿Hay alguna medida cautelar vigente?' · '¿Qué plazos corren?'")

        for turno in st.session_state.historial_chat:
            clase = "chat-usuario" if turno["rol"] == "usuario" else "chat-asistente"
            st.markdown(f'<div class="{clase}">{turno["texto"]}</div>', unsafe_allow_html=True)

        pregunta = st.chat_input("Escribí tu consulta jurídica...")

        if pregunta:
            st.session_state.historial_chat.append({"rol": "usuario", "texto": pregunta})
            system_prompt = (
                "Sos un asistente jurídico que responde exclusivamente en base al contenido del "
                "expediente proporcionado. Si la información no está en el expediente, indicalo "
                "claramente en lugar de inventar datos. Respondé en español, de forma precisa y profesional."
            )
            with st.spinner("Analizando el expediente..."):
                respuesta = consultar_ia(system_prompt, pregunta)
            if respuesta:
                st.session_state.historial_chat.append({"rol": "asistente", "texto": respuesta})
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------
# TAB 4: GENERADOR AUTOMÁTICO DE ESCRITOS
# ------------------------------------------------------------------

with tab_escritos:
    if not st.session_state.texto_expediente:
        st.info("Cargá un expediente en la pestaña 'Expedientes' para generar borradores basados en su contenido.")
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Generar borrador de escrito")

        tipo_escrito = st.selectbox(
            "Tipo de escrito",
            [
                "Contestación de demanda",
                "Memorial",
                "Escrito de estilo (presentación general)",
                "Solicitud de medida cautelar",
                "Recurso de apelación",
            ],
        )
        instrucciones_extra = st.text_area(
            "Instrucciones adicionales (opcional)",
            placeholder="Ej: enfatizar la falta de legitimación pasiva, solicitar costas al vencido...",
            height=100,
        )

        if st.button("Generar escrito"):
            system_prompt = (
                "Sos un abogado experto en redacción de escritos judiciales en Argentina. "
                "A partir del expediente proporcionado, redactá un borrador profesional, "
                "formal y bien estructurado del tipo de escrito solicitado. Usá lenguaje "
                "jurídico apropiado, dejá indicado entre corchetes [ ] los datos que falten "
                "o deban ser completados por el abogado. Respondé en español."
            )
            mensaje = f"Tipo de escrito solicitado: {tipo_escrito}.\nInstrucciones adicionales: {instrucciones_extra or 'ninguna'}."
            with st.spinner("Redactando borrador..."):
                borrador = consultar_ia(system_prompt, mensaje)
            if borrador:
                st.session_state.ultimo_escrito = borrador

        st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.ultimo_escrito:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("#### Borrador generado")
            st.text_area("Editá el texto si lo necesitás", value=st.session_state.ultimo_escrito, height=350, key="editor_escrito")
            st.download_button(
                "⬇️ Descargar borrador (.txt)",
                data=st.session_state.editor_escrito,
                file_name=f"borrador_{tipo_escrito.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
            )
            st.markdown("</div>", unsafe_allow_html=True)
