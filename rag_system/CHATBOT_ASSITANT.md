# 🤖 Asistente Conversacional Gradio con Gemma 3

## Arquitectura del Asistente

```
📄 Upload PDF/CSV → 📊 Process → 🔢 Embeddings → 💾 ChromaDB
                                                        ↓
🧑 User Question → 🔍 Semantic Search → 🤖 Gemma 3 4B → 💬 Expert Answer
```

## Stack Tecnológico

- **Framework UI**: Gradio 4.x
- **LLM Local**: Gemma 3 4B (4-bit quantized via Ollama)
- **Vector Store**: ChromaDB (compartido con RAG principal)
- **Document Processing**: 
  - PDFs: PyMuPDF, pdfplumber
  - Excel: openpyxl, pandas
  - CSV: pandas, chardet
- **Embeddings**: sentence-transformers

## Implementación

### 1. Gradio App Principal

```python
# gradio_assistant/app.py
import gradio as gr
from document_uploader import DocumentUploader
from expert_qa import ExpertQA
from vector_store.chromadb_manager import VectorStore

class CyberIntelAssistant:
    def __init__(self):
        self.uploader = DocumentUploader()
        self.qa = ExpertQA(
            llm_provider='ollama',
            model='gemma:4b'
        )
        self.vector_store = VectorStore()
    
    def process_file_and_question(self, file, question, use_file_context=True):
        """
        Procesar archivo subido y responder pregunta
        """
        response = {
            'answer': '',
            'sources': [],
            'file_processed': False
        }
        
        # Procesar archivo si se subió
        if file is not None and use_file_context:
            try:
                processed = self.uploader.process(file)
                response['file_processed'] = True
                response['sources'].append({
                    'type': 'uploaded_file',
                    'name': file.name,
                    'chunks': len(processed['chunks'])
                })
            except Exception as e:
                return f"❌ Error procesando archivo: {str(e)}"
        
        # Responder pregunta
        qa_result = self.qa.answer(question, use_file=use_file_context)
        response['answer'] = qa_result['answer']
        response['sources'].extend(qa_result['sources'])
        
        # Formatear respuesta
        formatted = self._format_response(response)
        return formatted
    
    def _format_response(self, response):
        """Formatear respuesta para Gradio"""
        output = f"## 💡 Respuesta\n\n{response['answer']}\n\n"
        
        if response['file_processed']:
            output += "✅ **Archivo procesado y agregado a la base de conocimiento**\n\n"
        
        if response['sources']:
            output += "## 📚 Fuentes Consultadas\n\n"
            for src in response['sources']:
                if src['type'] == 'uploaded_file':
                    output += f"- 📄 {src['name']} ({src['chunks']} chunks)\n"
                else:
                    output += f"- 🔗 {src['source']} (confianza: {src['confidence']}%)\n"
        
        return output

# Inicializar asistente
assistant = CyberIntelAssistant()

# Interfaz Gradio
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🛡️ Asistente Experto en Ciberinteligencia
    
    Sube documentos para enriquecer la base de conocimiento o haz preguntas directamente.
    
    **Modelo**: Gemma 3 4B (corriendo localmente)
    """)
    
    with gr.Row():
        with gr.Column(scale=1):
            file_input = gr.File(
                label="📁 Subir Documento",
                file_types=[".pdf", ".csv", ".xlsx", ".json", ".txt"]
            )
            
            use_file = gr.Checkbox(
                label="Usar contexto del archivo",
                value=True
            )
            
            gr.Markdown("""
            ### Tipos de Archivo Soportados:
            - 📄 **PDF**: Reportes de seguridad, CVEs
            - 📊 **CSV/Excel**: Datos de vulnerabilidades
            - 📝 **TXT/JSON**: Logs, configuraciones
            """)
        
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="❓ Tu Pregunta",
                placeholder="Ej: ¿Qué vulnerabilidades críticas afectan a NVIDIA?",
                lines=3
            )
            
            submit_btn = gr.Button("🚀 Consultar", variant="primary")
            
            output = gr.Markdown(label="Respuesta del Experto")
    
    # Ejemplos predefinidos
    gr.Examples(
        examples=[
            [None, "¿Cuáles son las vulnerabilidades más críticas esta semana?", False],
            [None, "Explica la correlación entre CVEs de NVIDIA e Intel", False],
            [None, "¿Qué tendencias tecnológicas presentan mayor riesgo?", False],
        ],
        inputs=[file_input, question_input, use_file]
    )
    
    # Event handlers
    submit_btn.click(
        fn=assistant.process_file_and_question,
        inputs=[file_input, question_input, use_file],
        outputs=output
    )
    
    question_input.submit(
        fn=assistant.process_file_and_question,
        inputs=[file_input, question_input, use_file],
        outputs=output
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
```

