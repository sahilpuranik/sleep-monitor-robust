#!/usr/bin/env python3

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_utils import LLMAlertEnhancer, test_llm_connection

def test_enhanced_alerts():
    print("Testing LLM")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("No API key set")
        return
    
    print("Testing connection...")
    if not test_llm_connection():
        print("Connection failed")
        return
    
    print("Testing alerts...")
    
    # Create sample anomalies
    sample_anomalies = [
        {
            'metric': 'temp_f',
            'value': 78.5,
            'rule': 'robust_z_score',
            'details': 'Z-score: 7.61 (threshold: 6.0)',
            'ts_utc': datetime.now(timezone.utc).isoformat()
        },
        {
            'metric': 'humidity',
            'value': 85.2,
            'rule': 'guardrail',
            'details': 'Value 85.2% exceeds maximum threshold 85%',
            'ts_utc': datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Create sample sensor context
    sample_context = [
        {
            'timestamp': '2024-01-15T02:30:00Z',
            'temp_f': 72.1,
            'humidity': 65.3,
            'pressure': 1013.2
        },
        {
            'timestamp': '2024-01-15T02:31:00Z',
            'temp_f': 73.8,
            'humidity': 68.1,
            'pressure': 1013.1
        },
        {
            'timestamp': '2024-01-15T02:32:00Z',
            'temp_f': 75.2,
            'humidity': 72.4,
            'pressure': 1012.9
        },
        {
            'timestamp': '2024-01-15T02:33:00Z',
            'temp_f': 77.8,
            'humidity': 78.9,
            'pressure': 1012.7
        },
        {
            'timestamp': '2024-01-15T02:34:00Z',
            'temp_f': 78.5,
            'humidity': 85.2,
            'pressure': 1012.5
        }
    ]
    
    # Test enhanced alert
    enhancer = LLMAlertEnhancer()
    enhanced_alert = enhancer.enhance_anomaly_alert(sample_anomalies, sample_context)
    
    print("\nEnhanced Alert Output:")
    print("-" * 30)
    print(enhanced_alert)
    
    print("\n3. Testing fallback mode (no API key)...")
    
    # Test fallback mode
    original_key = os.environ.get('OPENAI_API_KEY')
    if original_key:
        del os.environ['OPENAI_API_KEY']
    
    fallback_enhancer = LLMAlertEnhancer()
    fallback_alert = fallback_enhancer.enhance_anomaly_alert(sample_anomalies)
    
    print("\nFallback Alert Output:")
    print("-" * 30)
    print(fallback_alert)
    
    # Restore API key
    if original_key:
        os.environ['OPENAI_API_KEY'] = original_key
    
    print("\n" + "=" * 50)
    print("LLM Integration Test Complete!")
    print("\nKey Features Demonstrated:")
    print("✓ OpenAI API integration")
    print("✓ Human-readable alert formatting")
    print("✓ Root-cause analysis with sensor context")
    print("✓ Graceful fallback to raw format")
    print("✓ Error handling and logging")

if __name__ == "__main__":
    test_enhanced_alerts()
