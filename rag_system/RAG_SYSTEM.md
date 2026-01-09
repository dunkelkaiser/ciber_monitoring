# 🧠 Sistema RAG y Storytelling Automático

## Arquitectura RAG

```
📄 Documents → 🔪 Chunking → 🔢 Embeddings → 💾 ChromaDB → 🤖 LLM → 📊 Power BI
                                                              ↓
                                                         📝 Storytelling
```

## Stack Tecnológico

### Vector Store
- **ChromaDB**: Base de datos vectorial embebida
- **Alternativas**: Pinecone, Weaviate, Qdrant

### Embeddings
- **sentence-transformers**: Modelos locales
  - `all-MiniLM-L6-v2` (ligero, rápido)
  - `all-mpnet-base-v2` (mejor calidad)
- **OpenAI Embeddings**: `text-embedding-3-small` (API)

### LLM Providers
- **Ollama** (local): llama3, mistral, gemma3
- **OpenAI**: gpt-5, gpt-5-nano, gpt-5-mini
- **Anthropic**: claude-4.5-opus, claude-4.5-sonnet
- **Google**: gemini-3.0-flash

### Orquestación
- **LangChain**: Chains, agents, retrievers
- **LlamaIndex**: Indexing y query engine alternativo

## Implementación

### 1. Chunking Strategy

```python
# vector_store/chunking.py
from langchain.text_splitter import RecursiveCharacterTextSplitter

class SmartChunker:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def chunk_documents(self, documents):
        """
        Divide documentos en chunks con contexto
        
        Args:
            documents: Lista de dicts con {text, metadata}
        Returns:
            Lista de chunks con metadata enriquecida
        """
        chunks = []
        
        for doc in documents:
            splits = self.splitter.split_text(doc['text'])
            
            for i, chunk in enumerate(splits):
                chunks.append({
                    'text': chunk,
                    'metadata': {
                        **doc['metadata'],
                        'chunk_index': i,
                        'total_chunks': len(splits)
                    }
                })
        
        return chunks

# Uso
chunker = SmartChunker()
chunks = chunker.chunk_documents([
    {
        'text': 'CVE-2024-1234 affects NVIDIA drivers...',
        'metadata': {
            'source': 'nvidia_security',
            'date': '2024-01-15',
            'severity': 'HIGH'
        }
    }
])
```

### 2. Embedding Generation

```python
# vector_store/embeddings.py
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingService:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    
    def embed_chunks(self, chunks):
        """Generar embeddings para chunks"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True
        )
        
        # Agregar embeddings a chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding.tolist()
        
        return chunks
    
    def embed_query(self, query):
        """Embedding para query de búsqueda"""
        return self.model.encode(query).tolist()

# Uso
embedder = EmbeddingService()
chunks_with_embeddings = embedder.embed_chunks(chunks)
```

### 3. ChromaDB Manager

```python
# vector_store/chromadb_manager.py
import chromadb
from chromadb.config import Settings

class VectorStore:
    def __init__(self, persist_directory='./chroma_db'):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        self.collection = self.client.get_or_create_collection(
            name="cyber_intel",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_documents(self, chunks):
        """Agregar documentos con embeddings"""
        ids = [f"doc_{i}" for i in range(len(chunks))]
        documents = [chunk['text'] for chunk in chunks]
        embeddings = [chunk['embedding'] for chunk in chunks]
        metadatas = [chunk['metadata'] for chunk in chunks]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
    
    def search(self, query_embedding, n_results=5, filter_dict=None):
        """Búsqueda semántica"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_dict  # Filtros de metadata
        )
        
        return results

# Uso
vector_store = VectorStore()
vector_store.add_documents(chunks_with_embeddings)

# Búsqueda con filtros
results = vector_store.search(
    query_embedding=embedder.embed_query("NVIDIA vulnerabilities"),
    n_results=5,
    filter_dict={"severity": "HIGH"}
)
```

### 4. LLM Router (Multi-Provider)

