# syntax=docker/dockerfile:1
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then \
      PIP_CERT=/run/secrets/build_ca pip install --no-cache-dir .; \
    else pip install --no-cache-dir .; fi \
    && useradd --create-home appuser \
    && chmod -R a+rX /app
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
