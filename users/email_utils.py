from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, Content
from django.conf import settings
import json

def send_otp_email(user, otp):
    """
    Send OTP verification email using SendGrid template
    """
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        from_email = Email(settings.DEFAULT_FROM_EMAIL)
        to_email = Email(user.email)
        
        # Create mail with template
        mail = Mail(
            from_email=from_email,
            to_emails=to_email
        )
        
        # Set template ID
        mail.template_id = settings.SENDGRID_TEMPLATE_ID
        
        # Set template data
        mail.dynamic_template_data = {
            "username": user.username,
            "otp": otp,
            "email": user.email
        }
        
        # Send email
        response = sg.send(mail)
        print(f"SendGrid Response Status Code: {response.status_code}")
        print(f"SendGrid Response Headers: {response.headers}")
        print(f"SendGrid Response Body: {response.body}")
        return True
    except Exception as e:
        print(f"SendGrid Error: {str(e)}")
        return False 