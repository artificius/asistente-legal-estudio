import streamlit as st
import os
from google import genai
from google.genai import types
import pypdf

# Configuración de la página (Diseño corporativo y formal)
st.set_page_config(
    page_title="Asistente Legal Online | S.A.D.",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para un look corporativo (Azul marino, grises, tipografía sobria)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #e9ecef;
        border-radius: 4px;
        padding: 10px 20px;
        font-weight: 600;
        color: #495057;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1d3557 !important;
        color: white !important;
    }
    .stButton>button {
        background-color: #1d3557;
        color: white;
        border-radius: 4px;
        font-weight: 600;
        border: none;
    }
    .stButton>button:hover {
        background-color: #457b9d;
        color: white;
    }
    h1, h2, h3 {
        color: #1d3557;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    .stAlert {
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Verificación y carga segura de la API Key de Gemini desde los Secretos de Streamlit
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ Error de configuración: No se encontró la `GEMINI_API_KEY` en los secretos de Streamlit. Por favor, configúrala en el panel de control.")
    st.stop()

# Inicializar el cliente oficial de Google GenAI
client = genai.Client(api_key=api_key)
# Usamos gemini-2.5-flash por su velocidad, gratuidad y enorme ventana de contexto para documentos largos
MODEL_ID = 'gemini-2.5-flash'

# Encabezado Corporativo
st.markdown("# ⚖️ ASISTENTE LEGAL ONLINE")
st.markdown("### Sistema Inteligente de Análisis y Gestión de Expedientes Judiciales")
st.markdown("---")

# Función auxiliar para extraer texto de PDFs usando pypdf
def extraer_texto_pdf(uploaded_file):
    texto = ""
    try:
        reader = pypdf.PdfReader(uploaded_file)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texto += t + "\n"
    except Exception as e:
        st.error(f"Error al leer el archivo PDF: {e}")
    return texto

# Sidebar corporativa informativa
with st.sidebar:
    st.markdown("### 🏢 Panel de Control")
    st.info("Estado del Sistema: **Conectado y Operativo**")
    st.markdown("---")
    st.markdown("**Módulos Activos:**")
    st.markdown("✔️ Análisis Masivo de Fojas")
    st.markdown("✔️ Consultas Inteligentes (Q&A)")
    st.markdown("✔️ Generador de Escritos")
    st.markdown("---")
    st.caption("Uso exclusivo para profesionales del derecho. Desarrollado bajo altos estándares de seguridad y confidencialidad.")

# Contenedor principal de carga de documentos (Expediente)
st.markdown("#### 📂 Carga de Expediente Judicial (Formato PDF)")
uploaded_file = st.file_uploader("Seleccione o arrastre el archivo PDF completo del expediente", type=["pdf"])

# Variables de sesión para retener el texto del expediente analizado
if "expediente_texto" not in st.session_state:
    st.session_state.expediente_texto = ""

if uploaded_file is not None:
    if not st.session_state.expediente_texto:
        with st.spinner("Procesando y indexando el expediente completo por detrás..."):
            st.session_state.expediente_texto = extraer_texto_pdf(uploaded_file)
        st.success(f"¡Expediente cargado con éxito! ({len(uploaded_file.name)}) - Listo para operar.")

# Si hay un expediente cargado, mostramos las pestañas de herramientas profesionales
if st.session_state.expediente_texto:
    
    tab1, tab2, tab3 = st.tabs(["💬 Consultas al Expediente", "🔍 Buscador de Términos", "📝 Generador de Escritos"])

    # PESTAÑA 1: CHAT / CONSULTAS INTELIGENTES
    with tab1:
        st.markdown("### Asistente de Consultas Legales")
        st.write("Realice preguntas en lenguaje natural sobre el contenido del expediente (ej: *¿Cuál fue el último movimiento?*, *¿Hay medidas cautelares vigentes?*, *¿Qué plazos procesales corren?*).")

        # Historial de chat en memoria de sesión
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_query := st.chat_input("Escriba su consulta sobre el expediente..."):
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Analizando fojas del expediente..."):
                    try:
                        # Prompt de sistema estructurado para rol legal estricto
                        prompt_completo = f"""
                        Eres un asistente legal experto y meticuloso. Basándote exclusivamente en el siguiente texto de un expediente judicial, responde con precisión jurídica a la consulta del usuario. Si la información no se encuentra en el texto, indícalo claramente.
                        
                        --- TEXTO DEL EXPEDIENTE ---
                        {st.session_state.expediente_texto[:150000]} 
                        --- FIN DEL TEXTO ---
                        
                        Consulta del Profesional: {user_query}
                        """
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=prompt_completo,
                        )
                        respuesta_ia = response.text
                        st.markdown(respuesta_ia)
                        st.session_state.messages.append({"role": "assistant", "content": respuesta_ia})
                    except Exception as e:
                        st.error(f"Ocurrió un error al procesar la consulta con la IA: {e}")

    # PESTAÑA 2: BUSCADOR DE TÉRMINOS
    with tab2:
        st.markdown("### Buscador Avanzado de Palabras Clave")
        st.write("Filtra y localiza de forma instantánea menciones de términos específicos dentro de todo el expediente.")
        
        keyword = st.text_input("Ingrese palabra o concepto a buscar (ej: 'embargo', 'caducidad', 'testigo', 'cédula'):")
        if keyword:
            with st.spinner(f"Buscando '{keyword}' en el documento..."):
                try:
                    prompt_busqueda = f"""
                    Busca en el siguiente texto del expediente todas las menciones relevantes relacionadas con la palabra clave: '{keyword}'. 
                    Extrae los fragmentos o párrafos donde se mencione e indica en qué contexto o foja aproximada aparece si es posible.
                    
                    --- TEXTO DEL EXPEDIENTE ---
                    {st.session_state.expediente_texto[:150000]}
                    """
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=prompt_busqueda,
                    )
                    st.markdown("#### Resultados de la Búsqueda:")
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"Error en la búsqueda: {e}")

    # PESTAÑA 3: GENERADOR AUTOMÁTICO DE ESCRITOS
    with tab3:
        st.markdown("### Generador Automático de Escritos Judiciales")
        st.write("Seleccione el tipo de documento que necesita redactar a partir de los antecedentes y datos reales extraídos del expediente analizado.")
        
        tipo_escrito = st.selectbox(
            "Seleccione el tipo de pieza procesal:",
            ["Contestación de Demanda / Traslado", "Memorial de Agravios", "Escrito de mero trámite (Impulso procesal)", "Planteo de Prescripción / Caducidad"]
        )
        
        instrucciones_extra = st.text_area("Instrucciones o directivas particulares para este escrito (opcional):", placeholder="Ej: Solicitar rechazo con costas, argumentar falta de legitimación...")
        
        if st.button("Generar Borrador del Escrito"):
            with st.spinner("Redactando documento legal con rigor formal..."):
                try:
                    prompt_escrito = f"""
                    Actúa como un abogado redactor senior. A partir de los datos y antecedentes del siguiente expediente judicial, redacta un borrador formal y completo para el siguiente documento: '{tipo_escrito}'.
                    Instrucciones adicionales del letrado: {instrucciones_extra}
                    
                    Utiliza formato legal adecuado (Vistos y Consideradores si corresponde, petitorio formal, estilo jurídico sobrio y profesional).
                    
                    --- TEXTO DEL EXPEDIENTE ---
                    {st.session_state.expediente_texto[:150000]}
                    """
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=prompt_escrito,
                    )
                    st.markdown("#### Borrador Generado:")
                    st.markdown(response.text)
                    st.success("Borrador generado con éxito. Puede copiar el texto para su revisión final y presentación.")
                except Exception as e:
                    st.error(f"Error al generar el escrito: {e}")

else:
    st.warning("⚠️ Por favor, cargue un archivo PDF de expediente en la parte superior para habilitar el sistema de análisis inteligente y las herramientas de redacción.")
                      