### 2. Document Uploader

```python
# gradio_assistant/document_uploader.py
import PyMuPDF  # fitz
import pandas as pd
from pathlib import Path
import json
from vector_store.chunking import SmartChunker
from vector_store.embeddings import EmbeddingService
from vector_store.chromadb_manager import VectorStore

class DocumentUploader:
    def __init__(self):
        self.chunker = SmartChunker(chunk_size=800, chunk_overlap=150)
        self.embedder = EmbeddingService()
        self.vector_store = VectorStore()
    
    def process(self, file):
        """
        Procesar archivo subido y agregarlo al vector store
        
        Args:
            file: Gradio file object
        Returns:
            Dict con metadata del procesamiento
        """
        file_path = Path(file.name)
        extension = file_path.suffix.lower()
        
        # Extraer texto según tipo de archivo
        if extension == '.pdf':
            text = self._extract_pdf(file.name)
        elif extension in ['.csv', '.xlsx']:
            text = self._extract_tabular(file.name)
        elif extension == '.json':
            text = self._extract_json(file.name)
        elif extension == '.txt':
            with open(file.name, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError(f"Tipo de archivo no soportado: {extension}")
        
        # Crear documento con metadata
        document = {
            'text': text,
            'metadata': {
                'source': file_path.name,
                'type': extension,
                'uploaded_at': datetime.now().isoformat(),
                'user_uploaded': True
            }
        }
        
        # Chunking
        chunks = self.chunker.chunk_documents([document])
        
        # Embeddings
        chunks_with_embeddings = self.embedder.embed_chunks(chunks)
        
        # Agregar a ChromaDB
        self.vector_store.add_documents(chunks_with_embeddings)
        
        return {
            'file_name': file_path.name,
            'text_length': len(text),
            'chunks': len(chunks),
            'status': 'success'
        }
    
    def _extract_pdf(self, file_path):
        """Extraer texto de PDF"""
        doc = PyMuPDF.open(file_path)
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        return text
    
    def _extract_tabular(self, file_path):
        """Extraer texto de CSV/Excel"""
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Convertir a texto estructurado
        text_parts = []
        
        # Headers
        text_parts.append("Columnas: " + ", ".join(df.columns))
        
        # Rows
        for idx, row in df.iterrows():
            row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
            text_parts.append(row_text)
        
        return "\n".join(text_parts)
    
    def _extract_json(self, file_path):
        """Extraer texto de JSON"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Convertir a texto legible
        return json.dumps(data, indent=2)
```

### 3. Expert Q&A System

