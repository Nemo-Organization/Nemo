FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

RUN pip install --no-cache-dir uv==0.13.9 \
    && groupadd --gid 10001 guardian \
    && useradd --uid 10001 --gid guardian --create-home guardian

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations

USER guardian
EXPOSE 8080

CMD ["python", "-m", "app"]
