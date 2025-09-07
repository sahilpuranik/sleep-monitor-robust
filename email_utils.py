#!/usr/bin/env python3
"""
Email utilities for Sleep Monitor
Handles SMTP email alerts for anomaly detection
"""

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
            logger.warning("Email configuration incomplete. Alerts will not be sent.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"Email alerts configured for: {self.alert_to}")
        
        # Initialize LLM enhancer
        try:
            from llm_utils import LLMAlertEnhancer
            self.llm_enhancer = LLMAlertEnhancer()
        except ImportError:
            logger.warning("LLM utilities not available. Alerts will use raw format.")
            self.llm_enhancer = None
    
    def send_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                          sensor_context: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Send email alert for detected anomalies with optional LLM enhancement
        Returns True if email was sent successfully
        """
        if not self.enabled:
            logger.warning("Email alerts disabled - skipping alert")
            return False
        
        if not anomalies:
            logger.info("No anomalies to alert about")
            return False
        
        try:
            # Create email content
            subject = f"Sleep Monitor Alert - {len(anomalies)} Anomaly(ies) Detected"
            
            # Use LLM enhancement if available
            if self.llm_enhancer:
                body = self.llm_enhancer.enhance_anomaly_alert(anomalies, sensor_context)
            else:
                body = self._create_alert_body(anomalies)
            
            # Send email
            success = self._send_email(subject, body)
            
            if success:
                logger.info(f"Alert email sent successfully for {len(anomalies)} anomalies")
            else:
                logger.error("Failed to send alert email")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending alert email: {e}")
            return False
    
    def send_batch_anomaly_alert(self, anomalies: List[Dict[str, Any]], 
                                sensor_context: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Send batch email alert for all anomalies collected during session
        Returns True if email was sent successfully
        """
        if not self.enabled:
            logger.warning("Email alerts disabled - skipping batch alert")
            return False
        
        if not anomalies:
            logger.info("No anomalies to alert about")
            return False
        
        try:
            # Create email content
            subject = f"Sleep Monitor Night Summary - {len(anomalies)} Anomaly(ies) Detected"
            
            # Use LLM enhancement if available
            if self.llm_enhancer:
                body = self.llm_enhancer.enhance_batch_anomaly_alert(anomalies, sensor_context)
            else:
                body = self._create_batch_alert_body(anomalies)
            
            # Send email
            success = self._send_email(subject, body)
            
            if success:
                logger.info(f"Batch alert email sent successfully for {len(anomalies)} anomalies")
            else:
                logger.error("Failed to send batch alert email")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending batch alert email: {e}")
            return False
    
    def send_no_anomaly_alert(self) -> bool:
        """
        Send email notification when no anomalies were detected during session
        Returns True if email was sent successfully
        """
        if not self.enabled:
            logger.warning("Email alerts disabled - skipping no-anomaly alert")
            return False
        
        try:
            subject = "Sleep Monitor Night Summary - No Anomalies Detected"
            body = self._create_no_anomaly_body()
            
            success = self._send_email(subject, body)
            
            if success:
                logger.info("No-anomaly email sent successfully")
            else:
                logger.error("Failed to send no-anomaly email")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending no-anomaly email: {e}")
            return False
    
    def _create_alert_body(self, anomalies: List[Dict[str, Any]]) -> str:
        """Create formatted email body for anomalies"""
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
    
    def _create_batch_alert_body(self, anomalies: List[Dict[str, Any]]) -> str:
        """Create formatted email body for batch anomalies"""
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
        
        body += f"""

---
Sleep Monitor System
Raspberry Pi Environment Monitor
This is an automated summary of your sleep environment monitoring session.
"""
        
        return body.strip()
    
    def _create_no_anomaly_body(self) -> str:
        """Create formatted email body for no anomalies detected"""
        current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        body = f"""
SLEEP MONITOR NIGHT SUMMARY

Time: {current_time}
Status: No anomalies detected tonight

Your sleep environment remained within normal parameters throughout the monitoring session.

---
Sleep Monitor System
Raspberry Pi Environment Monitor
This is an automated summary of your sleep environment monitoring session.
"""
        
        return body.strip()
    
    def _send_email(self, subject: str, body: str) -> bool:
        """Send email via Gmail SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_to
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to Gmail SMTP
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP authentication failed. Check your Gmail App Password.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test SMTP connection and authentication"""
        if not self.enabled:
            logger.warning("Email not configured - cannot test connection")
            return False
        
        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                logger.info("SMTP connection test successful")
                return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

def send_test_email():
    """Send a test email to verify configuration"""
    manager = EmailAlertManager()
    if manager.enabled:
        success = manager._send_email(
            "Sleep Monitor Test Email",
            "This is a test email from your Sleep Monitor system.\n\nIf you receive this, your email configuration is working correctly!"
        )
        if success:
            print("Test email sent successfully!")
        else:
            print("Test email failed to send")
    else:
        print("Email not configured. Set SMTP_USER, SMTP_PASS_APP, and ALERT_TO environment variables.")

if __name__ == "__main__":
    # Test email functionality
    send_test_email()
