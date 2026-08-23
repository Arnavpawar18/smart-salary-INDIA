import email.utils
import logging
import smtplib
import threading
import time
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import StrEnum
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class DeliveryState(StrEnum):
    OTP_GENERATED = "OTP_GENERATED"
    EMAIL_QUEUED = "EMAIL_QUEUED"
    SMTP_CONNECTED = "SMTP_CONNECTED"
    SMTP_AUTHENTICATED = "SMTP_AUTHENTICATED"
    SMTP_ACCEPTED = "SMTP_ACCEPTED"
    SEND_FAILED = "SEND_FAILED"


class TestEmailInbox:
    """In-memory test inbox for deterministic automated testing without network access."""

    inbox: list[dict[str, Any]] = []
    _capture_mode: bool = False

    @classmethod
    def _is_capture_allowed(cls) -> bool:
        return settings.ENVIRONMENT in {"test", "development"}

    @classmethod
    def enable_capture(cls) -> None:
        if not cls._is_capture_allowed():
            logger.warning("TestEmailInbox.enable_capture() ignored in production.")
            return
        cls._capture_mode = True
        cls.inbox.clear()

    @classmethod
    def disable_capture(cls) -> None:
        cls._capture_mode = False
        cls.inbox.clear()

    @classmethod
    def is_capture_mode(cls) -> bool:
        return cls._capture_mode and cls._is_capture_allowed()

    @classmethod
    def get_last_otp(cls) -> str | None:
        """Return the OTP from the most recent recorded email, or None if none."""
        if not cls.inbox:
            return None
        return cls.inbox[-1].get("otp")

    @classmethod
    def record(cls, to_email: str, subject: str, body_text: str, body_html: str, raw_otp: str | None) -> None:
        cls.inbox.append(
            {
                "to_email": to_email,
                "subject": subject,
                "body_text": body_text,
                "body_html": body_html,
                "otp": raw_otp,
                "timestamp": time.time(),
            }
        )

    @classmethod
    def get_last_email(cls) -> dict[str, Any] | None:
        return cls.inbox[-1] if cls.inbox else None

    @classmethod
    def clear(cls) -> None:
        cls.inbox.clear()


