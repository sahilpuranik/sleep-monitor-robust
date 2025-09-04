#!/usr/bin/env python3
"""
Test Email Configuration
Simple script to test email setup and send a test email
"""

import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from email_utils import EmailAlertManager

def main():
    """Test email configuration and send test email"""
    print("Testing Email Configuration")
    print("=" * 40)
    
    # Check environment variables
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS_APP')
    alert_to = os.getenv('ALERT_TO')
    
    print("Environment Variables:")
    print(f"   SMTP_USER: {'Set' if smtp_user else 'Not set'}")
    print(f"   SMTP_PASS_APP: {'Set' if smtp_pass else 'Not set'}")
    print(f"   ALERT_TO: {'Set' if alert_to else 'Not set'}")
    
    if not all([smtp_user, smtp_pass, alert_to]):
        print("\nEmail configuration incomplete!")
        print("   Please set the required environment variables:")
        print("   export SMTP_USER='your.email@gmail.com'")
        print("   export SMTP_PASS_APP='your-app-password'")
        print("   export ALERT_TO='alert.recipient@gmail.com'")
        return
    
    print(f"\nEmail Configuration:")
    print(f"   From: {smtp_user}")
    print(f"   To: {alert_to}")
    
    # Test connection
    print("\nTesting SMTP connection...")
    email_manager = EmailAlertManager()
    
    if not email_manager.enabled:
        print("Email manager not enabled")
        return
    
    # Test connection
    if email_manager.test_connection():
        print("SMTP connection successful!")
        
        # Send test email
        print("\nSending test email...")
        success = email_manager._send_email(
            "Sleep Monitor Test Email",
            "This is a test email from your Sleep Monitor system.\n\nIf you receive this, your email configuration is working correctly!"
        )
        
        if success:
            print("Test email sent successfully!")
            print("   Check your inbox for the test email.")
        else:
            print("Failed to send test email")
    else:
        print("SMTP connection failed")
        print("   Check your Gmail App Password and network connection")

if __name__ == "__main__":
    main()
