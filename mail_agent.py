import os
import json
import subprocess
import sys
import webbrowser
import urllib.parse
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

# Load secrets from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  # your UIC email (for info/logging only)

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in environment or .env file.")
if not EMAIL_ADDRESS:
    raise ValueError("EMAIL_ADDRESS not set in .env file (set to your UIC email).")

# OpenAI client (used for both chat + web search)
client = OpenAI(api_key=OPENAI_API_KEY)


def print_rule(char: str = "-", width: int = 48) -> None:
    """Render a simple horizontal separator."""
    print(char * width)


def print_section(title: str) -> None:
    """Render a section heading surrounded by separators."""
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
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def enforce_signature_and_clean(email_obj: dict) -> dict:
    """
    Remove placeholders and ensure the body closes with Best Regards, Bhagyesh.
    """
    body = email_obj.get("body", "") or ""

    placeholders = [
        "[Your Name]", "[Your Full Name]", "[Your Name Here]",
        "[Insert Name]", "[Signature]", "[Your Signature]",
        "{Your Name}", "{Signature}"
    ]
    for token in placeholders:
        body = body.replace(token, "Bhagyesh")

    closing = "Best Regards,\nBhagyesh"
    if closing.lower() not in body.strip().lower():
        body = body.rstrip() + "\n\n" + closing

    email_obj["body"] = body
    return email_obj


