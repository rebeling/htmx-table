
up:
	@echo "Starting ..." \
	&& uv venv --clear && source .venv/bin/activate  \
	&& uv run uvicorn backend.main:app --reload

build:
	@echo "Building ..." \
	&& uv venv --clear && source .venv/bin/activate  \
	&& uv sync
