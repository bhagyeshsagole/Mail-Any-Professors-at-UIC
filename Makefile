PY ?= python3
VENV_DIR ?= .venv
VENV_PY := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

.PHONY: setup mail mail-auto

# One-time setup:
#   make setup
setup:
	$(PY) -m venv $(VENV_DIR)
	$(VENV_PIP) install -r requirements.txt

# Run interactive mail agent
#   make mail
mail:
	$(VENV_PY) mail_agent.py

# Run auto variant
#   make mail-auto
mail-auto:
	$(VENV_PY) mail_agent_auto.py
