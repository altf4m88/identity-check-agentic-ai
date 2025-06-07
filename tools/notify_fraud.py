import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langchain_core.tools import tool

# --- Load Environment Variables ---
# This loads the .env file at the project root
load_dotenv()

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Schema for Tool Input ---
class NotifyFraudInput(BaseModel):
    """Input schema for the fraud notification tool."""
    identity_number: str = Field(description="The duplicated identity number.")
    full_name: str = Field(description="The full name associated with the duplicated ID.")
    date_of_birth: str = Field(description="The date of birth associated with the duplicated ID.")

# --- The Tool Definition ---
@tool("notify_fraud_tool", args_schema=NotifyFraudInput)
def notify_fraud_tool(identity_number: str, full_name: str, date_of_birth: str) -> Dict[str, str]:
    """
    Sends an email notification about a potential fraud attempt.
    Uses SMTP credentials stored in environment variables.
    """
    # --- Fetch Email Credentials from Environment ---
    email_host = os.getenv("EMAIL_HOST")
    email_port = os.getenv("EMAIL_PORT")
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    recipient_email = os.getenv("EMAIL_USER") # Sending to self for this example

    if not all([email_host, email_port, email_user, email_pass]):
        error_msg = "Email credentials (HOST, PORT, USER, PASS) are not fully set in the .env file."
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}

    # --- Construct the Email Message ---
    subject = "🚨 FRAUD ALERT: Duplicate Identity Detected"
    
    # Plain text version
    text_body = f"""
FRAUD DETECTION ALERT
{'='*50}

IMPORTANT: A potential identity fraud attempt has been detected in our system.

INCIDENT DETAILS
---------------
A submitted identification card matches an existing record in our database.

Submission Information:
• Identity Number: {identity_number}
• Full Name     : {full_name}
• Date of Birth : {date_of_birth}

ACTION REQUIRED
--------------
This incident requires immediate review and investigation. Please verify the authenticity 
of the submitted documents and take appropriate action according to security protocols.

Note: This is an automated message from our security system. Please do not reply directly.

Best regards,
Security Monitoring System
ID Check Agent
{'='*50}
"""

    # HTML version
    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
        <h1 style="color: #721c24; margin: 0; font-size: 24px;">🚨 FRAUD DETECTION ALERT</h1>
    </div>

    <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
        <p style="color: #856404; font-weight: bold; margin: 0;">
            IMPORTANT: A potential identity fraud attempt has been detected in our system.
        </p>
    </div>

    <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
        <h2 style="color: #495057; font-size: 18px; margin-top: 0;">INCIDENT DETAILS</h2>
        <p style="margin: 0 0 10px 0;">A submitted identification card matches an existing record in our database.</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 5px;">
            <h3 style="color: #495057; font-size: 16px; margin-top: 0;">Submission Information:</h3>
            <ul style="list-style: none; padding: 0; margin: 0;">
                <li style="margin-bottom: 5px;">• Identity Number: <strong>{identity_number}</strong></li>
                <li style="margin-bottom: 5px;">• Full Name: <strong>{full_name}</strong></li>
                <li style="margin-bottom: 5px;">• Date of Birth: <strong>{date_of_birth}</strong></li>
            </ul>
        </div>
    </div>

    <div style="background-color: #cce5ff; border: 1px solid #b8daff; border-radius: 5px; padding: 15px; margin-bottom: 20px;">
        <h2 style="color: #004085; font-size: 18px; margin-top: 0;">ACTION REQUIRED</h2>
        <p style="margin: 0;">
            This incident requires immediate review and investigation. Please verify the authenticity 
            of the submitted documents and take appropriate action according to security protocols.
        </p>
    </div>

    <div style="border-top: 1px solid #dee2e6; padding-top: 15px; margin-top: 20px; color: #6c757d; font-size: 14px;">
        <p style="margin: 0 0 5px 0;"><em>Note: This is an automated message from our security system. Please do not reply directly.</em></p>
        <p style="margin: 0;">
            Best regards,<br>
            Security Monitoring System<br>
            ID Check Agent
        </p>
    </div>
</body>
</html>
"""

    message = MIMEMultipart('alternative')
    message["From"] = f"ID Check Security System <{email_user}>"
    message["To"] = recipient_email
    message["Subject"] = subject

    # Attach both plain text and HTML versions
    message.attach(MIMEText(text_body, 'plain'))
    message.attach(MIMEText(html_body, 'html'))

    # --- Send the Email via SMTP ---
    try:
        logger.info(f"Connecting to SMTP server at {email_host}:{email_port}...")
        with smtplib.SMTP(email_host, int(email_port)) as server:
            server.starttls()  # Secure the connection
            server.login(email_user, email_pass)
            server.sendmail(email_user, recipient_email, message.as_string())
            logger.info("Fraud notification email sent successfully.")
        
        return {
            "status": "success",
            "message": f"Fraud notification for ID {identity_number} sent to {recipient_email}."
        }

    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP Authentication Error: {e}. Check your EMAIL_USER and EMAIL_PASS."
        logger.error(error_msg)
        return {"status": "error", "error": error_msg}
    except Exception as e:
        error_msg = f"Failed to send email: {e}"
        logger.error(error_msg, exc_info=True)
        return {"status": "error", "error": error_msg}
