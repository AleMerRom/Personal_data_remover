PYTHON = venv/bin/python3
PIP = venv/bin/pip

ifneq (,$(wildcard .env))
	include .env
	export
endif

venv:
	python3 -m venv venv

install: venv
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py

check:
	$(PYTHON) check_replies.py

summary:
	$(PYTHON) tracker.py --summary
