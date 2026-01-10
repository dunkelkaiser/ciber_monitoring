import gradio as gr
import json
import logging
import requests
import os
import sys

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GradioBot")

logger.info("Starting Gradio App Initialization...")

try:
    from tools import AVAILABLE_TOOLS, TOOL_DESCRIPTIONS
    # Lazy import of uploader to prevent import-time crashes
    # from document_uploader import DocumentProcessor 
except Exception as e:
    logger.error(f"Import Error: {e}")
    sys.exit(1)

# LLM Config (Ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = "gemma3:4b"

# Global lazy instance
_uploader_instance = None

def get_uploader():
    global _uploader_instance
    if _uploader_instance is None:
        try:
            logger.info("Initializing DocumentProcessor...")
            from document_uploader import DocumentProcessor
            _uploader_instance = DocumentProcessor()
            logger.info("DocumentProcessor Initialized.")
        except Exception as e:
            logger.error(f"Failed to init DocumentProcessor: {e}")
            return None
    return _uploader_instance

# CSS
custom_css = """
body { font-family: 'Arial', sans-serif; background-color: #f0f2f5; }
.gradio-container { max-width: 1200px; margin: 0 auto; }
"""

def query_ollama_stream(prompt):
    chat_url = OLLAMA_URL.replace("/api/generate", "/api/chat")
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {"temperature": 0.3}
        }
        with requests.post(chat_url, json=payload, stream=True) as res:
            res.raise_for_status()
            for line in res.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        yield f"[Error: {e}]"

def query_ollama_direct(prompt):
    full_response = ""
    for chunk in query_ollama_stream(prompt):
        full_response += chunk
    return full_response

def chatbot_response(message, history):
    decision_prompt = f"""
    You are a CiberSecurity Expert Assistant.
    User Query: "{message}"
    {TOOL_DESCRIPTIONS}
    Analyze the query. If it requires real-time data from the platform/tools, reply ONLY with the JSON tool call.
    If it is general knowledge or conversation, reply with "DIRECT_ANSWER".
    """
    
    decision = query_ollama_direct(decision_prompt).strip()
    tool_output = None
    
    if "{" in decision and "}" in decision and '"tool":' in decision:
        try:
            start = decision.find("{")
            end = decision.rfind("}") + 1
            json_str = decision[start:end]
            tool_call = json.loads(json_str)
            tool_name = tool_call.get("tool")
            
            if tool_name in AVAILABLE_TOOLS:
                tool_output = AVAILABLE_TOOLS[tool_name]()
                logger.info(f"Tool {tool_name} executed.")
                
                synthesis_prompt = f"""
                You are a CiberSecurity Expert.
                User Query: "{message}"
                Tool Used: {tool_name}
                Tool Data: {json.dumps(tool_output)}
                Provide a professional executive summary.
                """
                partial = ""
                for chunk in query_ollama_stream(synthesis_prompt):
                    partial += chunk
                    yield partial
                return 
            else:
                 yield "Tool not found."
        except Exception:
             pass

    direct_prompt = f"You are a CiberSecurity Expert. Answer nicely: {message}"
    partial = ""
    for chunk in query_ollama_stream(direct_prompt):
        partial += chunk
        yield partial

def handle_upload(files):
    proc = get_uploader()
    if not proc:
        return "System Error: Uploader not available."
    if not files:
        return "No files selected."
    
    results = []
    if not isinstance(files, list):
        files = [files]
        
    for f in files:
        if f is None: continue
        path = f.name if hasattr(f, 'name') else f
        res = proc.process_file(path)
        results.append(res)
    
    return "\n".join(results)

logger.info("Building Gradio UI...")
with gr.Blocks(css=custom_css, theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🛡️ CiberMonitoring AI Platform")
    
    with gr.Tabs():
        with gr.Tab("💬 Assistant"):
            gr.ChatInterface(
                fn=chatbot_response,
                chatbot=gr.Chatbot(height=500),
                description="Gemma 3 Expert Agent",
                examples=["What is the Tech Edge Score?", "Summarize latest CVEs."]
            )
            
        with gr.Tab("📂 Upload"):
            gr.Markdown("### Knowledge Base Ingestion")
            file_in = gr.File(label="Documents", file_count="multiple", type="filepath")
            btn = gr.Button("Process", variant="primary")
            out = gr.Textbox(label="Log")
            btn.click(handle_upload, file_in, out)

if __name__ == "__main__":
    logger.info("Launching Server...")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=True)
