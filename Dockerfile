# 1. Imagen base de Python ligera
FROM python:3.11-slim

# 2. Establecer directorio de trabajo
WORKDIR /app

# 3. Evitar que Python genere archivos .pyc y permitir logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 4. Instalar dependencias del sistema (¡AQUÍ AGREGAMOS CURL Y GNUPG2!)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# 4.1 Agregar repo de Microsoft (Usa 'bullseye' para v17 o 'bookworm' para v18)
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] \
        https://packages.microsoft.com/debian/11/prod bullseye main" \
        > /etc/apt/sources.list.d/mssql-release.list

# 4.2 Instalar driver SQL Server (msodbcsql17 o msodbcsql18)
RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

# 5. Copiar el archivo de requerimientos y luego instalar las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el resto del código de la aplicación
COPY . .

# 7. Exponer el puerto en el que la aplicación se ejecutará
EXPOSE 8000

# 8. Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]