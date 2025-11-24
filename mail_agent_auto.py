import os
import json
import smtplib
from email.mime.text import MIMEText
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

# Load secrets from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")

# Generic SMTP settings (configured in .env)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "True").lower() == "true"
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "False").lower() == "true"

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment or .env file.")
if not EMAIL_ADDRESS or not EMAIL_APP_PASSWORD:
    raise ValueError("EMAIL_ADDRESS or EMAIL_APP_PASSWORD not set in .env file.")

# OpenAI client (used for both chat + web search)
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def print_rule(char: str = "-", width: int = 48) -> None:
    """Render a single horizontal rule."""
    print(char * width)


def print_section(title: str) -> None:
    """Display a simple section header in the terminal."""
    print_rule()
    print(title)
    print_rule()


def safe_json_loads(text: str) -> Optional[dict]:
    """
    Try to parse JSON robustly from a model response.
    Returns None if parsing fails.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                return None
    return None


def enforce_signature_and_clean(email_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure the body has no bracket placeholders and always ends with:
    Sincerely,
    Bhagyesh
    """
    body = email_obj.get("body", "") or ""

    placeholders = [
        "[Your Name]", "[Your Full Name]", "[Your Name Here]",
        "[Insert Name]", "[Signature]", "[Your Signature]"
    ]
    for ph in placeholders:
        body = body.replace(ph, "Bhagyesh")

    signature_block = "Sincerely,\nBhagyesh"
    if not body.strip().lower().endswith("bhagyesh"):
        body = body.rstrip() + "\n\n" + signature_block

    email_obj["body"] = body
    return email_obj

# ---------------------------------------------------------------------
# Web Search for Professor Email (now returns name + email)
# ---------------------------------------------------------------------

