
all:
	@echo "Starting ..." \
	&& uv venv --clear && source .venv/bin/activate  \
	&& uv run uvicorn backend.main:app --reload