class EmailService:
    """
    Authoritative email delivery service for SmartSalary India.
    Handles transactional OTP emails for registration and password resets with
    explicit delivery state tracking, connection pooling/timeouts, and retry loops.
    """

    last_delivery_state: DeliveryState = DeliveryState.OTP_GENERATED
    last_send_metrics: dict[str, Any] = {}
    _last_error: Exception | None = None

    @classmethod
    def check_connectivity(cls) -> bool:
        """Probes SMTP handshake on startup without raising unhandled exceptions."""
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            return True
        try:
            cls._open_connection()
            return True
        except Exception as exc:
            cls._last_error = exc
            logger.warning(
                "SMTP connectivity probe failed at %s:%s — %s",
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                exc,
            )
            return False

    @classmethod
    def _open_connection(cls) -> smtplib.SMTP | smtplib.SMTP_SSL:
        if settings.SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_CONNECT_TIMEOUT_SECONDS,
            )
        else:
            server = smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_CONNECT_TIMEOUT_SECONDS,
            )

        server.ehlo()
        if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
            server.starttls()
            server.ehlo()

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            password = settings.SMTP_PASSWORD.replace(" ", "")
            server.login(settings.SMTP_USER, password)

        return server

    @classmethod
    def _send_smtp(cls, to_email: str, subject: str, body_text: str, body_html: str, raw_otp: str | None = None) -> bool:
        """Dispatches an email via configured SMTP server with TLS/SSL and transient retries."""
        cls.last_delivery_state = DeliveryState.EMAIL_QUEUED

        # Development / Test capture interception
        if TestEmailInbox.is_capture_mode():
            TestEmailInbox.record(to_email, subject, body_text, body_html, raw_otp)
            cls.last_delivery_state = DeliveryState.SMTP_ACCEPTED
            cls.last_send_metrics = {"ok": True, "duration_ms": 0, "state": DeliveryState.SMTP_ACCEPTED}
            return True

        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            if settings.ENVIRONMENT != "production":
                if settings.DEV_EXPOSE_OTP:
                    logger.info("📧 [DEV EMAIL] To: %s | Subject: %s | OTP: %s", to_email, subject, raw_otp)
                else:
                    logger.info("📧 [DEV EMAIL] To: %s | Subject: %s (OTP suppressed in logs)", to_email, subject)
                cls.last_delivery_state = DeliveryState.SMTP_ACCEPTED
                cls.last_send_metrics = {"ok": True, "duration_ms": 0, "state": DeliveryState.SMTP_ACCEPTED}
                return True
            logger.warning("SMTP credentials not configured; email to %s suppressed.", to_email)
            cls.last_delivery_state = DeliveryState.SEND_FAILED
            return False

        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        from_header = f"{settings.SMTP_FROM_NAME} <{from_email}>"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_header
        msg["To"] = to_email
        msg["Message-ID"] = f"<{uuid.uuid4().hex}@smartsalary.in>"
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Reply-To"] = from_email

        part1 = MIMEText(body_text, "plain", "utf-8")
        part2 = MIMEText(body_html, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        start_time = time.perf_counter()
        attempts = 0

        while True:
            attempts += 1
            server = None
            try:
                cls.last_delivery_state = DeliveryState.SMTP_CONNECTED
                server = cls._open_connection()
                cls.last_delivery_state = DeliveryState.SMTP_AUTHENTICATED
                server.sendmail(from_email, [to_email], msg.as_string())
                cls.last_delivery_state = DeliveryState.SMTP_ACCEPTED

                duration_ms = (time.perf_counter() - start_time) * 1000
                cls.last_send_metrics = {"ok": True, "duration_ms": duration_ms, "state": DeliveryState.SMTP_ACCEPTED}
                logger.info("Successfully dispatched email [%s] to %s (latency: %.2fms)", subject, to_email, duration_ms)
                return True
            except smtplib.SMTPAuthenticationError as auth_err:
                cls._last_error = auth_err
                cls.last_delivery_state = DeliveryState.SEND_FAILED
                duration_ms = (time.perf_counter() - start_time) * 1000
                cls.last_send_metrics = {"ok": False, "duration_ms": duration_ms, "error": str(auth_err)}
                logger.error(
                    "SMTP authentication failed for %s. Check SMTP_USER/SMTP_PASSWORD "
                    "(Gmail requires a 16-char App Password).",
                    settings.SMTP_USER,
                )
                return False
            except (TimeoutError, ConnectionRefusedError, smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, OSError) as transient_err:
                cls._last_error = transient_err
                if attempts > settings.SMTP_MAX_RETRIES:
                    cls.last_delivery_state = DeliveryState.SEND_FAILED
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    cls.last_send_metrics = {"ok": False, "duration_ms": duration_ms, "error": str(transient_err)}
                    logger.error(
                        "Failed to send email to %s after %d attempts (%.2fms): %s",
                        to_email,
                        attempts,
                        duration_ms,
                        transient_err,
                    )
                    return False
                time.sleep(settings.SMTP_RETRY_BACKOFF_SECONDS)
            except Exception as exc:
                cls._last_error = exc
                cls.last_delivery_state = DeliveryState.SEND_FAILED
                duration_ms = (time.perf_counter() - start_time) * 1000
                cls.last_send_metrics = {"ok": False, "duration_ms": duration_ms, "error": str(exc)}
                logger.error("Unexpected SMTP failure sending email to %s: %s", to_email, exc)
                return False
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass

    @classmethod
    def send_email_background(cls, to_email: str, subject: str, body_text: str, body_html: str) -> None:
        """Lightweight background email worker thread."""
        thread = threading.Thread(
            target=cls._send_smtp,
            args=(to_email, subject, body_text, body_html),
            daemon=True,
            name=f"email-dispatch-{to_email}",
        )
        thread.start()

    @classmethod
    def send_email_verification_otp_background(cls, to_email: str, otp: str) -> None:
        """Non-blocking background dispatch of email verification OTP."""
        thread = threading.Thread(
            target=cls.send_email_verification_otp,
            args=(to_email, otp),
            daemon=True,
            name=f"otp-verify-{to_email}",
        )
        thread.start()

    @classmethod
    def send_password_reset_otp_background(cls, to_email: str, otp: str) -> None:
        """Non-blocking background dispatch of password reset OTP."""
        thread = threading.Thread(
            target=cls.send_password_reset_otp,
            args=(to_email, otp),
            daemon=True,
            name=f"otp-reset-{to_email}",
        )
        thread.start()

    @classmethod
    def send_email_verification_otp(cls, to_email: str, otp: str) -> bool:
        """Dispatches 6-digit verification OTP during user registration."""
        subject = "Verify your SmartSalary India email"
        body_text = (
            f"Welcome to SmartSalary India!\n\n"
            f"Your 6-digit verification code is: {otp}\n\n"
            f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes. "
            f"If you did not sign up for SmartSalary India, please ignore this email."
        )
        body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .brand {{ font-size: 20px; font-weight: 700; color: #4f46e5; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }}
    .otp-box {{ background: #f1f5f9; border-radius: 8px; padding: 16px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1e293b; margin: 24px 0; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 28px; line-height: 1.5; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">₹ SmartSalary.IN</div>
    <h2 style="font-size: 18px; margin: 0 0 12px 0; color: #0f172a;">Verify your email address</h2>
    <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px 0;">
      Thank you for registering with SmartSalary India. Please use the following 6-digit one-time password (OTP) to activate your account:
    </p>
    <div class="otp-box">{otp}</div>
    <p style="font-size: 13px; color: #64748b; margin: 0;">
      ⏱️ This code expires in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>. Never share this code with anyone.
    </p>
    <div class="footer">
      If you did not request this email, you can safely ignore it.<br>
      © 2026 SmartSalary India. Statutory Financial & Tax Intelligence.
    </div>
  </div>
</body>
</html>"""

        return cls._send_smtp(to_email, subject, body_text, body_html, raw_otp=otp)

    @classmethod
    def send_password_reset_otp(cls, to_email: str, otp: str) -> bool:
        """Dispatches 6-digit password reset OTP for verified account recovery."""
        subject = "SmartSalary India password reset verification"
        body_text = (
            f"A password reset request was received for your SmartSalary India account.\n\n"
            f"Your 6-digit verification code is: {otp}\n\n"
            f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes. "
            f"If you did not initiate this password reset, please change your password immediately or contact support."
        )
        body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .brand {{ font-size: 20px; font-weight: 700; color: #4f46e5; margin-bottom: 24px; }}
    .alert-banner {{ background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 12px; border-radius: 6px; font-size: 13px; margin-bottom: 16px; }}
    .otp-box {{ background: #f1f5f9; border-radius: 8px; padding: 16px; text-align: center; font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1e293b; margin: 20px 0; }}
    .footer {{ font-size: 12px; color: #64748b; margin-top: 28px; line-height: 1.5; border-top: 1px solid #f1f5f9; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">₹ SmartSalary.IN</div>
    <div class="alert-banner">🔒 Password Reset Request</div>
    <h2 style="font-size: 18px; margin: 0 0 12px 0; color: #0f172a;">Verify your identity to reset password</h2>
    <p style="font-size: 14px; line-height: 1.6; color: #334155; margin: 0 0 16px 0;">
      We received a request to reset your password. Use the 6-digit verification code below to authorize this change:
    </p>
    <div class="otp-box">{otp}</div>
    <p style="font-size: 13px; color: #64748b; margin: 0;">
      ⏱️ This code expires in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>. If you did not make this request, someone may be trying to access your account.
    </p>
    <div class="footer">
      © 2026 SmartSalary India. Statutory Financial & Tax Intelligence.
    </div>
  </div>
</body>
</html>"""

        return cls._send_smtp(to_email, subject, body_text, body_html, raw_otp=otp)
