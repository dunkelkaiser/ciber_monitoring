import gradio as gr
import json
import logging
import requests
from tools import AVAILABLE_TOOLS, TOOL_DESCRIPTIONS

import os

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GradioBot")

# LLM Config (Ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = "gemma3:4b"  # Updated to verified model name

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
    """Raw call to Ollama via /api/chat."""
    # Ensure URL points to /api/chat
    chat_url = OLLAMA_URL.replace("/api/generate", "/api/chat")
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.3}
        }
        res = requests.post(chat_url, json=payload)
        if res.status_code == 200:
            return res.json().get("message", {}).get("content", "")
        return f"Error: {res.text}"
    except Exception as e:
        return f"Connection Failed: {e}"

def chatbot_response(message, history):
    # History is managed by ChatInterface, but for independent logic we use message
    
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

    return final_answer


# Create Chat Interface
chat_interface = gr.ChatInterface(
    fn=chatbot_response,
    chatbot=gr.Chatbot(height=500),
    title="🛡️ CiberMonitoring AI Assistant (Gemma 3)",
    description="Ask about risks, trends, or specific CVEs... (Capabilities: Tech Edge Score, Risk Index, Correlations)",
    examples=["What is the current Tech Edge Score?", "Show me the vulnerability risk index.", "Is there a correlation between tweets and CVEs?"]
)

if __name__ == "__main__":
    chat_interface.launch(server_name="0.0.0.0", server_port=7860)


