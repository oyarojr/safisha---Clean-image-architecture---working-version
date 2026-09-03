from twilio.rest import Client
from django.conf import settings
import base64
import requests
from datetime import datetime
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils import timezone

def format_phone(phone):
    phone = phone.strip()
    if phone.startswith('0'):
        return '254' + phone[1:]
    if phone.startswith('1'):
        return '254' + phone
    if phone.startswith('+'):
        return phone.replace('+', '')
    return phone

def get_access_token():
    auth = base64.b64encode(
        f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}".encode()
    ).decode()

    response = requests.get(
        settings.MPESA_TOKEN_URL,
        headers={"Authorization": f"Basic {auth}"}
    )
    return response.json()['access_token']

def initiate_stk_push(phone, amount, order_id):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(
        f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": f"ORDER{order_id}",
        "TransactionDesc": "Order Payment"
    }

    response = requests.post(
        settings.MPESA_STK_URL,
        json=payload,
        headers={
            "Authorization": f"Bearer {get_access_token()}",
            "Content-Type": "application/json"
        }
    )

    return response.json()


def send_whatsapp_message(message, to):
    client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)

    client.messages.create(
        body=message,
        from_='whatsapp:+14155238886',
        to=f'whatsapp:+{to}'
    )


# Email verification functions
def generate_verification_token():
    """Generate a random verification token"""
    return get_random_string(64)


def send_verification_email(user, request):
    """Send email verification link to user"""
    profile = user.profile
    token = generate_verification_token()
    profile.email_verification_token = token
    profile.email_verification_sent_at = timezone.now()
    profile.save()
    
    verification_url = request.build_absolute_uri(
        f'/verify-email/{token}/'
    )
    
    subject = 'Verify Your Email - MyStore'
    message = f'''
Hi {user.first_name or user.username},

Thank you for signing up at MyStore!

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
The MyStore Team
'''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_password_reset_email(user, reset_url):
    """Send password reset email"""
    subject = 'Password Reset - MyStore'
    message = f'''
Hi {user.first_name or user.username},

You requested to reset your password for your MyStore account.

Click the link below to reset your password:
{reset_url}

If you didn't request this, please ignore this email.
Your password will remain unchanged.

This link will expire in 1 hour.

Best regards,
The MyStore Team
'''
    
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )