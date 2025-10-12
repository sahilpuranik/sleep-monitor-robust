#!/usr/bin/env python3

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailAlertManager:
    def __init__(self):
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS_APP')
        self.alert_to = os.getenv('ALERT_TO')
        
        if not all([self.smtp_user, self.smtp_pass, self.alert_to]):
            logger.warning("Email config incomplete")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Email enabled: {self.alert_to}")
        
        try:
            from llm_utils import LLMAlertEnhancer
            self.llm_enhancer = LLMAlertEnhancer()
        except ImportError:
            logger.warning("No LLM")
            self.llm_enhancer = None
    
    def send_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                          sensor_context: Optional[List[Dict[str, Any]]] = None) -> bool:
        if not self.enabled:
            return False
        
        if not anomalies:
            return False
        
        try:
            subject = f"Sleep Monitor Alert - {len(anomalies)} Anomaly(ies) Detected"
            
            if self.llm_enhancer:
                body = self.llm_enhancer.enhance_anomaly_alert(anomalies, sensor_context)
            else:
                body = self._create_alert_body(anomalies)
            
            success = self._send_email(subject, body)
            
            if success:
                logger.info(f"Sent alert for {len(anomalies)} anomalies")
            
            return success
        except Exception as e:
            logger.error(f"Alert send failed: {e}")
            return False
    
    def send_batch_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                                sensor_context: Optional[List[Dict[str, Any]]] = None) -> bool:
        if not self.enabled or not anomalies:
            return False
        
        try:
            subject = f"Sleep Monitor Night Summary - {len(anomalies)} Anomaly(ies) Detected"
            
            if self.llm_enhancer:
                body = self.llm_enhancer.enhance_batch_anomaly_alert(anomalies, sensor_context)
            else:
                body = self._create_batch_alert_body(anomalies)
            
            success = self._send_email(subject, body)
            
            if success:
                logger.info(f"Sent batch alert")
            
            return success
        except Exception as e:
            logger.error(f"Batch alert failed: {e}")
            return False
    
    def send_no_anomaly_alert(self) -> bool:
        if not self.enabled:
            return False
        
        try:
            subject = "Sleep Monitor Night Summary - No Anomalies Detected"
            body = self._create_no_anomaly_body()
            success = self._send_email(subject, body)
            
            if success:
                logger.info("Sent no-anomaly email")
            
            return success
        except Exception as e:
            logger.error(f"No-anomaly email failed: {e}")
            return False
    
    def _create_alert_body(self, anomalies: List[Dict[str, Any]]) -> str:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        body = f"SLEEP MONITOR ALERT\n\nTime: {current_time}\nAnomalies Detected: {len(anomalies)}\n\n"
        
        for i, anomaly in enumerate(anomalies, 1):
            body += f"{i}. {anomaly['metric'].upper()} ANOMALY\n"
            body += f"   Time: {anomaly['ts_utc']}\n"
            body += f"   Value: {anomaly['value']}\n"
            body += f"   Rule: {anomaly['rule']}\n"
            body += f"   Details: {anomaly['details']}\n\n"
        
        body += "---\nSleep Monitor System"
        return body.strip()
    
    def _create_batch_alert_body(self, anomalies: List[Dict[str, Any]]) -> str:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        body = f"SLEEP MONITOR NIGHT SUMMARY\n\nTime: {current_time}\nTotal Anomalies: {len(anomalies)}\n\n"
        
        for i, anomaly in enumerate(anomalies, 1):
            body += f"{i}. {anomaly['metric'].upper()} ANOMALY\n"
            body += f"   Time: {anomaly['ts_utc']}\n"
            body += f"   Value: {anomaly['value']}\n"
            body += f"   Details: {anomaly['details']}\n\n"
        
        body += "---\nSleep Monitor System"
        return body.strip()
    
    def _create_no_anomaly_body(self) -> str:
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        return f"SLEEP MONITOR NIGHT SUMMARY\n\nTime: {current_time}\nStatus: No anomalies detected\n\n---\nSleep Monitor System"
    
    def _send_email(self, subject: str, body: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_to
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            return True
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP auth failed")
            return False
        except Exception as e:
            logger.error(f"Email error: {e}")
            return False
    
    def test_connection(self) -> bool:
        if not self.enabled:
            return False
        
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                logger.info("SMTP test OK")
                return True
        except Exception as e:
            logger.error(f"SMTP test failed: {e}")
            return False

def send_test_email():
    manager = EmailAlertManager()
    if manager.enabled:
        success = manager._send_email(
            "Sleep Monitor Test",
            "Test email"
        )
        print("Test sent" if success else "Test failed")
    else:
        print("No email config")

if __name__ == "__main__":
    send_test_email()
