import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()
def send_confirmation_email(user_name, user_email, meeting_time):
    """
    Sends a formatted HTML confirmation email to the user.
    """
    
    # 1. Configuration (Ideally, store these in environment variables)
    SMTP_SERVER = "smtp.gmail.com" # Example: Gmail, SendGrid, AWS SES
    SMTP_PORT = 587
    SENDER_EMAIL = "tech@asklena.ai"
    # IMPORTANT: Use an App Password if using Gmail, not your login password
    SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD") 

    # 2. Load the HTML Template
    try:
        with open("email_template.html", "r", encoding="utf-8") as f:
            html_content = f.read()
    except FileNotFoundError:
        print("Error: 'email_template.html' not found.")
        return

    # 3. Inject User Data into the Template
    # This replaces {user_name} and {meeting_time} in the HTML file
    personalized_html = html_content.replace("{user_name}", user_name)
    personalized_html = personalized_html.replace("{meeting_time}", meeting_time)

    # 4. Construct the Email Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Confirmation: Tech Discovery Call with {user_name}"
    msg["From"] = f"Lena (AskLena.AI) <{SENDER_EMAIL}>"
    msg["To"] = user_email

    # Attach both plain text (fallback) and HTML versions
    text_part = MIMEText(f"Hi {user_name}, your meeting is confirmed for {meeting_time}.", "plain")
    html_part = MIMEText(personalized_html, "html")

    msg.attach(text_part)
    msg.attach(html_part)

    # 5. Send the Email
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls() # Secure the connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, user_email, msg.as_string())
        server.quit()
        print(f"✅ Email successfully sent to {user_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Example Usage (For Testing) ---
if __name__ == "__main__":
    # In a real app, these values come from the AI Agent's tool output
    fake_user_name = "Chitraksha Sharma"
    fake_user_email = "chitraksha@developmentunited.com"
    fake_meeting_time = "Thursday, November 30th at 2:00 PM EST"

    send_confirmation_email(fake_user_name, fake_user_email, fake_meeting_time)