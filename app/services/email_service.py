import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class EmailService:
    @staticmethod
    async def send_email(subject: str, body: str, to_email: str):
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            print(f"SMTP not configured. Email to {to_email} skipped.")
            print(f"Subject: {subject}")
            # print(f"Body: {body[:100]}...")
            return

        def _send():
            msg = MIMEMultipart()
            msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

        # Run smtplib in a thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, _send)
        except Exception as e:
            print(f"Failed to send email to {to_email}: {e}")

    @staticmethod
    async def send_validation_alert(student_email: str, student_name: str, status: str, feedback: str = ""):
        subject = f"Resume Status Update: {status.capitalize()}"
        
        status_color = "#10b981" if status == "approved" else "#ef4444"
        
        html_body = f"""
        <html>
        <body style="font-family: sans-serif; line-height: 1.6; color: #334155;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; rounded: 12px;">
                <h2 style="color: #0f172a;">Hello {student_name},</h2>
                <p>There is an update on your resume validation status.</p>
                <div style="padding: 16px; background-color: #f8fafc; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; font-weight: bold;">Status: 
                        <span style="color: {status_color};">{status.upper()}</span>
                    </p>
                    {f'<p style="margin: 10px 0 0 0; font-style: italic;">Feedback: {feedback}</p>' if feedback else ""}
                </div>
                <p>You can view more details and download your PDF from the dashboard.</p>
                <a href="http://localhost:3000/dashboard/student/resumes" 
                   style="display: inline-block; padding: 12px 24px; background-color: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px;">
                   Open Dashboard
                </a>
                <p style="margin-top: 30px; font-size: 12px; color: #94a3b8;">
                    This is an automated message from the Matrix Placement Portal.
                </p>
            </div>
        </body>
        </html>
        """
        
        await EmailService.send_email(subject, html_body, student_email)
