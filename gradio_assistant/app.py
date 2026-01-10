import gradio as gr
import json
import logging
import requests
from tools import AVAILABLE_TOOLS, TOOL_DESCRIPTIONS

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GradioBot")

# LLM Config (Ollama)
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma:4b"  # User specified "Gemma 3", mapping to available tag or custom

# CSS (Provided by User)
custom_css = """
body {
    font-family: 'Arial', sans-serif;
    background-color: #f0f2f5;
}
.gradio-container {
    max-width: 1200px;
    margin: 30px auto;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    border-radius: 10px;
    overflow: hidden;
}
.gradio-column {
    padding: 20px;
    background-color: #ffffff;
    border-radius: 8px;
}
.gradio-column:first-child {
    border-right: 1px solid #e0e0e0;
}
.gradio-chatbot {
    height: 500px !important;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 10px;
    background-color: #f9f9f9;
}
.gradio-markdown {
    background-color: #f9f9f9;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 15px;
    min-height: 500px;
}
h3 {
    color: #333;
    border-bottom: 2px solid #4CAF50;
    padding-bottom: 5px;
    margin-bottom: 20px;
}
"""

def query_ollama(prompt):
    """Raw call to Ollama."""
    try:
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3}
        }
        res = requests.post(OLLAMA_URL, json=payload)
        if res.status_code == 200:
            return res.json().get("response", "")
        return f"Error: {res.text}"
    except Exception as e:
        return f"Connection Failed: {e}"

def chatbot_response(message, history):
    history = history or []
    
    # 1. Decision Step (Tool Use?)
    decision_prompt = f"""
    You are a CiberSecurity Expert Assistant.
    User Query: "{message}"
    
    {TOOL_DESCRIPTIONS}
    
    Analyze the query. If it requires real-time data from the platform/tools, reply ONLY with the JSON tool call.
    If it is general knowledge or conversation, reply with "DIRECT_ANSWER".
    """
    
    decision = query_ollama(decision_prompt).strip()
    
    tool_output = None
    final_answer = ""
    
    # Check for JSON tool call
    if "{" in decision and "}" in decision and '"tool":' in decision:
        try:
            # Extract JSON
            start = decision.find("{")
            end = decision.rfind("}") + 1
            json_str = decision[start:end]
            tool_call = json.loads(json_str)
            tool_name = tool_call.get("tool")
            
            if tool_name in AVAILABLE_TOOLS:
                tool_output = AVAILABLE_TOOLS[tool_name]()
                logger.info(f"Tool {tool_name} returned: {str(tool_output)[:100]}...")
                
                # 2. Synthesis Step
                synthesis_prompt = f"""
                You are a CiberSecurity Expert.
                User Query: "{message}"
                Tool Used: {tool_name}
                Tool Data: {json.dumps(tool_output)}
                
                Provide a professional executive summary answering the user's question based on the tool data.
                """
                final_answer = query_ollama(synthesis_prompt)
            else:
                final_answer = "I calculated the tool call but the function is not implemented."
        except Exception as e:
            logger.error(f"Tool parse error: {e}")
            final_answer = query_ollama(f"Answer this query directly: {message}")
    else:
        # Direct Answer
        final_answer = query_ollama(f"You are a CiberSecurity Expert. Answer nicely: {message}")

    history.append((message, final_answer))
    return history, history

with gr.Blocks(css=custom_css, theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🛡️ CiberMonitoring AI Assistant (Gemma 3)")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🛠️ Config & Tools")
            gr.Markdown("""
            **Active Model**: Gemma 3 4B
            **Capabilities**:
            - 📈 **Tech Edge Score**: Analyzes Innovation.
            - 🛡️ **Risk Index**: Historical CVE Data.
            - 🔗 **Correlations**: Social vs Risk.
            """)
            
            manual_tool_btn = gr.Button("Force Refresh Metrics")
            status_box = gr.JSON(label="System Status", value={"api": "online", "rag": "ready"})

        with gr.Column(scale=2):
            gr.Markdown("### 💬 Secure Chat Ops")
            chatbot = gr.Chatbot(label="Agent Session")
            msg = gr.Textbox(
                label="Command Center",
                placeholder="Ask about risks, trends, or specific CVEs...",
                autofocus=True
            )
            clear = gr.Button("Clear Context")

    msg.submit(chatbot_response, [msg, chatbot], [chatbot, chatbot])
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
