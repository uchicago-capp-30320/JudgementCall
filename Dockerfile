# uv docker image based on Debian bookworm
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# python env variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# PostgreSQL
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libpq5 \
#     && rm -rf /var/lib/apt/lists/*

# expose code as /app
ADD . /app
WORKDIR /app

# hand over directory to django user
RUN useradd -m -u 1000 django
RUN chown -R django:django /app
USER django

# uv setup
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# make directories
RUN mkdir -p /app/_logs/

# static files built into image
ENV DEBUG=true
RUN python manage.py collectstatic --noinput
# can be overriden in compose
ENV DEBUG=false

# expose app on 8000
ENTRYPOINT []
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--preload", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "60"]
