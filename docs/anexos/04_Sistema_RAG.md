# Anexo 04: Sistema RAG (Retrieval-Augmented Generation)

## 1. Arquitectura RAG

El sistema RAG permite al Asistente IA (Chatbot) y a los scripts de análisis acceder a una "memoria a largo plazo" basada en los datos recolectados.

### Componentes
1.  **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`. Convierte texto en vectores de 384 dimensiones.
2.  **Vector Store**: **chroma_db_store**. Base de datos local optimizada para búsqueda de similaridad para contexto histórico.
3.  **Retrieve Strategy**: Búsqueda semántica por similitud coseno + filtros de metadatos (fecha, fuente).
4.  **Real-time Tool Use**: El sistema realiza llamadas API en tiempo real para obtener las últimas métricas de la capa Gold y complementar el contexto recuperado.

---

## 2. Ingesta Vectorial

**Script**: `rag_system/build_vector_store.py` (Parte del pipeline ETL o ejecución manual).

### Estrategia de Chunking
*   **RecursiveCharacterTextSplitter**: Divide textos largos (papers, blogs) en fragmentos manejables.
*   **Configuración**:
    *   `chunk_size`: 1000 caracteres.
    *   `chunk_overlap`: 200 caracteres (para mantener contexto entre cortes).

### Metadata Enriquecida
Cada vector almacenado incluye metadatos críticos para el filtrado posterior:
*   `source`: (nvidia, cve, reddit)
*   `date`: Fecha ISO.
*   `category`: (research, vulnerability, social)

---

## 3. Motor de Storytelling

El sistema no solo "busca", sino que "narra". Utiliza un **LLM Router** para conectar con modelos locales (Ollama) o remotos (OpenAI).

### Flujo de Consulta
1.  **Query Usuario**: "¿Qué riesgos hay con GPUs hoy?"
2.  **Embedding**: Vectorización de la pregunta.
3.  **Retrieval**: ChromaDB devuelve los 5 chunks más similares (ej. un CVE de drivers NVIDIA y un paper de exploits).
4.  **Generación Contextual**:
    *   Se construye un prompt con los chunks recuperados.
    *   Se inyectan instrucciones de estilo (ver Anexo 08).
    *   El LLM genera un resumen ejecutivo o narrativa.

### Integración en Dashboard
Este motor puede ser invocado por **Power BI** (vía Python Script) para generar explicaciones textuales automáticas ("Insight Generation") que acompañan a los gráficos.
