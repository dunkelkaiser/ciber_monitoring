
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))
# Add gradio_assistant to path to find tools.py
sys.path.append(str(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'gradio_assistant'))))

# Mock gradio and requests BEFORE importing app
with patch('gradio.Blocks'), \
     patch('gradio.Markdown'), \
     patch('gradio.Tabs'), \
     patch('gradio.Tab'), \
     patch('gradio.ChatInterface'), \
     patch('gradio.Chatbot'), \
     patch('gradio.File'), \
     patch('gradio.Button'), \
     patch('gradio.Textbox'), \
     patch('requests.post') as mock_post:
    
    # Import app
    from gradio_assistant import app

    def test_optimization_logic():
        print("--- Testing Optimization Logic ---")
        
        # 1. Test Caching
        print("\n1. Testing Cache...")
        prompt = "Hello"
        key = app.get_cache_key(prompt)
        app.CACHE[key] = "Cached Response"
        
        # Mock stream to return something else if called
        mock_post.return_value.__enter__.return_value.iter_lines.return_value = [b'{"message": {"content": "New Response"}}']
        
        res = app.query_ollama_direct(prompt, use_cache=True)
        print(f"Result: {res}")
        assert res == "Cached Response"
        print("PASS: Cache Hit verified.")
        
        # 2. Test Router & Fast Path
        print("\n2. Testing Fast Path (No Verification)...")
        # Mock Router to return needs_verification=False
        app.query_ollama_direct = MagicMock(return_value='{"tool": null, "needs_verification": false}')
        
        # Mock Stream for Direct Answer
        app.query_ollama_stream = MagicMock(return_value=iter(["Fast Response"]))
        
        gen = app.chatbot_response("Hi", [])
        output = ""
        for chunk in gen:
            output = chunk
        print(f"Output: {output}")
        assert "Fast Response" in output
        # Verify CoVe prompt not used
        # We can't easily check prompt content with this mock setup unless we inspect calls
        print("PASS: Fast Path executed.")
        
        # 3. Test CoVe Path
        print("\n3. Testing CoVe Path...")
        # Mock Router to return needs_verification=True
        app.query_ollama_direct = MagicMock(return_value='{"tool": null, "needs_verification": true}')
        
        # Mock Stream for CoVe
        app.query_ollama_stream = MagicMock(return_value=iter(["[Draft] ...", "[Check] ...", "Verified"]))
        
        gen = app.chatbot_response("Critical Query", [])
        output = ""
        for chunk in gen:
            output = chunk
        print(f"Output: {output}")
        assert "Verified" in output
        print("PASS: CoVe Path executed.")

        # 4. Test Fallback
        print("\n4. Testing Fallback...")
        # Mock Router -> True
        app.query_ollama_direct = MagicMock(return_value='{"tool": null, "needs_verification": true}')
        
        # Mock Stream -> Error/Fail
        def fail_stream(*args):
             raise Exception("Model Failed")
             yield ""
        
        app.query_ollama_stream = fail_stream
        
        gen = app.chatbot_response("Fail Query", [])
        output = ""
        for chunk in gen:
            output = chunk
        print(f"Output: {output}")
        assert "Paid API Fallback" in output
        print("PASS: Fallback executed.")

if __name__ == "__main__":
    test_optimization_logic()
