# Anexo 07: Evaluación, Métricas y Limitaciones

## 1. Métricas de Evaluación del Sistema

Para garantizar la fiabilidad del sistema, se proponen las siguientes métricas de desempeño:

### 1.1 Calidad de Datos (Data Quality)
*   **Completitud**: % de registros con `published_date` válido. (Objetivo: >95%)
*   **Unicidad**: % de duplicados eliminados en capa Silver.
*   **Frescura**: Tiempo promedio desde publicación vs. `scraped_date`. (Objetivo: < 24h)

### 1.2 Desempeño RAG (RAGas)
*   **Context Precision**: ¿Qué tan relevante es la información recuperada (chunks) para la consulta?
*   **Faithfulness**: ¿La respuesta generada se basa *realmente* en el contexto recuperado y no en alucinaciones?
*   **Answer Relevance**: ¿La respuesta contesta directamente la pregunta del usuario?

### 1.3 Machine Learning
*   **Correlación (Pearson)**: Fuerza de relación entre Señal Social y Volumen CVE. >0.7 indica correlación fuerte.
*   **Sentiment Accuracy**: (Evaluación manual por muestreo) ¿El sentimiento (-1 a 1) asignado corresponde a la realidad del tweet?

---

## 2. Riesgos y Limitaciones Conocidas

| Riesgo | Impacto | Mitigación Actual |
| :--- | :--- | :--- |
| **Bloqueo IP** | Scrapers fallan, pérdida de datos. | Rate limiting, User-Agent rotation. Plan futuro: Proxies residenciales. |
| **Alucinación LLM** | Chatbot inventa CVEs o fechas. | **CoVe (Chain-of-Verification)** prompt implementado. RAG limita contexto. |
| **Sesgo en Scoring** | "Innovation Score" sesgado por buzzwords. | Normalización TF-IDF + Prompt de IA calibrado. |
| **Costos API** | Alto consumo de tokens OpenAI. | Uso de modelos locales (Gemma/Ollama) para tareas rutinarias. |

---

## 3. Trabajo Futuro
1.  **Migración a Base de Datos Real**: Reemplazar archivos JSON/Parquet por PostgreSQL/Snowflake para escalar a TBs de datos.
2.  **Agentes Autónomos**: Implementar agentes que no solo lean, sino que *actúen* (ej. abrir tickets en Jira ante CVE crítico).
3.  **Fine-tuning**: Entrenar un modelo pequeño (Lora adapter) específicamente en jerga de ciberseguridad.
