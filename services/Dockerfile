FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS dependencies
WORKDIR /build
COPY requirements.lock .
RUN pip wheel --timeout 120 --retries 8 --no-cache-dir --wheel-dir /wheels -r requirements.lock

FROM python:3.12.16-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app/services
WORKDIR /app
COPY --from=dependencies /wheels /wheels
COPY requirements.lock .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.lock \
    && rm -rf /wheels && groupadd -g 10001 clinic && useradd -u 10001 -g clinic -M clinic
COPY services services
COPY contracts contracts
COPY alembic.ini .
USER 10001:10001
EXPOSE 8000 8001 8002
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)"
CMD ["python", "-m", "uvicorn", "clinic.api:app", "--host", "0.0.0.0", "--no-access-log"]
