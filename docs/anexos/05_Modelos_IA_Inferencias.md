# Anexo 05: IA e Inferencia

## 1. Modelos de Lenguaje (LLMs)

El proyecto utiliza una estrategia híbrida de modelos para balancear costo, privacidad y capacidad.

### Modelos Soportados
*   **Gemma 3 (4B)**: Modelo "Edge" utilizado localmente vía Ollama. Ideal para tareas rápidas, clasificación y chat interactivo en el Gradio Assistant.
*   **GPT-4o / GPT-5-Nano**: Modelos de OpenAI (vía API) para tareas de razonamiento complejo, CoVe (Chain-of-Verification) y generación de código SQL/Python.
*   **Claude 3.5 Sonnet / 4.5**: Utilizado en fase de desarrollo (assistant rol) y arquitectura.

---

## 2. KPIs y Métricas de Inferencia
- **Tech Edge Score**: Nivel de innovación técnica (ML-driven).
- **Vulnerability Index**: Tendencia temporal de parches y brechas.
- **Correlation Matrix**: Correlación entre ruido social y criticidad técnica.

---

## 2. Lógica de Inferencias

### 2.1 Chain-of-Verification (CoVe)
Implementado en el Prompt del Chatbot (`gradio_assistant/app.py`).
**Objetivo**: Reducir alucinaciones.
**Proceso**:
1.  **Draft**: Genera respuesta inicial.
2.  **Plan**: Auto-cuestiona los hechos del draft.
3.  **Execute**: Verifica información (puede usar RAG tool).
4.  **Final**: Reescribe la respuesta.
*Nota: Actualmente el prompt del chatbot instruye al modelo a simular/ejecutar este proceso mentalmente.*

### 2.2 Detección de Idioma Automática
El sistema instruye al LLM a identificar el idioma de entrada del usuario y forzar la respuesta en ese mismo idioma, mejorando la UX para usuarios globales.

---

## 3. Algoritmos de Machine Learning Clásico

Además de LLMs, se usan algoritmos tradicionales en `GoldETL`:
*   **TF-IDF**: Para extracción de "features" de texto no supervisado. Base del "Complexity Score".
*   **Regresión Lineal (OLS)**: Utilizada exploratoriamente en notebooks para predecir tendencias de CVEs basadas en menciones sociales (correlación).
*   **Sentiment Analysis (Lexicon-based)**: `TextBlob` para scoring rápido de polaridad en redes sociales sin necesidad de inferencia pesada.
