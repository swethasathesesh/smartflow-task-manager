import smtplib
import random
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
import asyncio
import aiosmtplib
from email_config import (
    SMTP_SERVER, SMTP_PORT, EMAIL_ADDRESS, EMAIL_PASSWORD,
    EMAIL_FROM_NAME, EMAIL_TIMEOUT, OTP_LENGTH, OTP_EXPIRY_MINUTES,
    MAX_OTP_ATTEMPTS, DEVELOPMENT_MODE
)

# In-memory OTP storage (in production, use Redis or database)
otp_storage: Dict[str, Dict] = {}

class EmailService:
    def __init__(self):
        # Email configuration from config file
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.email_address = EMAIL_ADDRESS
        self.email_password = EMAIL_PASSWORD
        self.from_name = EMAIL_FROM_NAME
        self.timeout = EMAIL_TIMEOUT
        self.development_mode = DEVELOPMENT_MODE
        
    def generate_otp(self, length: int = None) -> str:
        """Generate a random OTP"""
        if length is None:
            length = OTP_LENGTH
        return ''.join(random.choices(string.digits, k=length))
    
    def store_otp(self, email: str, otp: str, purpose: str = "registration") -> None:
        """Store OTP with expiration time"""
        expiry_time = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        otp_storage[email] = {
            "otp": otp,
            "purpose": purpose,
            "created_at": datetime.utcnow(),
            "expires_at": expiry_time,
            "attempts": 0
        }
    
    def verify_otp(self, email: str, provided_otp: str, purpose: str = "registration", consume: bool = False) -> Dict[str, any]:
        """Verify OTP and return result
        
        Args:
            email: Email address
            provided_otp: OTP code to verify
            purpose: Purpose of OTP (registration, password_reset, etc.)
            consume: If True, delete OTP after successful verification
        """
        if email not in otp_storage:
            print(f"[OTP DEBUG] No OTP found for email: {email}")
            return {"valid": False, "message": "No OTP found for this email"}
        
        stored_data = otp_storage[email]
        print(f"[OTP DEBUG] Email: {email}, Stored OTP: {stored_data['otp']}, Provided OTP: {provided_otp}")
        
        # Check if OTP has expired
        if datetime.utcnow() > stored_data["expires_at"]:
            del otp_storage[email]
            return {"valid": False, "message": "OTP has expired"}
        
        # Check if too many attempts
        if stored_data["attempts"] >= MAX_OTP_ATTEMPTS:
            del otp_storage[email]
            return {"valid": False, "message": "Too many failed attempts. Please request a new OTP"}
        
        # Check if purpose matches
        if stored_data["purpose"] != purpose:
            return {"valid": False, "message": "Invalid OTP purpose"}
        
        # Verify OTP
        if stored_data["otp"] == provided_otp:
            if consume:
                print(f"[OTP DEBUG] Consuming OTP for email: {email}")
                del otp_storage[email]  # Remove OTP after successful verification
            print(f"[OTP DEBUG] OTP verified successfully for email: {email}")
            return {"valid": True, "message": "OTP verified successfully"}
        else:
            # Increment attempts
            otp_storage[email]["attempts"] += 1
            remaining_attempts = MAX_OTP_ATTEMPTS - otp_storage[email]["attempts"]
            print(f"[OTP DEBUG] Invalid OTP for email: {email}. Attempts remaining: {remaining_attempts}")
            return {
                "valid": False, 
                "message": f"Invalid OTP. {remaining_attempts} attempts remaining"
            }
    
    def create_otp_email_content(self, otp: str, purpose: str = "registration") -> tuple:
        """Create email content for OTP"""
        if purpose == "registration":
            subject = "Verify Your Email - Task Management System"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .otp-box {{ background-color: #e8f5e8; border: 2px solid #4CAF50; padding: 15px; text-align: center; margin: 20px 0; }}
                    .otp-code {{ font-size: 24px; font-weight: bold; color: #2e7d32; letter-spacing: 3px; }}
                    .footer {{ background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Email Verification</h1>
                    </div>
                    <div class="content">
                        <h2>Welcome to Task Management System!</h2>
                        <p>Thank you for registering with us. To complete your registration, please verify your email address using the OTP below:</p>
                        
                        <div class="otp-box">
                            <p>Your verification code is:</p>
                            <div class="otp-code">{otp}</div>
                        </div>
                        
                        <p><strong>Important:</strong></p>
                        <ul>
                            <li>This OTP is valid for 10 minutes only</li>
                            <li>Do not share this code with anyone</li>
                            <li>If you didn't request this, please ignore this email</li>
                        </ul>
                        
                        <p>If you have any questions, please contact our support team.</p>
                    </div>
                    <div class="footer">
                        <p>&copy; 2025 Task Management System. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            subject = "Your OTP Code - Task Management System"
            html_content = f"""
            <html>
            <body>
                <h2>Your OTP Code</h2>
                <p>Your OTP code is: <strong>{otp}</strong></p>
                <p>This code will expire in 10 minutes.</p>
            </body>
            </html>
            """
        
        return subject, html_content
    
    async def send_otp_email(self, email: str, otp: str, purpose: str = "registration") -> Dict[str, any]:
        """Send OTP email asynchronously"""
        try:
            # Development mode - just print OTP to console
            if self.development_mode:
                print(f"\n{'='*50}")
                print(f"DEVELOPMENT MODE - OTP EMAIL")
                print(f"{'='*50}")
                print(f"To: {email}")
                print(f"Purpose: {purpose}")
                print(f"OTP Code: {otp}")
                print(f"Expires in: {OTP_EXPIRY_MINUTES} minutes")
                print(f"{'='*50}\n")
                return {"success": True, "message": "OTP sent successfully (development mode)"}
            
            subject, html_content = self.create_otp_email_content(otp, purpose)
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.email_address}>"
            message["To"] = email
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email using aiosmtplib for async operation
            await aiosmtplib.send(
                message,
                hostname=self.smtp_server,
                port=self.smtp_port,
                start_tls=True,
                username=self.email_address,
                password=self.email_password,
                timeout=self.timeout
            )
            
            return {"success": True, "message": "OTP sent successfully"}
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            return {"success": False, "message": f"Failed to send email: {str(e)}"}
    
    def cleanup_expired_otps(self):
        """Clean up expired OTPs from storage"""
        current_time = datetime.utcnow()
        expired_emails = [
            email for email, data in otp_storage.items()
            if current_time > data["expires_at"]
        ]
        
        for email in expired_emails:
            del otp_storage[email]
        
        return len(expired_emails)

# Global email service instance
email_service = EmailService()

# Helper functions for easy access
async def send_registration_otp(email: str) -> Dict[str, any]:
    """Send OTP for registration"""
    otp = email_service.generate_otp()
    email_service.store_otp(email, otp, "registration")
    result = await email_service.send_otp_email(email, otp, "registration")
    
    if result["success"]:
        return {"success": True, "message": "OTP sent to your email address"}
    else:
        return {"success": False, "message": "Failed to send OTP. Please try again."}

def verify_registration_otp(email: str, otp: str, consume: bool = False) -> Dict[str, any]:
    """Verify OTP for registration
    
    Args:
        email: Email address
        otp: OTP code to verify
        consume: If True, delete OTP after successful verification
    """
    return email_service.verify_otp(email, otp, "registration", consume)
