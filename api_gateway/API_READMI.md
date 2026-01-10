# 🌐 API Gateway - CiberMonitoring

Este módulo expone los datos de inteligencia procesados (Capa Gold) a través de una API RESTful de alto rendimiento construida con **FastAPI**.

## 🚀 Inicio Rápido

### Prerrequisitos
Asegúrate de estar en la carpeta `api_gateway` y tener instaladas las dependencias:

```bash
cd api_gateway
pip install -r requirements.txt
```

### Ejecutar el Servidor
Para iniciar el servidor de desarrollo en local:

```bash
python main.py
```
O usando uvicorn directamente:
```bash
uvicorn main:app --reload
```

El servidor iniciará en: `http://localhost:8000`

---

## 📚 Documentación Interactiva (Swagger UI)

Una vez iniciado, visita **[http://localhost:8000/docs](http://localhost:8000/docs)** para ver la documentación automática, probar los endpoints y ver los esquemas de respuesta.

---

## 🔗 Endpoints Disponibles

### 🧠 Insights (Inteligencia)

#### `GET /api/v1/tech-edge-score`
Devuelve el ranking de innovación tecnológica basado en papers de investigación analizados por IA.
*   **Uso:** Visualización de "Hype Cycle" o ranking de temas emergentes.
*   **Datos Clave:** `ai_innovation_score`, `complexity_score`, `tech_edge_total`.

#### `GET /api/v1/vulnerability-index`
Retorna el índice histórico de vulnerabilidades agragadas.
*   **Uso:** Gráficos de series de tiempo para predecir tendencias de riesgo.
*   **Datos Clave:** `days_risk_score`, `risk_moving_avg`.

### 📉 Correlaciones

#### `GET /api/v1/correlation/matrix`
Datos fusionados (diarios) de Sentimiento Social vs Riesgo de Vulnerabilidad.
*   **Uso:** Scatter plots o líneas temporales comparativas.

#### `GET /api/v1/correlation/values`
Valores calculados de correlación (Coeficientes de Pearson).
*   **Uso:** Tarjetas de resumen "KPI" (ej: "Correlación Alta detectada: 0.85").

---

## 🛠️ Arquitectura

La API lee directamente los archivos optimizados **Parquet** de la capa `data_engineering/gold`. Esto garantiza:
1.  **Velocidad**: Lectura columnar rápida sin sobrecarga de bases de datos tradicionales para lectura.
2.  **Desacoplamiento**: El sistema de ETL puede regenerar los parquets independientemente de la API.
