import requests
import json
import logging

import os

# Configure logger
logger = logging.getLogger("AssistantTools")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

def get_tech_edge_score():
    """Fetches the current Tech Edge Score and innovation ranking."""
    try:
        response = requests.get(f"{API_BASE_URL}/tech-edge-score")
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_vulnerability_index():
    """Fetches the historical vulnerability risk index."""
    try:
        response = requests.get(f"{API_BASE_URL}/vulnerability-index")
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def get_correlation_analysis():
    """Fetches correlation values between social sentiment and risk."""
    try:
        response = requests.get(f"{API_BASE_URL}/correlation/values")
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

AVAILABLE_TOOLS = {
    "tech_edge_score": get_tech_edge_score,
    "vulnerability_index": get_vulnerability_index,
    "correlation_analysis": get_correlation_analysis
}

TOOL_DESCRIPTIONS = """
You have access to the following tools to query real-time data from the CiberMonitoring Platform:

1. `tech_edge_score`: Returns the innovation ranking of recent research papers (0-100 scale). Use this to answer questions about "innovation", "new technologies", or "tech trends".
2. `vulnerability_index`: Returns the historical risk scores based on CVEs. Use this for "risk trends", "vulnerability history", or "threat levels".
3. `correlation_analysis`: Returns statistcal correlations between Social Sentiment (Twitter) and Cyber Risk. Use this for "social impact", "sentiment correlation", or "prediction factors".

To use a tool, respond with a JSON block: {"tool": "tool_name", "parameters": {}}
"""
