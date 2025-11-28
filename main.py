import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
import os
import datetime
import uuid
import random
import string
import dateparser # pip install dateparser
import pytz       # pip install pytz

load_dotenv()
# --- CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "tech@asklena.ai" 
# Use environment variable or paste the 16-char App Password directly below
SENDER_PASSWORD = os.getenv("EMAIL_PASSWORD", "your-16-char-app-password") 

# YOUR DETAILS (The Host)
HOST_EMAIL = "chitraksha@asklena.ai"
# Go to meet.google.com -> New Meeting -> Create for later -> Paste link here:
PERMANENT_MEETING_LINK = "https://meet.google.com/igx-icor-cnz" 

def parse_meeting_time(raw_time_string):
    """
    Converts human string (e.g., "Nov 29th 5pm PST") into a strict UTC datetime object.
    """
    # Settings: Default to US/Pacific if the user doesn't say a timezone, 
    # but respect it if they do (e.g. "EST").
    settings = {
        'TIMEZONE': 'US/Pacific', 
        'RETURN_AS_TIMEZONE_AWARE': True
    }
    
    dt = dateparser.parse(raw_time_string, settings=settings)
    
    if not dt:
        print(f"❌ Could not parse time: {raw_time_string}")
        return None, None

    # Calculate End Time (15 minute meeting)
    dt_end = dt + datetime.timedelta(minutes=15)

    # Convert both to UTC (Computer Time) for the ICS file
    dt_start_utc = dt.astimezone(pytz.utc)
    dt_end_utc = dt_end.astimezone(pytz.utc)

    return dt_start_utc, dt_end_utc

def get_meeting_link():
    """
    Returns the permanent link if set, otherwise generates a random Google Meet-style URL.
    """
    if PERMANENT_MEETING_LINK and "your-permanent-link" not in PERMANENT_MEETING_LINK:
        return PERMANENT_MEETING_LINK
    
    # Generate a realistic looking random link as fallback
    chars = string.ascii_lowercase
    part1 = ''.join(random.choice(chars) for _ in range(3))
    part2 = ''.join(random.choice(chars) for _ in range(4))
    part3 = ''.join(random.choice(chars) for _ in range(3))
    return f"https://meet.google.com/{part1}-{part2}-{part3}"

def generate_ics_content(user_name, user_email, start_utc, end_utc):
    """
    Creates the text content for the .ics calendar file.
    """
    # Formatting time as YYYYMMDDTHHMMSSZ
    fmt = "%Y%m%dT%H%M%SZ"
    start_str = start_utc.strftime(fmt)
    end_str = end_utc.strftime(fmt)
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime(fmt)
    unique_id = str(uuid.uuid4())

    meet_link = get_meeting_link()

    # The ICS Body
    # We add TWO attendees now: The User AND The Host (Chitraksha)
    ics_body = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Ask Lena AI//Voice Agent//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{unique_id}
DTSTAMP:{now_str}
DTSTART:{start_str}
DTEND:{end_str}
SUMMARY:Voice AI Strategy Call: {user_name} <> Ask Lena
DESCRIPTION:Hi {user_name},\\n\\nThis is the technical discovery call you booked with Lena.\\n\\nHost: Chitraksha ({HOST_EMAIL})\\n\\nJoin the Google Meet here: {meet_link}
LOCATION:{meet_link}
ORGANIZER;CN=Ask Lena AI:mailto:{SENDER_EMAIL}
ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;CN={user_name}:mailto:{user_email}
ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;CN=Chitraksha:mailto:{HOST_EMAIL}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    return ics_body

def send_calendar_invite(user_name, user_email, raw_time_string):
    
    print(f"🤖 Processing invite for: {raw_time_string}...")

    # 1. Parse Time
    start_utc, end_utc = parse_meeting_time(raw_time_string)
    if not start_utc:
        return

    # 2. Prepare Email Body (HTML)
    try:
        with open("email_template.html", "r", encoding="utf-8") as f:
            html_content = f.read()
    except FileNotFoundError:
        print("❌ Error: 'email_template.html' not found.")
        return

    # Inject data into HTML
    personalized_html = html_content.replace("{user_name}", user_name)
    personalized_html = personalized_html.replace("{meeting_time}", raw_time_string)
    personalized_html = personalized_html.replace("{GOOGLE_MEET_LINK_HERE}",PERMANENT_MEETING_LINK)

    # 3. Construct Email
    msg = MIMEMultipart("mixed") 
    msg["Subject"] = f"Invitation: Tech Discovery Call with {user_name}"
    msg["From"] = f"Lena (Ask Lena AI) <{SENDER_EMAIL}>"
    # IMPORTANT: We send the email to the USER. 
    # (Chitraksha gets the calendar notification automatically via the ICS file logic, 
    # but we can also CC Chitraksha if we want to be safe)
    msg["To"] = user_email
    msg["Cc"] = HOST_EMAIL

    # 4. Attach HTML Content
    msg_html = MIMEMultipart("alternative")
    msg_html.attach(MIMEText(personalized_html, "html"))
    msg.attach(msg_html)

    # 5. Generate & Attach ICS File
    ics_content = generate_ics_content(user_name, user_email, start_utc, end_utc)
    
    part_ics = MIMEBase("text", "calendar", method="REQUEST", name="invite.ics")
    part_ics.set_payload(ics_content)
    encoders.encode_base64(part_ics)
    part_ics.add_header('Content-Description', 'Meeting Invitation')
    part_ics.add_header('Content-class', 'urn:content-classes:calendarmessage')
    
    msg.attach(part_ics)

    # 6. Send
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        # We must send to both the user AND the host in the "sendmail" function
        recipients = [user_email, HOST_EMAIL]
        
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        print(f"✅ Invite sent to {user_email} (and copied {HOST_EMAIL})")
    except smtplib.SMTPAuthenticationError:
        print("❌ Auth Error: Check App Password.")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

# --- TEST AREA ---
if __name__ == "__main__":
    # Test with the specific Timezone case you asked for:
    
    test_name = "Kaushal"
    test_email = "chitraksha@developmentunited.com" # <--- PUT YOUR REAL EMAIL HERE TO TEST
    
    # "Nov 29th 5pm PST"
    # The script will convert this to UTC and set the calendar correctly
    test_time = "November 29th 2025 at 5:00 PM PST"

    send_calendar_invite(test_name, test_email, test_time)