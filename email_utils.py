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
