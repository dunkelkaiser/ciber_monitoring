
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path
import json

# Add project root to sys.path
sys.path.append(str(Path(__file__).parents[1]))

from api_gateway import main as api_app

def test_api_endpoint_history():
    print("--- Testing API Endpoint: /api/v1/storytelling-history ---")
    
    # Mock Gold Directory and File
    mock_gold_dir = Path("tests/mock_gold")
    mock_file = mock_gold_dir / "gold_storytelling_history.parquet"
    
    # Setup Mock Environment
    with patch('api_gateway.main.GOLD_DIR', mock_gold_dir):
        if not mock_gold_dir.exists(): mock_gold_dir.mkdir()
        
        # 1. Test 404/Empty (File not found)
        # Note: The code raises 404 if file missing.
        print("\n[Case 1] File Missing -> 404")
        if mock_file.exists(): os.remove(mock_file)
        
        try:
            api_app.get_storytelling_history()
            print("FAIL: Should have raised exception")
        except Exception as e:
            print(f"PASS: Raised expected exception: {e}")
            
        # 2. Test Success
        print("\n[Case 2] File Exists -> Return JSON")
        # Create dummy parquet
        df = pd.DataFrame([
            {"date": "2026-01-01", "insight": "Test Insight", "model_used": "gemini-test"}
        ])
        df.to_parquet(mock_file)
        
        result = api_app.get_storytelling_history()
        print(f"Result: {result}")
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['model_used'] == "gemini-test"
        
        print("PASS: API Logic correct.")
        
        # Cleanup
        if mock_file.exists(): os.remove(mock_file)
        if mock_gold_dir.exists(): mock_gold_dir.rmdir()

if __name__ == "__main__":
    try:
        test_api_endpoint_history()
        print("\nALL API TESTS PASSED.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