def find_email_from_description(recipient_description: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Use OpenAI Responses API + web_search to find UIC professor name + email.

    Returns:
        {"name": "Full Name", "email": "prof@uic.edu"}  OR  None
    """

    prompt = (
        "You are an assistant that looks up university professors' official email "
        "addresses using web search.\n\n"
        "Assume by default the user is referring to someone at the University of Illinois Chicago (UIC). "
        "Prefer emails ending in 'uic.edu'. The user may type: 'cs professor scott reckinger', "
        "a partially misspelled name, or just a vague description.\n\n"
        "Use web search to infer the correct UIC professor or instructor.\n\n"
        "Return ONLY a JSON object like this:\n"
        "{\"name\": \"Full Professor Name\", \"email\": \"professor@uic.edu\"}\n\n"
        "If no confident match is found, return:\n"
        "{\"name\": null, \"email\": null}\n\n"
        f"Recipient description: {recipient_description}"
    )

    response = client.responses.create(
        model="gpt-4o",
        tools=[{"type": "web_search_preview"}],
        input=prompt,
    )

    raw = getattr(response, "output_text", None)
    if raw is None:
        try:
            raw = response.output[0].content[0].text
        except Exception:
            raw = ""

    data = safe_json_loads(raw)
    if not data:
        print("Could not parse JSON from web search response:")
        print(raw)
        return None

    name = data.get("name")
    email = data.get("email")

    if isinstance(email, str) and "@" in email:
        return {
            "name": name if isinstance(name, str) and name.strip() else None,
            "email": email.strip()
        }

    return None

# ---------------------------------------------------------------------
# Draft + Edit Email
# ---------------------------------------------------------------------

def draft_email(recipient_email: str, user_instruction: str) -> dict:
    """
    Create a clean professional email. No placeholders. Ends with Sincerely, Bhagyesh.
    """

    system_msg = {
        "role": "system",
        "content": (
            "You draft emails. Output ONLY a JSON object with keys: 'to', 'subject', 'body'.\n"
            "'to' must equal the provided recipient email.\n"
            "Subject must be short, clear, professional.\n"
            "Body must be simple, professional, and contain ZERO placeholders like [Your Name].\n"
            "ALWAYS end with:\nSincerely,\nBhagyesh\n"
        )
    }

    user_msg = {
        "role": "user",
        "content": (
            f"Recipient email: {recipient_email}\n\n"
            f"Message details: {user_instruction}"
        )
    }

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[system_msg, user_msg],
        response_format={"type": "json_object"}
    )

    draft = json.loads(response.choices[0].message.content)
    return enforce_signature_and_clean(draft)


def refine_email(existing_email: dict, edit_instruction: str) -> dict:
    """
    Modify subject/body according to user edits.
    """

    system_msg = {
        "role": "system",
        "content": (
            "You edit emails. Output ONLY JSON with keys: 'to', 'subject', 'body'.\n"
            "Keep 'to' unchanged. No placeholders allowed.\n"
            "Maintain clear professional tone.\n"
            "Always end body with 'Sincerely,' then 'Bhagyesh'."
        )
    }

    user_msg = {
        "role": "user",
        "content": (
            "Here is the existing email:\n"
            f"{json.dumps(existing_email)}\n\n"
            f"Edit instructions: {edit_instruction}"
        )
    }

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[system_msg, user_msg],
        response_format={"type": "json_object"}
    )

    updated = json.loads(response.choices[0].message.content)
    return enforce_signature_and_clean(updated)

# ---------------------------------------------------------------------
# Send Email
# ---------------------------------------------------------------------

def send_email_via_smtp(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_APP_PASSWORD)
            server.send_message(msg)

# ---------------------------------------------------------------------
# CLI Loop
# ---------------------------------------------------------------------

def main():
    print_section("Mail Agent · UIC")
    print("Type 'quit' at any time.\n")

    while True:
        print("Recipient Options:")
        print("  • Email address (prof@uic.edu)")
        print("  • Description (\"cs professor scott reckinger\")")
        recipient_raw = input("> ").strip()

        if recipient_raw.lower() in {"quit", "exit"}:
            break

        # Direct email
        if "@" in recipient_raw and "." in recipient_raw:
            recipient_email = recipient_raw
        else:
            print("\nSearching for UIC professor email...\n")
            result = find_email_from_description(recipient_raw)

            if result:
                prof_name = result.get("name") or "Unknown"
                email_found = result["email"]

                print_section("Lookup Result")
                print(f"Name : {prof_name}")
                print(f"Email: {email_found}\n")

                use_it = input("Use this result? (yes/no) ").strip().lower()
                if use_it.startswith("y"):
                    recipient_email = email_found
                else:
                    recipient_email = input("Enter email manually: ").strip()
            else:
                print("No confident match found.")
                recipient_email = input("Enter email manually: ").strip()

        if recipient_email.lower() in {"quit", "exit"}:
            break

        print("\nMessage Details:")
        msg_text = input("> ").strip()
        if msg_text.lower() in {"quit", "exit"}:
            break

        print("\nDrafting email...\n")
        draft = draft_email(recipient_email, msg_text)

        # ----- EDIT LOOP -----
        while True:
            print_section("Email Preview")
            print(f"To     : {draft['to']}")
            print(f"Subject: {draft['subject']}\n")
            print(draft['body'])
            print_rule()

            choice = input(
                "\nOptions:\n"
                "[s] Send\n"
                "[e] Edit\n"
                "[c] Cancel\n> "
            ).strip().lower()

            if choice.startswith("s"):
                try:
                    send_email_via_smtp(draft["to"], draft["subject"], draft["body"])
                    print("Email sent.\n")
                except Exception as e:
                    print("Error sending:", e)
                break

            elif choice.startswith("e"):
                edits = input("Describe changes:\n> ").strip()
                print("\nUpdating...\n")
                draft = refine_email(draft, edits)
                continue

            else:
                print("Cancelled.\n")
                break


if __name__ == "__main__":
    main()
