import aiosmtplip
from Email.message import EmailMessage
from config import Settings
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=templates)


async def send_email(
    to_mail: str
    subject: str
    plain_text: str
    html_content: str | None = None
) -> None:
message = EmailMessage()

message["FROM"] = settings.mail_from
message["TO"] = to_mail
message["SUBJECT"] = subject
message.set_content(plain_text)

if html_content:
    message.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        hostname=settings.mail_server
        port=settings.mail_port
        username=settings.mail_username
        password=settings.mail_password
        start_tls=settings.mail_use_tls
    )


async set_password_reset_email(to_mail: str, username: str, token:str ) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"

    template = templates.env.get_template("email/password_reset.html")

    html_content = template.render(reset_url=reset_url, username=username)

    plain_text = f"""Hi {username}
    You requested to reset your password. Click the link below to set a new password:

{reset_url}

This link will expire in 1 hour.

If you didn't request this, you can safely ignore this email.

Best regards,
The FastAPI Blog Team
"""

    await send_email(
        to_mail=to_mail,
        subject="Reset Your Password - ShareBlog",
        plain_text=plain_text,
        html_content=html_content
    )