# app/services/email_service.py
"""
Complete Email Service Implementation with Templates and Queue Support
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from pathlib import Path
import jinja2
from datetime import datetime
import asyncio
import logging

from app.core.config import get_settings
from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def __init__(self):
        self.smtp_host = getattr(settings, 'SMTP_HOST', 'localhost')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', '')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', '')
        self.email_from = getattr(settings, 'EMAIL_FROM', 'noreply@emberframe.com')
        self.use_tls = getattr(settings, 'SMTP_USE_TLS', True)

        # Email templates
        self.template_dir = Path("app/templates/email")
        self.template_dir.mkdir(exist_ok=True)

        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )

        # Cache service for rate limiting
        self.cache = CacheService()

        # Email queue for background processing
        self.email_queue = []

    def _create_templates(self):
        """Create default email templates"""
        templates = {
            "welcome.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to EmberFrame V2</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .footer { text-align: center; margin-top: 30px; font-size: 0.9rem; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Welcome to EmberFrame V2</h1>
            <p>Your modern web desktop environment</p>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>Thank you for joining EmberFrame V2. You now have access to a powerful web-based desktop environment with advanced file management capabilities.</p>

            <h3>Getting Started:</h3>
            <ul>
                <li>Upload and organize your files</li>
                <li>Use built-in applications like Text Editor and Calculator</li>
                <li>Customize your desktop experience</li>
                <li>Share files securely with others</li>
            </ul>

            <a href="{{ login_url }}" class="button">Access Your Desktop</a>

            <p>If you have any questions, please don't hesitate to contact our support team.</p>
        </div>
        <div class="footer">
            <p>&copy; 2024 EmberFrame V2. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
            """,

            "password_reset.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Password Reset - EmberFrame V2</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #e74c3c; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; padding: 12px 24px; background: #e74c3c; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 6px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Password Reset Request</h1>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>We received a request to reset your password for your EmberFrame V2 account.</p>

            <a href="{{ reset_url }}" class="button">Reset Your Password</a>

            <div class="warning">
                <strong>Security Notice:</strong>
                <ul>
                    <li>This link will expire in {{ expiry_hours }} hours</li>
                    <li>If you didn't request this reset, please ignore this email</li>
                    <li>Never share this link with anyone</li>
                </ul>
            </div>

            <p>If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="word-break: break-all; background: #f0f0f0; padding: 10px; border-radius: 4px;">{{ reset_url }}</p>
        </div>
    </div>
