FROM python:3.12.3-slim-bookworm AS base
WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy
ENV PATH="/workspace/.venv/bin:/root/.local/bin:${PATH}"

RUN pip install --no-cache-dir --break-system-packages uv==0.11.26

COPY .python-version pyproject.toml uv.lock README.md ./
COPY services ./services

RUN uv sync --frozen --no-dev --all-packages --no-editable \
    && useradd --create-home --uid 10001 appuser

USER appuser
CMD ["python", "-m", "zayd_service_worker.main"]
