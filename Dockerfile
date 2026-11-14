# Imagen del pipeline TLC: Python + Java + PySpark local + cliente de BigQuery.
# Spark corre en modo local dentro del contenedor (sin clúster, sin costo de nube).
ARG IMAGEN_BASE=python:3.13-slim-bookworm
FROM ${IMAGEN_BASE}

# Java 17: requerido por Spark 4.0. procps: Spark usa "ps" para administrar procesos.
ARG PAQUETE_JAVA=openjdk-17-jre-headless
RUN apt-get update \
 && apt-get install -y --no-install-recommends ${PAQUETE_JAVA} procps curl \
 && rm -rf /var/lib/apt/lists/*

# Usuario con el mismo UID/GID del usuario del host, para que los archivos
# que escribe el contenedor en plata/ y oro/ sigan siendo tuyos.
ARG UID=1000
ARG GID=1000
RUN groupadd -g ${GID} datos 2>/dev/null || true \
 && useradd -m -u ${UID} -g ${GID} -s /bin/bash datos

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYSPARK_PYTHON=python3

USER datos
CMD ["python", "-m", "tlc.reconocimiento"]
