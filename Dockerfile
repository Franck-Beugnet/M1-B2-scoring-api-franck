# Dockerfile — M1-B2 Pyrenex Risk API

# 1. Base image 
FROM python:3.11-slim

# 2. User non-root
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser


# 3. Working directory
WORKDIR /home/appuser/app

# 4. Dépendances en premier (cache layer)
COPY --chown=appuser:appuser requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Code applicatif
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser models/ ./models/
RUN mkdir -p ./logs && chown -R appuser:appuser /home/appuser/app

# 6. Passer au user appuser
USER appuser

# 7. Port exposé (documentaire)
EXPOSE 8000

# 8. Healthcheck (cf. mini-cours 02)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"


# 9. CMD uvicorn (en forme exec, --host 0.0.0.0, port 8000)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
