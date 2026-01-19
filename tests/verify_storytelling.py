
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))))

def test_storytelling():
    print("--- Testing Storytelling Generator ---")
    
    # Mock requests to skip API call
    with patch('requests.get') as mock_get:
        # Mock Metrics
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: [{'count': 100}]), # Vulnerability
            MagicMock(status_code=200, json=lambda: [{'score': 88}])  # Tech Edge
        ]
        
        # Mock RAG (Load of Chroma) to skip DB dependency
        with patch('langchain_chroma.Chroma') as mock_chroma, \
             patch('langchain_huggingface.HuggingFaceEmbeddings'):
            
            # Mock DB search
            mock_db = MagicMock()
            mock_db.similarity_search.return_value = [] # Empty docs
            mock_chroma.return_value = mock_db
            
            # Import script AFTER mocking
            # We need to use exec/import to run the script because it executes logic at toplevel
            
            script_path = os.path.join(os.path.dirname(__file__), '../user_interface/dashboards/storytelling_generator.py')
            
            # Run the script in a separate namespace
            global_vars = {}
            with open(script_path, 'r') as f:
                code = f.read()
            
            try:
                exec(code, global_vars)
                
                # Check results in global_vars
                insight_history = global_vars.get('insight_history')
                current_insight = global_vars.get('current_insight')
                
                print(f"Insight History Generated: {type(insight_history)}")
                print(f"Current Insight Generated: {type(current_insight)}")
                
                assert isinstance(insight_history, pd.DataFrame)
                assert isinstance(current_insight, pd.DataFrame)
                assert not current_insight.empty
                print(f"Current Row: {current_insight.iloc[0].to_dict()}")
                
                print("PASS: Dataframes generated.")
                
            except Exception as e:
                print(f"FAIL: Script execution error: {e}")
                raise

if __name__ == "__main__":
    test_storytelling()