```python
# gradio_assistant/expert_qa.py
from rag_system.llm_router import LLMRouter
from vector_store.chromadb_manager import VectorStore
from vector_store.embeddings import EmbeddingService

class ExpertQA:
    def __init__(self, llm_provider='ollama', model='gemma:4b'):
        self.llm = LLMRouter(provider=llm_provider, model=model)
        self.vector_store = VectorStore()
        self.embedder = EmbeddingService()
    
    def answer(self, question, use_file=False, n_results=5):
        """
        Responder pregunta usando RAG
        
        Args:
            question: Pregunta del usuario
            use_file: Usar solo documentos subidos por usuario
            n_results: Número de chunks a recuperar
        """
        # Embedding de la pregunta
        query_embedding = self.embedder.embed_query(question)
        
        # Buscar contexto relevante
        filter_dict = {'user_uploaded': True} if use_file else None
        
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=n_results,
            filter_dict=filter_dict
        )
        
        # Construir contexto
        context = self._build_context(results)
        
        # Prompt para Gemma 3
        prompt = f"""
Eres un experto en ciberseguridad especializado en análisis de vulnerabilidades 
y tecnologías emergentes.

CONTEXTO:
{context}

PREGUNTA DEL USUARIO:
{question}

INSTRUCCIONES:
- Proporciona una respuesta técnica pero comprensible
- Cita fuentes específicas del contexto cuando sea relevante
- Si el contexto no contiene información suficiente, indícalo claramente
- Enfócate en insights accionables

RESPUESTA:
"""
        
        # Generar respuesta
        answer = self.llm.generate(prompt)
        
        return {
            'answer': answer,
            'sources': self._extract_sources(results),
            'confidence': self._calculate_confidence(results)
        }
    
    def _build_context(self, results):
        """Construir contexto a partir de resultados"""
        if not results['documents'][0]:
            return "No se encontró información relevante en la base de conocimiento."
        
        context_parts = []
        for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
            source = meta.get('source', 'Unknown')
            context_parts.append(f"[Fuente: {source}]\n{doc}")
        
        return "\n\n---\n\n".join(context_parts)
    
    def _extract_sources(self, results):
        """Extraer fuentes únicas"""
        sources = []
        seen = set()
        
        for meta, distance in zip(results['metadatas'][0], results['distances'][0]):
            source = meta.get('source', 'Unknown')
            if source not in seen:
                sources.append({
                    'source': source,
                    'type': meta.get('type', 'document'),
                    'confidence': round((1 - distance) * 100, 2)
                })
                seen.add(source)
        
        return sources
    
    def _calculate_confidence(self, results):
        """Calcular confianza promedio"""
        if not results['distances'][0]:
            return 0.0
        
        distances = results['distances'][0]
        avg_distance = sum(distances) / len(distances)
        return round((1 - avg_distance) * 100, 2)
```

### 4. Interfaz Avanzada con Tabs

