import os
import smtplib
from email.message import EmailMessage

BREVO_HOST = os.getenv("BREVO_HOST", "smtp-relay.brevo.com")
BREVO_PORT = int(os.getenv("BREVO_PORT", "587"))
BREVO_USER = os.getenv("BREVO_USER")
BREVO_PASS = os.getenv("BREVO_PASS")
MAIL_FROM = os.getenv("MAIL_FROM")

def send_email_with_pdf(to_email: str, subject: str, body: str, pdf_bytes: bytes, filename: str):
    if not all([BREVO_USER, BREVO_PASS, MAIL_FROM]):
        raise RuntimeError("Missing Brevo env vars: BREVO_USER, BREVO_PASS, MAIL_FROM")

    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename
    )

    with smtplib.SMTP(BREVO_HOST, BREVO_PORT, timeout=30) as server:
        server.starttls()
        server.login(BREVO_USER, BREVO_PASS)
        server.send_message(msg)
