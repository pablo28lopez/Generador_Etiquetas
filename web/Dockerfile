# ==========================================
# DOCKERFILE - GENERADOR DE ETIQUETAS WEB (PWA)
# ==========================================
FROM python:3.11-slim

LABEL maintainer="Logística y Depósito - DLS Archer"
LABEL description="Generador de Etiquetas PWA con Código de Barras e Impresión Térmica Directa Brother QL"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Instalar herramientas del sistema:
# - curl: para el healthcheck del contenedor
# - smbclient: para imprimir en impresoras compartidas Windows (\\IP\Brother QL-800) desde Linux
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    smbclient \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar aplicación, módulos, fuentes, logos y estáticos
COPY main.py brother_raw.py logo.png ./
COPY fonts/ ./fonts/
COPY static/ ./static/
COPY data/ ./data/

# Crear usuario seguro no-root con permisos de escritura sobre /app/data
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