```python
# gradio_assistant/advanced_ui.py
import gradio as gr
from app import CyberIntelAssistant

assistant = CyberIntelAssistant()

with gr.Blocks(theme=gr.themes.Base()) as demo:
    gr.Markdown("# 🛡️ Plataforma de Ciberinteligencia - Asistente IA")
    
    with gr.Tabs():
        # Tab 1: Q&A
        with gr.Tab("💬 Preguntas y Respuestas"):
            with gr.Row():
                with gr.Column():
                    question = gr.Textbox(
                        label="Tu pregunta",
                        placeholder="Ej: ¿Qué CVEs críticos hay esta semana?",
                        lines=5
                    )
                    
                    submit = gr.Button("Consultar", variant="primary")
                
                with gr.Column():
                    answer = gr.Markdown(label="Respuesta")
            
            submit.click(
                fn=lambda q: assistant.process_file_and_question(None, q, False),
                inputs=question,
                outputs=answer
            )
        
        # Tab 2: Subir Documentos
        with gr.Tab("📤 Subir Documentos"):
            with gr.Row():
                with gr.Column():
                    file = gr.File(label="Archivo")
                    description = gr.Textbox(
                        label="Descripción (opcional)",
                        placeholder="Ej: Reporte de vulnerabilidades Q4 2024"
                    )
                    upload_btn = gr.Button("Procesar y Agregar", variant="primary")
                
                with gr.Column():
                    upload_status = gr.Markdown(label="Estado")
            
            upload_btn.click(
                fn=lambda f, d: assistant.uploader.process(f),
                inputs=[file, description],
                outputs=upload_status
            )
        
        # Tab 3: Explorar Base de Conocimiento
        with gr.Tab("🗂️ Base de Conocimiento"):
            gr.Markdown("""
            ### Documentos en la Base Vectorial
            
            Aquí puedes explorar todos los documentos almacenados.
            """)
            
            search_query = gr.Textbox(
                label="Buscar documentos",
                placeholder="Ej: NVIDIA vulnerabilities"
            )
            
            search_btn = gr.Button("Buscar")
            results_display = gr.DataFrame(
                headers=["Fuente", "Fragmento", "Confianza"],
                label="Resultados"
            )
            
            def search_knowledge_base(query):
                query_emb = assistant.qa.embedder.embed_query(query)
                results = assistant.vector_store.search(query_emb, n_results=10)
                
                # Formatear para tabla
                data = []
                for doc, meta, dist in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ):
                    data.append([
                        meta.get('source', 'Unknown'),
                        doc[:100] + '...',
                        f"{round((1-dist)*100, 1)}%"
                    ])
                
                return data
            
            search_btn.click(
                fn=search_knowledge_base,
                inputs=search_query,
                outputs=results_display
            )
        
        # Tab 4: Estadísticas
        with gr.Tab("📊 Estadísticas"):
            gr.Markdown("### Métricas de la Plataforma")
            
            with gr.Row():
                total_docs = gr.Number(label="Total Documentos", value=0)
                total_chunks = gr.Number(label="Total Chunks", value=0)
                total_queries = gr.Number(label="Consultas Realizadas", value=0)
            
            refresh_btn = gr.Button("Actualizar Estadísticas")
            
            def get_stats():
                # Implementar consultas a ChromaDB
                collection = assistant.vector_store.collection
                count = collection.count()
                
                return count, count * 3, 0  # Placeholder
            
            refresh_btn.click(
                fn=get_stats,
                outputs=[total_docs, total_chunks, total_queries]
            )

demo.launch(server_port=7860, share=False)
```

## Deployment

### Dockerfile

```dockerfile
# gradio_assistant/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto Gradio
EXPOSE 7860

# Comando de inicio
CMD ["python", "app.py"]
```

### Docker Compose Integration

```yaml
# Agregar a docker-compose.yml
services:
  gradio_assistant:
    build: ./gradio_assistant
    ports:
      - "7860:7860"
    depends_on:
      - ollama
    environment:
      - LLM_PROVIDER=ollama
      - LLM_MODEL=gemma:4b
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./uploads:/app/uploads
```

## Optimizaciones

### Gemma 3 4B Quantization

```bash
# Usar modelo 4-bit quantized para reducir uso de RAM
ollama pull gemma:4b-q4_0

# O 8-bit para mejor calidad
ollama pull gemma:4b-q8_0
```

### Caching de Respuestas

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_answer(question_hash, use_file):
    # Implementación...
    pass

def answer_with_cache(question, use_file):
    q_hash = hashlib.md5(question.encode()).hexdigest()
    return cached_answer(q_hash, use_file)
```

## Testing

```python
# tests/test_gradio_assistant.py
import pytest
from gradio_assistant.app import CyberIntelAssistant

def test_document_upload():
    assistant = CyberIntelAssistant()
    
    # Mock file
    class MockFile:
        name = "test.pdf"
    
    result = assistant.uploader.process(MockFile())
    assert result['status'] == 'success'

def test_qa_basic():
    assistant = CyberIntelAssistant()
    
    answer = assistant.qa.answer("What is CVE-2024-1234?")
    assert len(answer['answer']) > 0
```

## Tips de UX

1. **Feedback visual**: Spinners durante procesamiento
2. **Progreso**: Barra de progreso para uploads grandes
3. **Ejemplos**: Preguntas sugeridas para nuevos usuarios
4. **Historial**: Guardar últimas 10 conversaciones
5. **Export**: Descargar respuestas como Markdown/PDF