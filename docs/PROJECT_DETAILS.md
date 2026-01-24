# Documentación Detallada: CiberMonitoring

Este documento proporciona una visión profunda de los componentes técnicos, decisiones de diseño y flujo de datos del proyecto CiberMonitoring.

## 1. Misión de Datos
CiberMonitoring es un ecosistema diseñado para detectar la correlación entre la innovación en Hardware/IA (NVIDIA, OpenAI) y el ecosistema de amenazas (CVE, Hacker News). El objetivo principal es proporcionar un "Índice de Riesgo de Adopción" mediante el cruce de señales sociales y vulnerabilidades técnicas.

## 2. Arquitectura Multicapa (Bronze, Silver, Gold)

### Capa Bronze (Raw Ingestion)
- **Scrapers**: 
  - `CVEMitreScraper`: Consulta la base de datos de Mitre.
  - `IntelScraper`: Extrae avisos de seguridad de Intel.
  - `ArxivScraper`: Recolecta abstracts de investigación científica.
  - `HackerNewsScraper`: Captura señales de tendencia en tecnología y seguridad.
- **Formato**: Archivos JSON crudos con metadatos de recolección.

### Capa Silver (Normalization)
- **Proceso**: `cleaner_etl.py`.
- **Acciones**: 
  - Limpieza de HTML.
  - Estandarización de fechas a ISO-8601 (UTC).
  - Unificación de señales sociales.
  - Generación de esquemas de validación (Great Expectations).

### Capa Gold (Business Logic & ML)
- **Proceso**: `gold_etl.py`.
- **KPIs Calculados**:
  - `Tech Edge Score`: Nivel de innovación técnica (ML-driven).
  - `Vulnerability Index`: Tendencia temporal de parches y brechas.
  - `Correlation Matrix`: Correlación entre ruido social y criticidad técnica.
- **Optimización**: Procesamiento en paralelo de llamadas a LLM para scoring masivo.

## 3. Asistente Inteligente (Gradio & RAG)
El asistente conversacional utiliza una arquitectura híbrida:
1. **RAG (Retrieval Augmented Generation)**: Consulta `chroma_db_store` para contexto histórico.
2. **Tool Use**: Llamadas API en tiempo real para obtener las últimas métricas de la capa Gold.
3. **Multi-Model Fallback**:
   - Primario: Gemini 3 Flash.
   - Secundario: GPT-5 Nano.
   - Terciario: Claude Haiku.

## 4. Stack de Infraestructura
- **Docker**: Contenedores optimizados para Python 3.11+.
- **Redes**: Aislamiento de capas (DB, API, Front).
- **Seguridad**: Gestión centralizada de secretos mediante `.env` (ignorado por Git).

---
*Documentación generada para el cierre del proyecto integrador.*
