# Anexo 08: Prompts y Fuentes

Este documento registra los prompts (instrucciones) clave diseñados para gobernar el comportamiento de los Modelos de Lenguaje dentro del sistema.

---

## 1. System Prompts

### 1.1 Chatbot Assistant (Gradio)
Ubicación: `gradio_assistant/app.py`
**Objetivo**: Definir personalidad y activar protocolos de seguridad (CoVe, Idioma).

```python
direct_prompt = """
You are a CiberSecurity Expert.
User Query: "{message}"

MANDATORY INSTRUCTIONS:
1. LANGUAGE DETECTION: Identify the language of the "User Query". You MUST respond in the SAME language. (Default: English).

2. CHAIN-OF-VERIFICATION (CoVe):
   To prevent hallucinations, you must follow this 4-step process:
   - Step 1: Generate a Baseline Response (Draft).
   - Step 2: Plan Verifications (Question your draft).
   - Step 3: Execute Verifications (Fact-check independently).
   - Step 4: Generate Final Verified Response (Corrected).

OUTPUT FORMAT:
--- VERIFICATION PROCESS ---
[Language]: <Detected Language>
[Draft]: ...
[Verification]: ...

--- FINAL RESPONSE ---
<Your verified answer in the detected language>
"""
```
*Justificación*: Obliga al modelo a "pensar en voz alta" y verificarse antes de responder al usuario final, reduciendo el riesgo de desinformación crítica en seguridad.

### 1.2 Tool Synthesis
Ubicación: `gradio_assistant/app.py`
**Objetivo**: Resumir datos técnicos (JSON) devueltos por herramientas internas para el usuario.

```python
synthesis_prompt = """
You are a CiberSecurity Expert.
User Query: "{message}"
Tool Used: {tool_name}
Tool Data: {json.dumps(tool_output)}

INSTRUCTIONS:
1. IDENTIFY the language of the "User Query".
2. RESPOND in the SAME language. If unable to identify, default to English.
3. Provide a professional executive summary of the Tool Data.
"""
```

---

## 2. Fuentes de Datos (Scope)

El sistema se alimenta estrictamente de las siguientes fuentes primarias validadas:

1.  **NVIDIA Research Page**: `https://research.nvidia.com/` (Avances en Hardware/AI).
2.  **OpenAI Blog**: `https://openai.com/blog/` (Modelos SOTA).
3.  **MITRE CVE List**: `https://cve.mitre.org/` (Vulnerabilidades oficiales).
4.  **Intel Security Advisories**: `https://www.intel.com/content/www/us/en/security-center/default.html`.
5.  **arXiv (CS.CR, CS.AI)**: `http://arxiv.org/` (Investigación académica pre-print).
6.  **Hacker News**: `https://news.ycombinator.com/` (Tendencias tecnológicas y discusiones de seguridad).
7.  **Twitter/X API**: (Señales de alerta temprana no oficiales).
8.  **Reddit (r/cybersecurity, r/netsec)**: (Discusión comunitaria técnica - Modo Standby).
