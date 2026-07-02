# Workflows del proyecto

## CI

Archivo: `.github/workflows/ci.yml`.

### Disparadores

```yaml
on:
  pull_request:
  push:
    branches:
      - main
      - base_provision
  workflow_dispatch:
```

- Cualquier pull request ejecuta CI.
- Los pushes directos solo lo ejecutan en `main` y `base_provision`.
- `workflow_dispatch` permite ejecutarlo manualmente desde GitHub.

### Runner

```yaml
runs-on: ubuntu-latest
```

GitHub crea una máquina Linux temporal. Se elimina al terminar el job.

### Checkout

```yaml
- uses: actions/checkout@v6
```

Descarga el commit que se está evaluando.

### Buildx

```yaml
- uses: docker/setup-buildx-action@v3
```

Configura Docker Buildx, necesario para caché avanzada y builds reproducibles.

### Imagen de pruebas

```yaml
- uses: docker/build-push-action@v6
  with:
    context: .
    target: test
    load: true
    tags: backend-finance:test
```

- `context: .`: envía el repositorio según `.dockerignore`.
- `target: test`: construye la etapa de pruebas del Dockerfile.
- `load: true`: carga la imagen en Docker local del runner.
- `tags`: nombre temporal; no se publica.

### Pruebas

El siguiente step ejecuta el `CMD` del target `test`:

```yaml
docker run --rm ... backend-finance:test
```

Si una prueba falla, el proceso devuelve un código distinto de cero y el job
falla.

### OpenAPI

El último step importa `app.main`, genera OpenAPI y verifica que existan rutas.
Esto detecta imports circulares, routers rotos y contratos que no cargan.

## Publish backend image

Archivo: `.github/workflows/publish.yml`.

### Disparadores

```yaml
on:
  push:
    tags:
      - "v*.*.*"
  workflow_dispatch:
```

Se ejecuta con un tag semántico o manualmente.

### Dependencia entre jobs

```yaml
publish:
  needs: test
```

La imagen no se publica si el job `test` falla.

### Environment

```yaml
environment: production
```

El job utiliza el environment `production`. GitHub puede exigir aprobación y
limitar sus secretos a este job.

### Login

```yaml
- uses: docker/login-action@v3
```

Inicia sesión en Docker Hub mediante:

```yaml
${{ secrets.DOCKERHUB_USERNAME }}
${{ secrets.DOCKERHUB_TOKEN }}
```

### Metadata

`docker/metadata-action` transforma el tag Git en etiquetas Docker.

Para `v3.1.0` genera, entre otras:

```text
backend-finance:3.1.0
backend-finance:3.1
backend-finance:sha-...
```

### Publicación

```yaml
target: production
push: true
```

Construye la etapa productiva y la publica. Nunca debe publicar el target
`test`, porque ese target ejecuta `unittest` en lugar de Uvicorn.

## Testeo manual previo

Antes de hacer push:

```bash
docker build --target test -t backend-finance:test .
docker run --rm \
  -e DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/test \
  -e JWT_SECRET=ci-secret \
  -e DB_SAP_USER=ci \
  -e DB_SAP_PASSWORD=ci \
  -e DB_SAP_HOST=localhost \
  -e DB_SAP_PORT=30015 \
  -e SAP_URL=https://localhost:50000/b1s/v1 \
  backend-finance:test
```

Para publicar de forma manual:

```bash
docker build --target production \
  -t brayan1951/backend-finance:v3.1.0 .
docker push brayan1951/backend-finance:v3.1.0
```

## Evolución recomendada

1. Mantener CI obligatorio en pull requests.
2. Proteger `main` para impedir merge cuando CI falla.
3. Publicar únicamente mediante tags.
4. Mantener el despliegue manual mientras se aprende.
5. Añadir despliegue automático con aprobación posteriormente.
