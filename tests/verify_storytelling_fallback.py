
import sys
import os
import pandas as pd
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parents[1]))

from user_interface.dashboards import storytelling_generator

def test_fallback_logic():
    print("--- Testing Multi-Model Fallback ---")
    
    # Mock Data
    mock_risk = {"count": 50}
    mock_innov = {"score": 85}
    mock_context = "Context info."
    
    # 1. Test Gemini Success
    print("\n[Case 1] Gemini Success")
    with patch('requests.post') as mock_post:
        # Mock Gemini Success
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{'content': {'parts': [{'text': 'Gemini Insight'}]}}]
        }
        mock_post.return_value = mock_response
        
        # Inject API Key for test
        storytelling_generator.GOOGLE_API_KEY = "test_key"
        
        result = storytelling_generator.generate_insight_with_fallback(mock_risk, mock_innov, mock_context)
        print(f"Result: {result}")
        assert "[Gemini]" in result
        
    # 2. Test Gemini Fail -> OpenAI Success
    print("\n[Case 2] Gemini Fail -> OpenAI Success")
    with patch('requests.post') as mock_post:
        def side_effect(*args, **kwargs):
            url = args[0]
            if "googleapis" in url:
                # Gemini Fail
                r = MagicMock()
                r.status_code = 500
                r.text = "Error"
                return r
            elif "openai" in url:
                # OpenAI Success
                r = MagicMock()
                r.status_code = 200
                r.json.return_value = {
                    'choices': [{'message': {'content': 'OpenAI Insight'}}]
                }
                return r
            return MagicMock()
            
        mock_post.side_effect = side_effect
        
        storytelling_generator.GOOGLE_API_KEY = "test_key"
        storytelling_generator.OPENAI_API_KEY = "test_key"
        
        result = storytelling_generator.generate_insight_with_fallback(mock_risk, mock_innov, mock_context)
        print(f"Result: {result}")
        assert "[OpenAI]" in result

    # 3. Test Gemini Fail -> OpenAI Fail -> Claude Success
    print("\n[Case 3] Gemini & OpenAI Fail -> Claude Success")
    with patch('requests.post') as mock_post:
        def side_effect(*args, **kwargs):
            url = args[0]
            if "googleapis" in url or "openai" in url:
                r = MagicMock()
                r.status_code = 500
                return r
            elif "anthropic" in url:
                r = MagicMock()
                r.status_code = 200
                r.json.return_value = {
                    'content': [{'text': 'Claude Insight'}]
                }
                return r
            return MagicMock()
            
        mock_post.side_effect = side_effect
        
        storytelling_generator.GOOGLE_API_KEY = "test_key"
        storytelling_generator.OPENAI_API_KEY = "test_key"
        storytelling_generator.ANTHROPIC_API_KEY = "test_key"
        
        result = storytelling_generator.generate_insight_with_fallback(mock_risk, mock_innov, mock_context)
        print(f"Result: {result}")
        assert "[Claude]" in result

def test_history_logic():
    print("\n--- Testing History Logic ---")
    
    # Mock dependencies
    # 1. Mock API Data fetch
    with patch('user_interface.dashboards.storytelling_generator.get_api_metric') as mock_get:
        mock_get.return_value = {"count": 10, "score": 20}
        
        # 2. Mock RAG
        with patch('user_interface.dashboards.storytelling_generator.get_rag_context') as mock_rag:
            mock_rag.return_value = "context"
            
            # 3. Mock Insight Gen
            with patch('user_interface.dashboards.storytelling_generator.generate_insight_with_fallback') as mock_gen:
                mock_gen.return_value = "Test Insight Today"
                
                # Run Logic
                # Ensure we use a temp file for history to not mess up real gold
                temp_gold = Path("tests/temp_gold_history.parquet")
                storytelling_generator.HISTORY_FILE = temp_gold
                
                if temp_gold.exists(): os.remove(temp_gold)
                
                # Run 1
                print("Running Day 1...")
                df_day1 = storytelling_generator.run_storytelling()
                
                assert len(df_day1) == 1
                print("Day 1 Output Rows:", len(df_day1))
                
                # Check model_used presence
                assert 'model_used' in df_day1.columns
                print(f"Model used: {df_day1.iloc[0]['model_used']}")
                assert df_day1.iloc[0]['model_used'] is not None

                # Check persistence
                assert temp_gold.exists()
                df_disk = pd.read_parquet(temp_gold)
                assert len(df_disk) == 1
                assert 'model_used' in df_disk.columns
                
                # Run 2 (Same Day - Should Replace/Update)
                # Script logic: "if today in history: skip/log" -> returns ???
                # Wait, looking at script: 
                # "if not df_history.empty ... and today in ...: logger.info... "
                # It does NOT append if today exists.
                # Let's verify behavior.
                
                print("Running Day 1 Again (Idempotency)...")
                df_day1_again = storytelling_generator.run_storytelling()
                
                # If it didn't append, it returns the existing history? 
                # Code: "return df_history" (which is read from disk).
                # But wait, the code says "Return Only Today's Insight".
                # Let's check the code replacement carefully.
                
                # In the replaced code:
                # if today exists: df_history = df_history[df_history['date'] != today_str] (Drop old)
                # then append new.
                # then save.
                # then return new.
                
                # So it SHOULD return 1 row (the new one).
                assert len(df_day1_again) == 1
                print("Day 1 Again Output Rows:", len(df_day1_again))
                
                if temp_gold.exists(): os.remove(temp_gold)
                print("History Logic Verified.")

if __name__ == "__main__":
    try:
        test_fallback_logic()
        test_history_logic()
        print("\nALL TESTS PASSED.")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
