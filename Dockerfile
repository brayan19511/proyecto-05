# Dockerfile
# 1. Imagen base de Python ligera
FROM python:3.11-slim

# 2. Establecer directorio de trabajo
WORKDIR /app

# 3. Evitar que Python genere archivos .pyc y permitir logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 4. Instalar dependencias del sistema (necesarias para psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiar el archivo de requerimientos y luego instalar las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el resto del código de la aplicación
COPY . .
# 7. Exponer el puerto en el que la aplicación se ejecutará
EXPOSE 8000

# 8. Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]