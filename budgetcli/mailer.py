import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_password_reset(to_email: str, reset_url: str) -> None:
    """Send a password-reset email, or print to stderr in dev mode.

    Dev mode activates when SMTP_HOST is not set — the reset link is printed
    to stderr so the full flow can be tested locally without real credentials.
    """
    smtp_host = os.environ.get("SMTP_HOST", "")
    if not smtp_host:
        print("\n" + "=" * 60, file=sys.stderr)
        print("DEV MODE — password reset link (not emailed):", file=sys.stderr)
        print(f"  To:   {to_email}", file=sys.stderr)
        print(f"  Link: {reset_url}", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr, flush=True)
        return

    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("FROM_EMAIL", smtp_user)

    subject = "Reset your BudgetBalancer password"
    plain = (
        f"Hi,\n\n"
        f"We received a request to reset your BudgetBalancer password.\n\n"
        f"Click the link below to set a new password — it expires in 30 minutes:\n\n"
        f"  {reset_url}\n\n"
        f"If you didn't request this, you can safely ignore this email.\n\n"
        f"— BudgetBalancer"
    )
    html = (
        f"<p>Hi,</p>"
        f"<p>We received a request to reset your BudgetBalancer password.</p>"
        f"<p>Click the link below to set a new password — it expires in <strong>30 minutes</strong>:</p>"
        f'<p><a href="{reset_url}">{reset_url}</a></p>'
        f"<p>If you didn't request this, you can safely ignore this email.</p>"
        f"<p>— BudgetBalancer</p>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
