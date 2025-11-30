# UIC Mail Agent: A Build Log

I wrote the **UIC Mail Agent** after too many late nights hunting for the right University of Illinois Chicago professor and agonizing over polite wording. This README doubles as a blog post: it tells the story of how I stand up the agent on any computer and the exact steps I follow from blank folder to first email.

## Step 0 – Picture the goal
Before touching code, I reminded myself what success looks like:
- Type a clue like "CS 211 Monday lecture" or provide a direct `uic.edu` address.
- Let the agent confirm the right faculty contact, draft a respectful message in my voice, and make sure my signature is already attached.
- Choose whether the draft opens in my default mail client (`mailto:` link) or send it automatically after I approve it.

## Step 1 – Gather the toolkit
I make sure the basics are installed so nothing surprises me mid-setup:
- Python 3.10 or newer (macOS and Linux by default, Windows via PowerShell).
- An OpenAI API key that can reach `gpt-4o` or another Responses API model.
- `make` (optional but speeds up bootstrapping).
- SMTP credentials (email + app password) only if I expect to use the automatic sender.

## Step 2 – Clone the repo
```bash
git clone https://github.com/your-org/mail-agent.git
cd mail-agent
```
Everything in this story happens from inside that folder.

## Step 3 – Teach the agent who I am
The environment template ships with the repo. I copy and customize it so the agent knows my identity:
```bash
cp .env.example .env
```
Inside `.env` I fill out:
- `OPENAI_API_KEY` so GPT can draft messages.
- `EMAIL_ADDRESS` so the closing signature matches my inbox.
- Optional SMTP fields (`EMAIL_APP_PASSWORD`, host, port) in case I want automated delivery later.

## Step 4 – Install dependencies
If `make` exists, I let it handle everything:
```bash
make setup
```
On systems without `make`, I recreate the same steps manually:
```bash
python3 -m venv .venv
. .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Either route leaves a `.venv` directory that isolates Python packages for the agent.

## Step 5 – Start chatting with professors
Time to run the interactive helper:
```bash
make mail
```
When I cannot rely on `make`, I launch it directly:
```bash
. .venv/bin/activate   # Windows: .\.venv\Scripts\activate
python mail_agent.py
```
During a session I can paste a full email address or write something like `Professor Ortiz, BioE 310 lab`. The CLI shows the lookup, drafts the message, and keeps iterating until I approve it. One keypress opens the draft in my default mail client.

## Step 6 – Mac shortcut for busy mornings
On macOS I prefer double-clicking when I am running between meetings. I give the launcher execute permissions once:
```bash
chmod +x MailAgent.command
```
From then on, opening `MailAgent.command` spins up the virtual environment (if missing) and launches the same CLI without touching Terminal.

## Step 7 – Flip on autopilot (optional)
When I have SMTP credentials ready and want the script to send the message after approval, I run:
```bash
make mail-auto
```
or, without `make`:
```bash
. .venv/bin/activate
python mail_agent_auto.py
```
The automated mode still pauses so I can read the draft, then hands the message to the SMTP server and prints a status update.

## Step 8 – Keep the project tidy
A few maintenance rituals keep deployments painless:
- Never commit `.env`; share `.env.example` instead.
- If dependencies act up, delete `.venv` and rerun `make setup` for a clean slate.
- The Makefile and `.command` script only touch files inside the repo, so syncing the folder between machines is safe.

## Step 9 – Experiment and share
Once the workflow works, I try new prompts, switch SMTP providers, or tweak the drafting tone. Every iteration returns to the same checklist above, so this README remains both a setup manual and a narrative of how the UIC Mail Agent keeps my outreach fast and courteous.

## Video
[![Watch the video](https://img.youtube.com/vi/5Hhbuk2VwBc/hqdefault.jpg)](https://youtu.be/5Hhbuk2VwBc)
