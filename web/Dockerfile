# ==========================================
# DOCKERFILE - GENERADOR DE ETIQUETAS WEB (PWA)
# ==========================================
FROM python:3.11-slim

LABEL maintainer="Logística y Depósito"
LABEL description="Generador de Etiquetas PWA con Código de Barras e Impresión PDF"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instalar herramientas básicas del sistema (curl para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar aplicación, fuentes y estáticos
COPY main.py .
COPY fonts/ ./fonts/
COPY static/ ./static/
COPY data/ ./data/

# Usuario seguro no-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
