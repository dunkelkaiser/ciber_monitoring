# Anexo 09: Asistentes LLM en Desarrollo

El desarrollo de **CiberMonitoring** ha seguido una metodología de **AI-Assisted Engineering**, donde múltiples modelos de lenguaje han actuado como "miembros del equipo" con roles especializados.

---

## 1. Equipo de IA (Roles y Responsabilidades)

| Modelo | Rol Asignado | Responsabilidades Principales |
| :--- | :--- | :--- |
| **ChatGPT (o1/4o)** | **Arquitecto Principal & Tech Lead** | Definición de estructura del proyecto, integración de componentes (Docker, Python), redacción de documentación técnica y orquestación general. |
| **Claude 3.5 Sonnet / 4.5** | **Data Architect & Backend Dev** | Diseño de esquemas de datos (Bronze/Silver/Gold), lógica compleja de ETL, refactorización de código Python y validación lógica. |
| **Gemini 3 Pro** | **Frontend Assistant & Visuals** | Apoyo en generación de referencias visuales, esquemas conceptuales y prototipado rápido de ideas. |
| **Grok** | **Design Consultant (UX/UI)** | Asesoría en teoría del color (para dashboards), escalas cromáticas para visualización de riesgo y tono de comunicación "edgy/cyberpunk". |

---

## 2. Justificación de la Selección Multimodelo

### ¿Por qué ChatGPT?
Por su capacidad de razonamiento generalista y mantenimiento de contexto largo, ideal para gestionar la visión "macro" del proyecto y asegurar que todas las piezas encajen.

### ¿Por qué Claude?
Claude destaca en **coding libre de errores** y razonamiento arquitectónico seguro. Se utilizó intensivamente para escribir los scripts de `silver_etl.py` y `gold_etl.py` donde la precisión lógica es crítica.

### ¿Por qué Gemini y Grok?
Aportan perspectivas laterales. Gemini para multimodalidad (entender imágenes/diagramas) y Grok para un enfoque estilístico diferenciador, alejado del diseño corporativo estándar.

---

## 3. Metodología de Trabajo

1.  **Definición**: El humano (User) define el requerimiento.
2.  **Consulta**: ChatGPT estructura el plan (Implementation Plan).
3.  **Ejecución**: Se delegan tareas de código específicas a los modelos (vía IDE o chat).
4.  **Revisión (CoVe Humano)**: El humano integra el código, ejecuta tests y solicita correcciones.
5.  **Documentación**: Los modelos generan borradores de la documentación (como este anexo) para revisión final.

Esta simbiosis permite acelerar el desarrollo de semanas a días, manteniendo un estándar de calidad senior.

---

## 4. Arquitectura Multi-Modelo (Storytelling)

Para la generación de narrativas ejecutivas en el Dashboard, se ha implementado una arquitectura de **"Relevo de Modelos"** para garantizar disponibilidad absoluta:

### Cadena de Responsabilidad
1.  **Primario**: **Gemini 3 Flash** (Google). Priorizado por su ventana de contexto y velocidad.
2.  **Secundario**: **GPT-5 Nano** (OpenAI). Se activa si Gemini falla o devuelve error 4xx/5xx.
3.  **Terciario**: **Claude Haiku 3.5** (Anthropic). Última línea de defensa si los anteriores fallan.

Esta lógica está encapsulada en `storytelling_generator.py` y reporta qué modelo fue utilizado en la columna `model_used` del historial.
