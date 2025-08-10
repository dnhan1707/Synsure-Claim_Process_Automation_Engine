from app.config.settings import get_settings
from app.schema.schema import EmailRequest
from email.mime.text import MIMEText
import smtplib


class EmailService():
    def __init__(self):
        email_settings = get_settings().email
        self.demo_email_user = email_settings.demo_email_user
        self.demo_email_pass = email_settings.demo_email_pass
    
    
    async def send_email(self, data: EmailRequest):
        try:
            body = f"Name: {data.name}\n Company: {data.company} \nEmail: {data.email}\nMessage: {data.message}"
            msg = MIMEText(body)
            msg["Subject"] = "Demo Request"
            msg["From"] = data.email
            msg["To"] = self.demo_email_user

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.demo_email_user, self.demo_email_pass)
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())

            return None
        
        except Exception as e:
            return {"error": e}