```python
# rag_system/llm_router.py
from langchain.llms import Ollama
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
import os

class LLMRouter:
    def __init__(self, provider='ollama', model='llama3'):
        self.provider = provider
        self.model = model
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        if self.provider == 'ollama':
            return Ollama(
                model=self.model,
                base_url='http://localhost:11434'
            )
        
        elif self.provider == 'openai':
            return ChatOpenAI(
                model=self.model,
                api_key=os.getenv('OPENAI_API_KEY'),
                temperature=0.3
            )
        
        elif self.provider == 'anthropic':
            return ChatAnthropic(
                model=self.model,
                api_key=os.getenv('ANTHROPIC_API_KEY'),
                temperature=0.3
            )
        
        elif self.provider == 'google':
            # Implementar Google Gemini
            pass
    
    def generate(self, prompt, system_prompt=None):
        """Generar respuesta con contexto"""
        if self.provider == 'ollama':
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return self.llm.invoke(full_prompt)
        
        else:  # Chat models
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            
            response = self.llm.invoke(messages)
            return response.content

# Uso
llm = LLMRouter(provider='ollama', model='llama3')
```

### 5. RAG Pipeline

```python
# rag_system/storytelling_engine.py
from vector_store.chromadb_manager import VectorStore
from vector_store.embeddings import EmbeddingService
from rag_system.llm_router import LLMRouter
from rag_system.prompt_templates import STORYTELLING_PROMPT

class StorytellingEngine:
    def __init__(self, llm_provider='ollama', llm_model='llama3'):
        self.vector_store = VectorStore()
        self.embedder = EmbeddingService()
        self.llm = LLMRouter(provider=llm_provider, model=llm_model)
    
    def generate_story(self, query, n_results=5):
        """
        Generar narrativa a partir de datos vectoriales
        
        Args:
            query: Pregunta o tema para el storytelling
            n_results: Número de documentos a recuperar
        """
        # 1. Embedding del query
        query_embedding = self.embedder.embed_query(query)
        
        # 2. Búsqueda semántica
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results
        )
        
        # 3. Construir contexto
        context = self._build_context(results)
        
        # 4. Generar narrativa con LLM
        prompt = STORYTELLING_PROMPT.format(
            query=query,
            context=context
        )
        
        story = self.llm.generate(
            prompt=prompt,
            system_prompt="Eres un analista de ciberseguridad experto."
        )
        
        return {
            'story': story,
            'sources': results['metadatas'][0],
            'confidence': self._calculate_confidence(results)
        }
    
    def _build_context(self, results):
        """Construir contexto a partir de resultados"""
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        
        context_parts = []
        for doc, meta in zip(documents, metadatas):
            context_parts.append(
                f"[Fuente: {meta['source']}, Fecha: {meta['date']}]\n{doc}"
            )
        
        return "\n\n---\n\n".join(context_parts)
    
    def _calculate_confidence(self, results):
        """Calcular confianza basada en distancias"""
        distances = results['distances'][0]
        avg_distance = sum(distances) / len(distances)
        
        # Convertir distancia coseno a confianza
        confidence = (1 - avg_distance) * 100
        return round(confidence, 2)

# Uso
engine = StorytellingEngine(llm_provider='ollama', model='llama3')

story_result = engine.generate_story(
    query="¿Qué vulnerabilidades críticas han surgido esta semana en NVIDIA?"
)

print(story_result['story'])
print(f"Confianza: {story_result['confidence']}%")
```

### 6. Prompt Templates

```python
# rag_system/prompt_templates.py

STORYTELLING_PROMPT = """
Basándote en el siguiente contexto de ciberseguridad, genera una narrativa ejecutiva 
que explique la situación actual de forma clara y accionable.

PREGUNTA DEL USUARIO:
{query}

CONTEXTO TÉCNICO:
{context}

INSTRUCCIONES:
1. Resume los hallazgos clave en 2-3 puntos principales
2. Explica el impacto potencial en infraestructura tecnológica
3. Proporciona recomendaciones accionables
4. Usa lenguaje técnico pero accesible
5. Destaca correlaciones entre vulnerabilidades y tendencias tecnológicas

FORMATO DE SALIDA:
## 🎯 Resumen Ejecutivo
[Tu resumen aquí]

## 🔍 Hallazgos Clave
[Puntos principales]

## 💡 Recomendaciones
[Acciones sugeridas]
"""

DASHBOARD_RECOMMENDATION_PROMPT = """
Basándote en los datos actuales de ciberseguridad, sugiere la mejor configuración 
de dashboard en Power BI.

DATOS ACTUALES:
{data_summary}

MÉTRICAS DISPONIBLES:
- CVEs por severidad
- Tendencias temporales
- Correlaciones tecnológicas
- Distribución por fabricante

GENERA:
1. Layout recomendado del dashboard
2. Visuales más efectivos para cada métrica
3. KPIs prioritarios
4. Filtros sugeridos
"""

EXPERT_QA_PROMPT = """
Eres un experto en ciberseguridad con conocimiento profundo de vulnerabilidades, 
tecnologías emergentes y mejores prácticas de seguridad.

CONTEXTO:
{context}

PREGUNTA:
{question}

Proporciona una respuesta detallada, técnicamente precisa y accionable. 
Cita fuentes específicas del contexto cuando sea relevante.
"""
```

