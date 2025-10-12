#!/usr/bin/env python3

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
            logger.warning("No API key found")
        else:
            logger.info("OpenAI enabled")
    
    def enhance_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                            sensor_context: Optional[List[Dict[str, Any]]] = None) -> str:
        if not self.enabled or not anomalies:
            return self._fallback_alert_format(anomalies)
        
        try:
            context = self._prepare_context(anomalies, sensor_context)
            explanation = self._call_openai_api(context)
            return explanation
        except Exception as e:
            logger.error(f"LLM failed: {e}")
            return self._fallback_alert_format(anomalies)
    
    def enhance_batch_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                                   sensor_context: Optional[List[Dict[str, Any]]] = None) -> str:
        if not self.enabled or not anomalies:
            return self._fallback_batch_alert_format(anomalies)
        
        try:
            context = self._prepare_batch_context(anomalies, sensor_context)
            explanation = self._call_openai_api(context)
            return explanation
        except Exception as e:
            logger.error(f"Batch LLM failed: {e}")
            return self._fallback_batch_alert_format(anomalies)
    
    def _prepare_context(self, anomalies: List[Dict[str, Any]], 
                        sensor_context: Optional[List[Dict[str, Any]]]) -> str:
        from datetime import datetime as dt
        
        context = "Sleep environment anomalies detected:\n\n"
        
        for i, anomaly in enumerate(anomalies, 1):
            try:
                ts = dt.fromisoformat(anomaly['ts_utc'])
                time_str = ts.strftime('%I:%M:%S %p PST')
            except:
                time_str = anomaly.get('ts_utc', 'Unknown time')
            
            context += f"{i}. [{time_str}] {anomaly['metric'].upper()}: {anomaly['value']} "
            context += f"(Rule: {anomaly['rule']}, Details: {anomaly['details']})\n"
        
        if sensor_context:
            context += "\nRecent sensor readings:\n"
            for reading in sensor_context[-10:]:
                context += f"  {reading['timestamp']}: Temp {reading['temp_f']:.1f}°F, "
                context += f"Humidity {reading['humidity']:.1f}%, "
                context += f"Pressure {reading['pressure']:.1f}hPa\n"
        
        return context
    
    def _prepare_batch_context(self, anomalies: List[Dict[str, Any]], 
                              sensor_context: Optional[List[Dict[str, Any]]]) -> str:
        from datetime import datetime as dt
        
        context = f"Sleep environment monitoring session completed with {len(anomalies)} total anomalies detected:\n\n"
        
        for i, anomaly in enumerate(anomalies, 1):
            try:
                ts = dt.fromisoformat(anomaly['ts_utc'])
                time_str = ts.strftime('%I:%M:%S %p PST')
            except:
                time_str = anomaly.get('ts_utc', 'Unknown time')
            
            context += f"{i}. [{time_str}] {anomaly['metric'].upper()}: {anomaly['value']} "
            context += f"(Rule: {anomaly['rule']}, Details: {anomaly['details']})\n"
        
        if sensor_context:
            context += "\nRecent sensor readings:\n"
            for reading in sensor_context[-10:]:
                context += f"  {reading['timestamp']}: Temp {reading['temp_f']:.1f}°F, "
                context += f"Humidity {reading['humidity']:.1f}%, "
                context += f"Pressure {reading['pressure']:.1f}hPa\n"
        
        return context
    
    def _call_openai_api(self, context: str) -> str:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            if "monitoring session completed" in context:
                prompt = f"""
You are a sleep environment monitoring system. Analyze the following night's monitoring session and provide a clear, concise summary for the user.

ROOM CONTEXT:
- User lives near a major road, so noise levels can be high from traffic
- Light comes through the window a little bit even when blinds are completely closed
- AC is not allowed, but user has a fan available for temperature control

{context}

Format your response EXACTLY like this for each anomaly:

1. [TIME] - [What happened]
   Potential cause: [explain why this happened, considering room context]
   Potential fix: [suggest solution, remember: no AC, but fan is available]

2. [TIME] - [What happened]
   Potential cause: [explain why this happened, considering room context]
   Potential fix: [suggest solution]

Keep each explanation brief and practical. Use simple language. No technical jargon.
"""
            else:
                prompt = f"""
You are a sleep environment monitoring system. Analyze the following anomaly data and provide a clear, concise explanation for the user.

ROOM CONTEXT:
- User lives near a major road, so noise levels can be high from traffic
- Light comes through the window a little bit even when blinds are completely closed
- AC is not allowed, but user has a fan available for temperature control

{context}

Format your response EXACTLY like this for each anomaly:

1. [TIME] - [What happened]
   Potential cause: [explain why this happened, considering room context]
   Potential fix: [suggest solution, remember: no AC, but fan is available]

2. [TIME] - [What happened]
   Potential cause: [explain why this happened, considering room context]
   Potential fix: [suggest solution]

Keep each explanation brief and practical. Use simple language. No technical jargon.
"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful sleep environment monitoring assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            explanation = response.choices[0].message.content.strip()
            return self._format_enhanced_alert(explanation)
            
        except ImportError:
            logger.error("OpenAI not installed")
            raise
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
    
    def _format_enhanced_alert(self, explanation: str) -> str:
        from datetime import timezone, timedelta
        pst = timezone(timedelta(hours=-8))
        current_time = datetime.now(pst).strftime("%Y-%m-%d %H:%M:%S PST")
        
        return f"""SLEEP MONITOR ALERT

Time: {current_time}

AI ANALYSIS:
{explanation}

---
Sleep Monitor System
""".strip()
    
    def _fallback_alert_format(self, anomalies: List[Dict[str, Any]]) -> str:
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
        
        body += "\n---\nSleep Monitor System"
        return body.strip()
    
    def _fallback_batch_alert_format(self, anomalies: List[Dict[str, Any]]) -> str:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        body = f"""
SLEEP MONITOR NIGHT SUMMARY

Time: {current_time}
Total Anomalies Detected: {len(anomalies)}

"""
        
        for i, anomaly in enumerate(anomalies, 1):
            body += f"""
{i}. {anomaly['metric'].upper()} ANOMALY
   Time: {anomaly['ts_utc']}
   Value: {anomaly['value']}
   Rule: {anomaly['rule']}
   Details: {anomaly['details']}
"""
        
        body += "\n---\nSleep Monitor System"
        return body.strip()

def test_llm_connection() -> bool:
    enhancer = LLMAlertEnhancer()
    
    if not enhancer.enabled:
        print("No API key set")
        return False
    
    try:
        test_anomalies = [{
            'metric': 'temp_f',
            'value': 75.2,
            'rule': 'robust_z_score',
            'details': 'Z-score: 7.61',
            'ts_utc': datetime.utcnow().isoformat()
        }]
        
        result = enhancer.enhance_anomaly_alert(test_anomalies)
        
        if "AI ANALYSIS:" in result:
            print("Test successful")
            print(result)
            return True
        else:
            print("Test failed")
            return False
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    test_llm_connection()
