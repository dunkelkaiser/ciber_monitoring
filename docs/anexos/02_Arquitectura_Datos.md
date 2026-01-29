# Anexo 02: Arquitectura de Datos

## 1. Modelo Medallion (Bronze/Silver/Gold)
El sistema implementa una arquitectura de datos en capas (Medallion Architecture) para garantizar la calidad, trazabilidad y evolución de los datos.

```mermaid
graph LR
    A[Fuentes Externas] --> B[Bronze Layer\n(Raw Ingestion)]
    B --> C[Silver Layer\n(Validated & Cleaned)]
    C --> D[Gold Layer\n(Business Aggregates)]
    D --> E[Power BI / API]
```

---

## 2. Capa Bronze (Raw)
- **Ubicación**: `data_engineering/bronze/`
- **Formato**: Archivos JSON crudos con metadatos de recolección.
- **Propósito**: Almacenamiento inmutable de la respuesta original de la fuente.
- **Esquema**: Flexible (Schema-on-Read).
- **Ejemplo**:
  ```json
  [
    {
      "title": "GPT-5 Announced",
      "url": "https://openai.com/blog/...",
      "published_date": "2025-08-01T10:00:00Z",
      "scraped_date": "2026-01-14T22:00:00Z",
      "source": "openai"
    }
  ]
  ```

---

## 3. Capa Silver (Validated)
- **Ubicación**: `data_engineering/silver/`
- **Formato**: Parquet (Columnares, comprimidos)
- **Propósito**: Datos limpios, deduplicados y validados.
- **Validación**: Utiliza **Great Expectations** para reglas de calidad (ej. `published_date` no nulo, URLs válidas).
- **Esquemas Definidos**:
    1. **Research Papers**: Unificación de NVIDIA, OpenAI, arXiv.
    2. **Vulnerabilities**: Unificación de CVE Mitre, Intel.
    3. **Social Signals**: Tweets y Reddit posts limpios.

---

## 4. Capa Gold (Aggregated)
- **Ubicación**: `data_engineering/gold/`
- **Formato**: Parquet
- **Propósito**: Tablas listas para consumo analítico y modelos de ML.
- **Optimización**: Procesamiento en paralelo mediante `ThreadPoolExecutor` para llamadas masivas a LLMs, acelerando el cálculo del `Tech Edge Score`.
- **Tablas Principales**:
    - **`gold_tech_edge_score`**: Puntuación de innovación por paper (0-100).
    - **`gold_vulnerability_index`**: Serie temporal de riesgo agregado diario.
    - **`gold_correlation_matrix`**: Matriz de correlación entre sentimiento social y volumen de vulnerabilidades.

---

## 5. Diccionario de Datos Clave

### Entidades Comunes
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | String | Identificador único del registro (hash o ID fuente). |
| `source_entity` | Categorical | Fuente original (NVIDIA, MITRE, HACKER NEWS, ARXIV). |
| `published_date` | Datetime (UTC) | Fecha de evento. |
| `sentiment_score` | Float (-1.0 a 1.0) | Polaridad del texto (Textblob/VADER). |
| `complexity_score` | Float (0-100) | Densidad técnica calculada (TF-IDF). |
| `ai_innovation_score` | Float (0-100) | Evaluación LLM sobre la relevancia tecnológica. |
