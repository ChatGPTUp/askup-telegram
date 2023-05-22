VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip3
UVICORN = $(VENV)/bin/uvicorn

include .env
export

# Need to use python 3.9 for aws lambda
$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt

init: $(VENV)/bin/activate

app: init
	$(PYTHON) askup.py reload

plugin: init
	$(PYTHON) plugin.py

clean:
	rm -rf __pycache__
	rm -rf $(VENV)
