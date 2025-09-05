# Enhanced Alert Example

This document shows how the LLM-enhanced alerts transform raw anomaly data into human-readable explanations.

## Before (Raw Format)

```
SLEEP MONITOR ALERT

Time: 2024-01-15 02:34:15 UTC
Anomalies Detected: 2

1. TEMP_F ANOMALY
   Time: 2024-01-15T02:34:15Z
   Value: 78.5
   Rule: robust_z_score
   Details: Z-score: 7.61 (threshold: 6.0)

2. HUMIDITY ANOMALY
   Time: 2024-01-15T02:34:15Z
   Value: 85.2
   Rule: guardrail
   Details: Value 85.2% exceeds maximum threshold 85%

---
Sleep Monitor System
Raspberry Pi Environment Monitor
This is an automated alert - please check your sleep environment.
```

## After (LLM-Enhanced Format)

```
SLEEP MONITOR ALERT

Time: 2024-01-15 02:34:15 UTC

AI ANALYSIS:
Your sleep environment has experienced significant changes that may affect your rest quality.

**Temperature Spike**: Your room temperature has risen to 78.5°F, which is unusually high compared to your normal baseline. This could indicate your heating system has activated or a window was opened, allowing warm air to enter.

**High Humidity**: Humidity levels have reached 85.2%, exceeding the recommended maximum. This suggests increased moisture in the air, possibly from:
- A humidifier running too high
- Poor ventilation
- Weather changes affecting indoor conditions

**Recommended Actions**:
1. Check if your heating system is running unnecessarily
2. Ensure windows and doors are properly closed
3. Consider adjusting your humidifier settings
4. Verify your room's ventilation is adequate

These conditions may lead to discomfort and disrupted sleep. Monitor the situation and take corrective action as needed.

---
Sleep Monitor System
Raspberry Pi Environment Monitor
This is an automated alert - please check your sleep environment.
```

## Key Improvements

1. **Human-Readable Language**: Technical terms like "robust z-score" and "guardrail" are explained in plain English
2. **Root-Cause Analysis**: The system analyzes sensor trends to suggest possible causes
3. **Actionable Recommendations**: Specific steps the user can take to address the issues
4. **Context Awareness**: Uses recent sensor data to understand the progression of environmental changes
5. **Health Focus**: Emphasizes the impact on sleep quality and comfort

## Technical Implementation

- Uses OpenAI GPT-3.5-turbo for natural language generation
- Analyzes last 5 minutes of sensor data for context
- Gracefully falls back to raw format if API is unavailable
- Maintains all original functionality while adding intelligence
- Production-safe with comprehensive error handling
