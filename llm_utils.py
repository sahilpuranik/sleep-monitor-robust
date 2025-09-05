#!/usr/bin/env python3
"""
LLM utilities for Sleep Monitor
Handles OpenAI API integration for human-readable alerts and root-cause analysis
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMAlertEnhancer:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("OpenAI API key not found. Alerts will use raw format.")
        else:
            logger.info("OpenAI integration enabled for enhanced alerts")
    
    def enhance_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                            sensor_context: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Generate human-readable explanation for anomalies using OpenAI API
        Returns enhanced alert text or falls back to raw format if API fails
        """
        if not self.enabled or not anomalies:
            return self._fallback_alert_format(anomalies)
        
        try:
            # Prepare context for LLM
            context = self._prepare_context(anomalies, sensor_context)
            
            # Generate explanation
            explanation = self._call_openai_api(context)
            
            return explanation
            
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            return self._fallback_alert_format(anomalies)
    
    def _prepare_context(self, anomalies: List[Dict[str, Any]], 
                        sensor_context: Optional[List[Dict[str, Any]]]) -> str:
        """Prepare context string for OpenAI API"""
        
        # Basic anomaly information
        context = "Sleep environment anomalies detected:\n\n"
        
        for i, anomaly in enumerate(anomalies, 1):
            context += f"{i}. {anomaly['metric'].upper()}: {anomaly['value']} "
            context += f"(Rule: {anomaly['rule']}, Details: {anomaly['details']})\n"
        
        # Add sensor context if available
        if sensor_context:
            context += "\nRecent sensor readings (last 5 minutes):\n"
            for reading in sensor_context[-10:]:  # Last 10 readings
                context += f"  {reading['timestamp']}: Temp {reading['temp_f']:.1f}°F, "
                context += f"Humidity {reading['humidity']:.1f}%, "
                context += f"Pressure {reading['pressure']:.1f}hPa\n"
        
        return context
    
    def _call_openai_api(self, context: str) -> str:
        """Call OpenAI API to generate human-readable explanation"""
        try:
            import openai
            
            # Set API key
            openai.api_key = self.api_key
            
            # Create prompt
            prompt = f"""
You are a sleep environment monitoring system. Analyze the following anomaly data and provide a clear, concise explanation for the user.

{context}

Provide:
1. A brief summary of what's happening
2. Possible causes for each anomaly
3. Suggested actions if any

Keep the response under 200 words, use simple language, and focus on practical insights. Do not include technical jargon or statistical details.
"""
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful sleep environment monitoring assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            explanation = response.choices[0].message.content.strip()
            
            # Format the explanation
            return self._format_enhanced_alert(explanation)
            
        except ImportError:
            logger.error("OpenAI library not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise
    
    def _format_enhanced_alert(self, explanation: str) -> str:
        """Format the LLM explanation into alert structure"""
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        formatted_alert = f"""
SLEEP MONITOR ALERT

Time: {current_time}

AI ANALYSIS:
{explanation}

---
Sleep Monitor System
Raspberry Pi Environment Monitor
This is an automated alert - please check your sleep environment.
"""
        
        return formatted_alert.strip()
    
    def _fallback_alert_format(self, anomalies: List[Dict[str, Any]]) -> str:
        """Fallback to raw anomaly format if LLM is unavailable"""
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        body = f"""
SLEEP MONITOR ALERT

Time: {current_time}
Anomalies Detected: {len(anomalies)}

"""
        
        for i, anomaly in enumerate(anomalies, 1):
            body += f"""
{i}. {anomaly['metric'].upper()} ANOMALY
   Time: {anomaly['ts_utc']}
   Value: {anomaly['value']}
   Rule: {anomaly['rule']}
   Details: {anomaly['details']}
"""
        
        body += f"""

---
Sleep Monitor System
Raspberry Pi Environment Monitor
This is an automated alert - please check your sleep environment.
"""
        
        return body.strip()

def test_llm_connection() -> bool:
    """Test OpenAI API connection"""
    enhancer = LLMAlertEnhancer()
    
    if not enhancer.enabled:
        print("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
        return False
    
    try:
        # Test with sample data
        test_anomalies = [
            {
                'metric': 'temp_f',
                'value': 75.2,
                'rule': 'robust_z_score',
                'details': 'Z-score: 7.61',
                'ts_utc': datetime.utcnow().isoformat()
            }
        ]
        
        result = enhancer.enhance_anomaly_alert(test_anomalies)
        
        if "AI ANALYSIS:" in result:
            print("OpenAI integration test successful!")
            print("\nSample enhanced alert:")
            print(result)
            return True
        else:
            print("OpenAI integration test failed - fallback format used")
            return False
            
    except Exception as e:
        print(f"OpenAI integration test failed: {e}")
        return False

if __name__ == "__main__":
    # Test LLM functionality
    test_llm_connection()
