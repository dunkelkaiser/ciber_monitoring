# Anexo 01: Scraping e Ingesta de Datos

## 1. Visión General
El módulo de ingesta (`agents/scrapers`) es responsable de la recolección autónoma de datos desde fuentes heterogéneas. Utiliza técnica de **Web Scraping** avanzado y consultas a **APIs oficiales** para alimentar el pipeline de datos.

### Tecnologías Clave
- **Playwright**: Para navegación headless en sitios dinámicos (SPA) como NVIDIA y OpenAI Blog.
- **AsyncIO**: Para ejecución concurrente de múltiples scrapers.
- **PRAW**: Wrapper oficial para la API de Reddit.
- **arXiv API**: Para consultas académicas estructuradas.

---

## 2. Catálogo de Scrapers

| Scraper | Fuente | Método | Frecuencia | Datos Clave |
| :--- | :--- | :--- | :--- | :--- |
| **NvidiaScraper** | NVIDIA Research | Playwright (DOM) | Semanal | Títulos, abstracts, links a papers. |
| **OpenAIBlogScraper** | OpenAI Blog | Playwright (DOM) | Semanal | Artículos de investigación, anuncios. |
| **CVEMitreScraper** | CVE Mitre / NIST | Playwright (Search) | Diario | CVE ID, descripción, severidad. |
| **IntelScraper** | Intel Security | Playwright (DOM) | Diario | Advisories, parches. |
| **TwitterScraper** | Twitter/X API | API (Tweepy) | Tiempo Real | Discusión social, tendencias. |
| **RedditScraper** | Reddit API | API (PRAW) [Standby] | Diario | Posts, comentarios, sentimiento. |
| **ArxivScraper** | arXiv.org | API (xml) | Semanal | Papers académicos (CS, AI, Crypto). |

---

## 3. Estrategias de Implementación

### 3.1 Manejo de Sesiones y Bloqueos
- **User-Agent Rotation**: Se utiliza `fake-useragent` para rotar identidades en cada petición.
- **Rate Limiting**: Implementado en la clase base `BaseScraper`. Esperas aleatorias entre peticiones (1-3s) para evitar detección.
- **Retry Logic**: Decoradores de `tenacity` para reintentar fallos de red (3 intentos con backoff exponencial).

### 3.2 Estandarización de Fechas
Todos los scrapers normalizan el tiempo a UTC ISO 8601:
- `published_date`: Fecha de creación del contenido en la fuente. Si no existe, "UNKNOWN".
- `scraped_date`: `datetime.utcnow().isoformat() + "Z"`.

---

## 4. Ejecución y Orquestación

El script `orchestrator.py` gestiona el ciclo de vida de los scrapers.

### Comandos Docker
```bash
# Ejecutar TODO el pipeline de ingesta
docker-compose run scrapers python agents/scrapers/orchestrator.py --scraper all

# Ejecutar un scraper específico
docker-compose run scrapers python agents/scrapers/orchestrator.py --scraper reddit
docker-compose run scrapers python agents/scrapers/orchestrator.py --scraper arxiv
```

### Flujo de Datos
1. **Ejecución**: Scraper obtiene HTML/JSON.
2. **Parsing**: Extracción de campos relevantes.
3. **Persistencia**: Guardado en `data_engineering/bronze/{source}_raw_{timestamp}.json`.
