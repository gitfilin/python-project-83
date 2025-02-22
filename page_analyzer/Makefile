install:
	uv sync

dev:
	uv run flask --debug --app page_analyzer:app run

lint:
	uv lint

test:
	uv test

PORT ?= 8000
start:
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

render-start:
	/opt/render/project/src/.venv/bin/gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

build:
	./build.sh