## Integración con Power BI

### Opción 1: Python Script en Power BI

```python
# powerbi/rag_integration.py
from rag_system.storytelling_engine import StorytellingEngine

# Este script corre dentro de Power BI
engine = StorytellingEngine(llm_provider='ollama', model='llama3')

# Obtener datos del modelo de Power BI
current_date = dataset['Date'].max()
cves_this_week = dataset[dataset['Date'] >= current_date - timedelta(days=7)]

# Generar storytelling
story = engine.generate_story(
    query=f"Analiza las {len(cves_this_week)} vulnerabilidades de esta semana"
)

# Retornar como tabla para visualización
result = pd.DataFrame({
    'Narrative': [story['story']],
    'Confidence': [story['confidence']]
})
```

### Opción 2: API REST + Custom Visual

```python
# api/routers/storytelling.py
from fastapi import APIRouter
from rag_system.storytelling_engine import StorytellingEngine

router = APIRouter()
engine = StorytellingEngine()

@router.post("/generate-story")
async def generate_story(query: str):
    result = engine.generate_story(query)
    return result

# Power BI Custom Visual hace fetch a este endpoint
```

## Recomendaciones para Dashboard

### Layout Inteligente con RAG

```python
def recommend_dashboard_layout(data_summary):
    """
    RAG sugiere el mejor layout según los datos actuales
    """
    engine = StorytellingEngine()
    
    recommendation = engine.generate_story(
        query=f"""
        Dados estos datos: {data_summary}
        Sugiere el layout óptimo de dashboard con:
        - Posición de cada visual
        - KPIs prioritarios
        - Filtros recomendados
        """
    )
    
    return recommendation

# Uso
summary = {
    'total_cves': 145,
    'critical_ratio': 0.23,
    'trending_vendors': ['NVIDIA', 'Intel'],
    'correlation_strength': 0.78
}

layout_rec = recommend_dashboard_layout(summary)
```

### Alertas Contextualizadas

```python
def generate_alert(cve_data):
    """Alerta con contexto RAG"""
    engine = StorytellingEngine()
    
    alert = engine.generate_story(
        query=f"""
        CVE-{cve_data['id']} detectado.
        Severidad: {cve_data['severity']}
        Producto: {cve_data['product']}
        
        Explica por qué es crítico y qué hacer.
        """
    )
    
    return alert
```

## Deployment

### Docker Compose con Ollama

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    command: serve

  rag_service:
    build: ./rag_system
    depends_on:
      - ollama
    environment:
      - LLM_PROVIDER=ollama
      - LLM_MODEL=llama3
    volumes:
      - ./chroma_db:/app/chroma_db

volumes:
  ollama_data:
```

### Inicialización de Modelos

```bash
# Pull modelos de Ollama
docker exec -it ollama ollama pull llama3
docker exec -it ollama ollama pull mistral
docker exec -it ollama ollama pull gemma:4b
```

## Optimizaciones

### Caching de Embeddings

```python
import hashlib
import pickle

class CachedEmbedder:
    def __init__(self, cache_dir='./cache'):
        self.cache_dir = cache_dir
        self.embedder = EmbeddingService()
    
    def embed_query(self, query):
        # Hash del query
        query_hash = hashlib.md5(query.encode()).hexdigest()
        cache_path = f"{self.cache_dir}/{query_hash}.pkl"
        
        # Buscar en cache
        if os.path.exists(cache_path):
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        
        # Generar y cachear
        embedding = self.embedder.embed_query(query)
        with open(cache_path, 'wb') as f:
            pickle.dump(embedding, f)
        
        return embedding
```

### Batch Processing

```python
def process_gold_layer_to_vectors(batch_size=100):
    """Procesar Gold layer en batches"""
    gold_data = load_gold_layer()
    
    for i in range(0, len(gold_data), batch_size):
        batch = gold_data[i:i+batch_size]
        
        chunks = chunker.chunk_documents(batch)
        chunks_with_emb = embedder.embed_chunks(chunks)
        vector_store.add_documents(chunks_with_emb)
        
        print(f"Processed {i+len(batch)}/{len(gold_data)}")
```