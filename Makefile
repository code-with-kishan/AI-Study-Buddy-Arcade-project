.PHONY: install dev test prod-up prod-down lint health

PYTHON := "/Users/macbook/Desktop/Code_Kishan /AI-Study-Buddy/venv/bin/python"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

dev:
	$(PYTHON) app.py

test:
	$(PYTHON) -m unittest discover -s tests -v

lint:
	$(PYTHON) -m compileall -q .

health:
	curl -s http://127.0.0.1:5000/healthz | cat

prod-up:
	docker compose -f docker-compose.prod.yml up --build

prod-down:
	docker compose -f docker-compose.prod.yml down
