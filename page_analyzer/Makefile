install:
	uv sync

requirements:
	cd .. && uv pip compile page_analyzer/pyproject.toml -o requirements.txt

dev:
	uv run flask --debug --app app run

lint:
	uv lint

test:
	uv test

PORT ?= 8000
start:
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) app:app

render-start:
	gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app
	