import os
import django
import smtplib
from email.mime.text import MIMEText

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doctorappointmentBackend.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email():
    try:
        # Print current email settings
        print("Current Email Settings:")
        print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        print(f"EMAIL_HOST_PASSWORD: {settings.EMAIL_HOST_PASSWORD}")  # Show actual password for debugging
        
        # Try direct SMTP connection first
        print("\nTesting SMTP connection...")
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls()
        try:
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            print("SMTP Login successful!")
        except Exception as e:
            print(f"SMTP Login failed: {str(e)}")
        finally:
            server.quit()
        
        # Try sending email through Django
        print("\nAttempting to send test email through Django...")
        send_mail(
            'Test Email from Django',
            'This is a test email from your Django application.',
            settings.EMAIL_HOST_USER,
            [settings.EMAIL_HOST_USER],  # Send to yourself
            fail_silently=False,
        )
        print("Test email sent successfully!")
        
    except Exception as e:
        print(f"\nError sending email: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Verify your Gmail account settings:")
        print("   - Go to https://myaccount.google.com/security")
        print("   - Make sure 2-Step Verification is enabled")
        print("   - Generate a new App Password if needed")
        print("2. Check your .env file configuration")
        print("3. Verify the email settings in settings.py")
        print("\nCurrent password being used:", settings.EMAIL_HOST_PASSWORD)

if __name__ == "__main__":
    test_email() 