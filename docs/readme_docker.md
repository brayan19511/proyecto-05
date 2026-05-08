# Guía de levantar proyecto - Proyecto-05
# 1. Clonar el repositorio
```
git clone https://github.com/brayan19511/proyecto-05.git
cd proyecto-05
```
# 2. Configurar variables de entorno
Copiar el template y completar los datos sensibles (DB Passwords, JWT Secrets, etc.):
```
cp .env.template .env
nano .env  # O usa tu editor preferido
-o-
copy .env.template .env
notepad .env  # O usa tu editor preferido


```
# 3. Actualizar y Construir
Asegúrate de tener la última versión del código y levanta los servicios:
```
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```
desarrollo
```
docker compose up -d 
```
# 4. realizar migraciones
revisar contenedor de api
```
docker ps
``` 
una vez identificado realizar 
``` 
docker exec -it proyecto-05-api-1 python -m alembic upgrade head
``` 


# 4. Verificación (Opcional pero Recomendado)
Para confirmar que la API y el sistema de auditoría iniciaron correctamente, revisa los logs:
```
docker logs -f api
```
(Si usas migraciones de base de datos con Alembic, recuerda ejecutar: docker exec -it api alembic upgrade head).