def find_email_from_description(recipient_description: str) -> Optional[dict]:
    """
    Use OpenAI Responses API + web_search to find an official academic email
    and professor name from a natural-language description like:
      'Prof Jane Doe, CS 211, UIC'
    Returns {"name": str, "email": str, "department": Optional[str], "candidates": list} or None if not confident.
    """

    prompt = (
        "You are an assistant that looks up university professors' official email "
        "addresses using web search.\n\n"
        "The user will describe who they want to email (name, course, university, etc.).\n"
        "Descriptions may include typos or partial information. First, reason about "
        "the most likely intended University of Illinois Chicago professor and correct spelling, then search.\n\n"
        "Use the web_search_preview tool to gather evidence from official University of Illinois Chicago pages "
        "or sources that clearly list the professor's email. Prefer addresses ending with 'uic.edu'.\n"
        "Double-check that the email matches the inferred professor before returning it.\n"
        "Only answer if you have high confidence AND the email ends with 'uic.edu'; otherwise respond with no matches.\n\n"
        "Return ONLY a JSON object like:\n"
        "{\n"
        '  "matches": [\n'
        '    {"name": "Professor Full Name", "department": "Department or course", "email": "name@uic.edu", "confidence": 0.0-1.0}\n'
        "  ]\n"
        "}\n\n"
        "List the most confident match first. If you cannot find a reliable match, return:\n"
        '{"matches": []}\n\n'
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
    if not isinstance(data, dict):
        print("Lookup error. Please refine the professor description.")
        return None

    matches = data.get("matches")
    if not isinstance(matches, list):
        print("Lookup error. Please refine the professor description.")
        return None

    valid_matches = []
    for entry in matches:
        if not isinstance(entry, dict):
            continue
        email = entry.get("email")
        name = entry.get("name")
        department = entry.get("department")
        if not isinstance(email, str) or "@" not in email:
            continue
        email_clean = email.strip()
        if not email_clean.lower().endswith("uic.edu"):
            continue
        clean_name = name.strip() if isinstance(name, str) and name.strip() else None
        clean_department = department.strip() if isinstance(department, str) and department.strip() else None
        valid_matches.append(
            {
                "name": clean_name,
                "department": clean_department,
                "email": email_clean,
            }
        )

    if not valid_matches:
        print("No reliable UIC email found for that description.")
        return None

    primary = dict(valid_matches[0])
    primary["candidates"] = valid_matches
    return primary


def draft_email(recipient_email: str, user_instruction: str, recipient_name: Optional[str] = None) -> dict:
    """
    Ask GPT (chat completions) to draft an email.
    Returns a dict with keys: to, subject, body
    """

    if recipient_name:
        salutation_rule = (
            "Use the provided recipient name exactly for the salutation (e.g., 'Dear Dr. Smith,').\n"
            f"The recipient name is: {recipient_name}\n"
        )
    else:
        salutation_rule = (
            "No specific recipient name is available. Use a generic greeting like 'Hello Professor,' "
            "without guessing or repeating the email address.\n"
        )

    system_msg = {
        "role": "system",
        "content": (
            "You are an email drafting assistant.\n"
            "You will be given a recipient email and a description of what the user wants.\n"
            "Return ONLY a JSON object with exactly these keys: 'to', 'subject', 'body'.\n"
            "'to' must be exactly the recipient email given.\n"
            "'subject' should be a short line (<= 80 characters).\n"
            "'body' should be a polite, clear email body in plain text.\n"
            f"{salutation_rule}"
            "Never include placeholders such as [Your Name].\n"
            "Always end the body with:\nBest Regards,\nBhagyesh\n"
            "Do NOT include markdown, explanations, or extra keys."
        ),
    }

    recipient_name_line = (
        f"Recipient name (if known): {recipient_name}\n"
        if recipient_name else
        "Recipient name (if known): Unknown\n"
    )

    user_msg = {
        "role": "user",
        "content": (
            f"Recipient email: {recipient_email}\n\n"
            f"{recipient_name_line}\n"
            f"What I want to say: {user_instruction}"
        ),
    }

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[system_msg, user_msg],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    draft = json.loads(content)
    return enforce_signature_and_clean(draft)


def open_in_mail_client(to: str, subject: str, body: str) -> None:
    """
    Open the default mail client with a pre-filled email using a mailto: link.
    The actual sending is done by the user in their email app (e.g. Outlook, Mail).
    """

    # Encode for URL
    to_enc = urllib.parse.quote(to, safe="@")
    subject_enc = urllib.parse.quote(subject)
    body_enc = urllib.parse.quote(body)

    mailto_url = f"mailto:{to_enc}?subject={subject_enc}&body={body_enc}"

    if sys.platform == "darwin":
        try:
            subprocess.run(["open", "-a", "Mail", mailto_url], check=True)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("Could not launch Mail app directly, falling back to default handler.")

    webbrowser.open(mailto_url)


def main():
    print_section("Mail Agent · UIC")
    print(f"Sender: {EMAIL_ADDRESS}")
    print("Type 'quit' anytime to exit.\n")

    while True:
        recipient_name = None
        print("Recipient options:")
        print("  - Email address (prof@uic.edu)")
        print("  - Description (\"Prof Jane Doe, CS 211, UIC\")")
        recipient_raw = input("> ").strip()

        if recipient_raw.lower() in {"quit", "exit"}:
            break

        # If it already looks like an email, just use it.
        if "@" in recipient_raw and "." in recipient_raw:
            recipient_email = recipient_raw
        else:
            # Try to find via web search
            recipient_email = None
            current_description = recipient_raw

            while current_description:
                print("\nSearching for their email address...\n")
                lookup = find_email_from_description(current_description)

                if lookup:
                    prof_name = lookup.get("name") or "Unknown"
                    prof_dept = lookup.get("department") or "Department not provided"
                    email_found = lookup["email"]
                    print_section("Lookup Result")
                    print(f"Professor Name: {prof_name}")
                    print(f"Department    : {prof_dept}")
                    print(f"Email         : {email_found}")

                    candidates = lookup.get("candidates") or []
                    normalized_primary = (prof_name or "").strip().lower()
                    same_name_candidates = [
                        c for c in candidates
                        if isinstance(c, dict)
                        and (c.get("name") or "").strip().lower() == normalized_primary
                        and c.get("email")
                    ]
                    if len(same_name_candidates) > 1:
                        print_rule()
                        print("Multiple professors share this name:")
                        for idx, cand in enumerate(same_name_candidates, 1):
                            dept = cand.get("department") or "Department not provided"
                            email = cand.get("email")
                            print(f"{idx}. {cand.get('name') or 'Unknown'} — {dept} — {email}")

                    print_rule()
                    use_found = input("Use this email? (yes/no) ").strip().lower()
                    if use_found.startswith("y"):
                        recipient_email = email_found
                        recipient_name = prof_name if prof_name != "Unknown" else None
                        break

                    manual_entry = input("Enter the email manually (press Enter to leave blank): ").strip()
                    if manual_entry.lower() in {"quit", "exit"}:
                        return
                    if manual_entry:
                        recipient_email = manual_entry
                        recipient_name = prof_name if prof_name != "Unknown" else None
                        break
                    recipient_email = ""
                    recipient_name = prof_name if prof_name != "Unknown" else None
                    print("Continuing without a pre-filled email. You can add it in Mail.\n")
                    break

                print("Failed to find professor.")
                retry = input(
                    "Type the professor name/description to retry (press Enter to skip lookup): "
                ).strip()
                if retry.lower() in {"quit", "exit"}:
                    return
                if retry:
                    current_description = retry
                    continue

                manual_entry = input("Type the email address manually (press Enter to leave blank): ").strip()
                if manual_entry.lower() in {"quit", "exit"}:
                    return
                if manual_entry:
                    recipient_email = manual_entry
                    recipient_name = None
                    break
                recipient_email = ""
                recipient_name = None
                print("Continuing without a pre-filled email. You can add it in Mail.\n")
                break

            if recipient_email is None:
                continue

        if recipient_email.lower() in {"quit", "exit"}:
            break

        print("\nMessage details:")
        description = input("> ").strip()
        if description.lower() in {"quit", "exit"}:
            break

        print("\nDrafting email...\n")
        try:
            draft = draft_email(recipient_email, description, recipient_name)
        except Exception as e:
            print("Error talking to GPT:", e)
            continue

        while True:
            print_section("Email Draft")
            print(f"To     : {draft['to']}")
            print(f"Subject: {draft['subject']}\n")
            print(draft["body"])
            print_rule()

            choice = input(
                "\nChoose an option:\n"
                "  [o] Open in Mail app\n"
                "  [e] Edit this message\n"
                "  [c] Cancel\n> "
            ).strip().lower()

            if choice.startswith("o"):
                try:
                    open_in_mail_client(draft["to"], draft["subject"], draft["body"])
                    print("Opened in your default mail app. Review and send there.\n")
                except Exception as e:
                    print("Error opening mail client:", e, "\n")
                break

            if choice.startswith("e"):
                print("\nDescribe the edits you'd like (enter to cancel editing):")
                new_description = input("> ").strip()
                if not new_description:
                    continue
                description = new_description
                print("\nUpdating draft...\n")
                try:
                    draft = draft_email(recipient_email, description, recipient_name)
                except Exception as e:
                    print("Error talking to GPT:", e)
                continue

            print("Draft not opened.\n")
            break


if __name__ == "__main__":
    main()
