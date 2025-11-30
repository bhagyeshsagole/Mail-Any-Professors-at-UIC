# UIC Mail Agent

Draft polished emails to University of Illinois Chicago faculty with a single prompt. The agent can look up official `uic.edu` addresses, generate a professional email that always ends with your signature, and open it in your default mail client so you can review and send it yourself. An optional automated mode is included if you want the script to send the email through SMTP after you approve it.

## Features
- Interactive CLI that accepts either a professor's email or a natural-language description (course, department, name) and performs a web search to locate the correct address.
- GPT-generated drafts that follow a consistent tone, enforce the closing signature, and never leave `[Your Name]` placeholders behind.
- `mailto:` launcher that pops the draft into your preferred email client for final edits and sending.
- Optional `mail_agent_auto.py` workflow that can deliver the message through your SMTP account once you've configured an app password.

## Requirements
- Python 3.10+ (tested on macOS and Linux; Windows works via the manual commands below).
- OpenAI API key with access to `gpt-4o` or compatible Responses API models.
- `make` (installed by default on macOS/Linux; Windows users can skip it and run the equivalent Python commands).
- For the automated sender: SMTP credentials (e.g., Gmail address + app password).

## Setup
1. **Clone & enter the project**
   ```bash
   git clone https://github.com/your-org/mail-agent.git
   cd mail-agent
   ```
2. **Create your environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in:
   - `OPENAI_API_KEY` – your OpenAI key.
   - `EMAIL_ADDRESS` – the UIC email that appears in the draft footer.
   - (Optional) `EMAIL_APP_PASSWORD` and SMTP settings if you plan to use the automated sender.
3. **Install dependencies**
   - Recommended (POSIX): `make setup`
   - Manual alternative:
     ```bash
     python3 -m venv .venv
     . .venv/bin/activate
     pip install -r requirements.txt
     ```
   - Windows PowerShell:
     ```powershell
     py -3 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     ```

## Running the interactive agent
- **From the terminal (any OS)**
  ```bash
  make mail
  ```
  or (if you skipped `make`):
  ```bash
  . .venv/bin/activate   # On Windows: .\.venv\Scripts\activate
  python mail_agent.py
  ```
- **macOS double-click launcher**
  - Double-click `MailAgent.command`. On the first run it will bootstrap the virtual environment automatically, then start the CLI.

During the session you can type either:
- A full email address (`professor@uic.edu`), or
- A description such as `Prof Smith, CS 211 instructor`.

The agent shows the lookup results, drafts the email, and lets you:
1. Open it in your Mail app (`mailto:` link) to send manually.
2. Ask for edits and regenerate.
3. Cancel and start over.

## Automated sender (optional)
Once `.env` also contains `EMAIL_APP_PASSWORD` plus any custom SMTP settings, you can let the agent send the email via SMTP after drafting:
```bash
make mail-auto
```
or, without `make`:
```bash
. .venv/bin/activate
python mail_agent_auto.py
```
The automated flow still asks you to review each draft and confirm before sending.

## Keeping it working on other machines
- Remember not to commit your real `.env`. Ship `.env.example` so your friends can copy it.
- The Makefile / `.command` script only touches files inside the repo, so the project stays portable.
- If someone hits dependency issues, deleting `.venv` and rerunning `make setup` will recreate the virtual environment with a clean install.

## Video
[![Watch the video](https://img.youtube.com/vi/5Hhbuk2VwBc/hqdefault.jpg)](https://youtu.be/5Hhbuk2VwBc)