</body>
</html>
            """,

            "security_alert.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Security Alert - EmberFrame V2</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f39c12; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .alert { background: #fee; border: 1px solid #fcc; padding: 15px; border-radius: 6px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Security Alert</h1>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>We detected {{ alert_type }} on your EmberFrame V2 account.</p>

            <div class="alert">
                <h3>Alert Details:</h3>
                <ul>
                    <li><strong>Time:</strong> {{ timestamp }}</li>
                    <li><strong>IP Address:</strong> {{ ip_address }}</li>
                    <li><strong>Location:</strong> {{ location }}</li>
                    <li><strong>Device:</strong> {{ device_info }}</li>
                </ul>
            </div>

            <p>If this was you, no action is needed. If you don't recognize this activity, please:</p>
            <ul>
                <li>Change your password immediately</li>
                <li>Review your account activity</li>
                <li>Enable two-factor authentication</li>
                <li>Contact support if needed</li>
            </ul>
        </div>
    </div>
</body>
</html>
            """,

            "file_shared.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>File Shared - EmberFrame V2</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2ecc71; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; padding: 12px 24px; background: #2ecc71; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }
        .file-info { background: white; border: 1px solid #ddd; padding: 15px; border-radius: 6px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📁 File Shared With You</h1>
        </div>
        <div class="content">
            <h2>Hello {{ recipient_name }}!</h2>
            <p>{{ sharer_name }} has shared a file with you on EmberFrame V2.</p>

            <div class="file-info">
                <h3>📄 {{ file_name }}</h3>
                <p><strong>Size:</strong> {{ file_size }}</p>
                <p><strong>Type:</strong> {{ file_type }}</p>
                <p><strong>Permission:</strong> {{ permission }}</p>
                {% if expires_at %}
                <p><strong>Expires:</strong> {{ expires_at }}</p>
                {% endif %}
            </div>

            <a href="{{ file_url }}" class="button">View File</a>

            <p>You can access this file anytime from your EmberFrame V2 desktop.</p>
        </div>
    </div>
</body>
</html>
            """,

            "storage_warning.html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Storage Warning - EmberFrame V2</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f39c12; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 6px; margin: 20px 0; }
        .storage-bar { background: #ddd; height: 20px; border-radius: 10px; overflow: hidden; margin: 10px 0; }
        .storage-fill { background: {{ bar_color }}; height: 100%; transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Storage Usage Warning</h1>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>Your storage usage is approaching the limit on EmberFrame V2.</p>

            <div class="warning">
                <h3>Current Usage:</h3>
                <p><strong>{{ used_storage }}</strong> of <strong>{{ total_storage }}</strong> ({{ usage_percentage }}%)</p>
                <div class="storage-bar">
                    <div class="storage-fill" style="width: {{ usage_percentage }}%;"></div>
                </div>
            </div>

            <h3>Recommended Actions:</h3>
            <ul>
                <li>Delete unnecessary files</li>
                <li>Archive old documents</li>
                <li>Move large files to external storage</li>
                <li>Consider upgrading your storage plan</li>
            </ul>

            <p>Manage your files from your EmberFrame V2 desktop to free up space.</p>
        </div>
    </div>
</body>
</html>
            """
        }

        # Create template files
        for filename, content in templates.items():
            template_path = self.template_dir / filename
            if not template_path.exists():
                template_path.write_text(content.strip())

    async def send_email(
            self,
            to_email: str,
            subject: str,
            template_name: str = None,
            template_vars: Dict[str, Any] = None,
            html_content: str = None,
            text_content: str = None,
            attachments: List[str] = None,
            priority: str = "normal"
    ) -> bool:
        """Send email with template support"""

        # Rate limiting check
        rate_key = f"email_rate:{to_email}"
        rate_count = await self.cache.get_system_cache(rate_key) or 0

        if rate_count >= 10:  # Max 10 emails per hour per recipient
            logger.warning(f"Email rate limit exceeded for {to_email}")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_from
            msg['To'] = to_email
            msg['Subject'] = subject
            msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Generate content from template
            if template_name:
                html_content = self._render_template(template_name, template_vars or {})
                text_content = self._html_to_text(html_content)

            # Add content parts
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))

            if html_content:
                msg.attach(MIMEText(html_content, 'html'))

            # Add attachments
            if attachments:
                for file_path in attachments:
                    if Path(file_path).exists():
                        self._add_attachment(msg, file_path)

            # Send email
            await self._send_smtp(msg)

            # Update rate limiting
            await self.cache.set_system_cache(rate_key, rate_count + 1, 3600)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        """Render email template with variables"""
        try:
            # Ensure templates exist
            self._create_templates()

            template = self.jinja_env.get_template(template_name)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return f"<p>Email content error</p>"

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text"""
        try:
            import re
            # Simple HTML to text conversion
            text = re.sub(r'<[^>]+>', '', html_content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except:
            return "Plain text version not available"

    def _add_attachment(self, msg: MIMEMultipart, file_path: str):
        """Add file attachment to email"""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {Path(file_path).name}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to add attachment {file_path}: {e}")

    async def _send_smtp(self, msg: MIMEMultipart):
        """Send email via SMTP"""

        def send_sync():
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)

                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

        # Run in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, send_sync)

    # Convenience methods for common email types
    async def send_welcome_email(self, email: str, username: str, login_url: str):
        """Send welcome email to new user"""
        return await self.send_email(
            to_email=email,
            subject="Welcome to EmberFrame V2!",
            template_name="welcome.html",
            template_vars={
                "username": username,
                "login_url": login_url
            }
        )

    async def send_password_reset_email(self, email: str, username: str, reset_token: str):
        """Send password reset email"""
        reset_url = f"{settings.APP_URL}/reset-password?token={reset_token}"

        return await self.send_email(
            to_email=email,
            subject="Password Reset - EmberFrame V2",
            template_name="password_reset.html",
            template_vars={
                "username": username,
                "reset_url": reset_url,
                "expiry_hours": 1
            }
        )

    async def send_security_alert(
            self,
            email: str,
            username: str,
            alert_type: str,
            ip_address: str,
            device_info: str,
            location: str = "Unknown"
    ):
        """Send security alert email"""
        return await self.send_email(
            to_email=email,
            subject=f"Security Alert - {alert_type}",
            template_name="security_alert.html",
            template_vars={
                "username": username,
                "alert_type": alert_type,
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                "ip_address": ip_address,
                "location": location,
                "device_info": device_info
            },
            priority="high"
        )

    async def send_file_shared_notification(
            self,
            recipient_email: str,
            recipient_name: str,
            sharer_name: str,
            file_name: str,
            file_size: str,
            file_type: str,
            permission: str,
            file_url: str,
            expires_at: str = None
    ):
        """Send file sharing notification"""
        return await self.send_email(
            to_email=recipient_email,
            subject=f"File shared: {file_name}",
            template_name="file_shared.html",
            template_vars={
                "recipient_name": recipient_name,
                "sharer_name": sharer_name,
                "file_name": file_name,
                "file_size": file_size,
                "file_type": file_type,
                "permission": permission,
                "file_url": file_url,
                "expires_at": expires_at
            }
        )

    async def send_storage_warning(
            self,
            email: str,
            username: str,
            used_storage: str,
            total_storage: str,
            usage_percentage: float
    ):
        """Send storage usage warning"""
        bar_color = "#e74c3c" if usage_percentage >= 90 else "#f39c12"

        return await self.send_email(
            to_email=email,
            subject="Storage Usage Warning - EmberFrame V2",
            template_name="storage_warning.html",
            template_vars={
                "username": username,
                "used_storage": used_storage,
                "total_storage": total_storage,
                "usage_percentage": int(usage_percentage),
                "bar_color": bar_color
            }
        )

    async def send_bulk_email(
            self,
            recipients: List[str],
            subject: str,
            template_name: str,
            template_vars: Dict[str, Any],
            batch_size: int = 10
    ):
        """Send bulk emails with rate limiting"""
        results = []

        for i in range(0, len(recipients), batch_size):
            batch = recipients[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[
                    self.send_email(email, subject, template_name, template_vars)
                    for email in batch
                ],
                return_exceptions=True
            )
            results.extend(batch_results)

            # Delay between batches to avoid overwhelming SMTP server
            if i + batch_size < len(recipients):
                await asyncio.sleep(1)

        return results

    def queue_email(self, **kwargs):
        """Queue email for background processing"""
        self.email_queue.append({
            "timestamp": datetime.utcnow(),
            "params": kwargs
        })

    async def process_email_queue(self):
        """Process queued emails"""
        while self.email_queue:
            email_data = self.email_queue.pop(0)
            try:
                await self.send_email(**email_data["params"])
            except Exception as e:
                logger.error(f"Failed to process queued email: {e}")


# Global email service instance
email_service = EmailService()