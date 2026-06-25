# Aprender GitHub Actions

GitHub Actions ejecuta procesos automáticos definidos mediante YAML. GitHub
busca estos archivos en `.github/workflows/`.

## Modelo mental

```text
Evento
  -> Workflow
      -> Job
          -> Step
```

- Evento: lo que inicia la automatización.
- Workflow: archivo YAML completo.
- Job: grupo de pasos ejecutado en un runner.
- Step: comando de shell o action reutilizable.
- Runner: máquina temporal donde se ejecuta el job.

## Eventos

### Push

```yaml
on:
  push:
    branches:
      - main
```

Se ejecuta cuando un commit llega a `main`, incluyendo un merge. Un merge no es
un evento independiente para este caso: normalmente produce un push en la rama
destino.

### Pull request

```yaml
on:
  pull_request:
    branches:
      - main
```

Se ejecuta cuando un pull request dirigido a `main` se abre, sincroniza o
reabre. Sirve para validar antes del merge.

### Tag

```yaml
on:
  push:
    tags:
      - "v*.*.*"
```

Se ejecuta al publicar etiquetas como `v3.1.0`.

### Ejecucion manual

```yaml
on:
  workflow_dispatch:
```

Agrega el botón **Run workflow** en la pestaña Actions.

## Qué ocurre actualmente

| Acción Git | CI | Publicación |
| --- | --- | --- |
| Push a `main` | Sí | No |
| Push a `base_provision` | Sí | No |
| Push a otra rama | No, salvo que exista PR | No |
| Abrir o actualizar un PR | Sí | No |
| Merge hacia `main` | Sí, por el push resultante | No |
| Push del tag `v3.1.0` | No | Sí |
| Botón Run workflow en CI | Sí | No |
| Botón Run workflow en Publish | No | Sí |

## Expresiones `${{ ... }}`

GitHub evalúa expresiones dentro de:

```yaml
${{ ... }}
```

Ejemplos:

```yaml
${{ github.ref }}
${{ github.actor }}
${{ secrets.DOCKERHUB_TOKEN }}
```

`github.ref` identifica la referencia Git que originó la ejecución:

```text
refs/heads/main
refs/heads/base_provision
refs/tags/v3.1.0
```

## Concurrencia

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

La expresión genera grupos como:

```text
ci-refs/heads/main
ci-refs/heads/feature/users
```

Si llegan dos pushes rápidos a la misma referencia, GitHub cancela la ejecución
anterior y conserva la nueva. Una rama distinta utiliza otro grupo.

## `uses` y versiones

Un step puede ejecutar comandos:

```yaml
- run: docker version
```

O utilizar una action:

```yaml
- uses: actions/checkout@v6
```

La forma es:

```text
propietario/repositorio@version
```

`actions/checkout@v6` es una action oficial de GitHub que descarga el
repositorio dentro del runner.

`docker/build-push-action@v6` es una action oficial mantenida por Docker para
construir y publicar imágenes con Buildx.

Las versiones se toman de la documentación y releases del repositorio de cada
action. Antes de actualizar una major version hay que leer sus notas.

Para mayor seguridad, una organización puede fijar una action por commit SHA:

```yaml
- uses: actions/checkout@<commit-sha>
```

## Caché de Docker

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

`type=gha` usa el almacenamiento de caché de GitHub Actions para conservar
capas de BuildKit entre ejecuciones.

- `cache-from`: intenta reutilizar capas existentes.
- `cache-to`: guarda las capas producidas.
- `mode=max`: almacena también capas intermedias, no solo las finales.

Ejemplo: si `requirements.txt` no cambió, Docker puede reutilizar la capa donde
instaló dependencias en vez de descargar todo nuevamente.

La caché:

- No es una imagen publicada.
- No reemplaza Docker Hub.
- Puede desaparecer y el build debe seguir funcionando.
- Mejora velocidad, no la corrección del resultado.

## Cómo aprender sin riesgo

1. Crear una rama:

```bash
git switch -c learn/actions
```

2. Abrir GitHub -> Actions -> CI -> Run workflow.
3. Seleccionar tu rama y ejecutar el workflow manualmente.
4. Abrir el job y leer la salida de sus steps.
5. Provocar el fallo de una prueba.
6. Hacer push y abrir un pull request hacia `main`.
7. Confirmar que el workflow se pone rojo.
8. Corregir la prueba y volver a hacer push.
9. Verificar que el mismo PR cambia a verde.

No crear un tag `vX.Y.Z` durante el ejercicio, porque ese evento publica una
imagen.

## Fuentes oficiales

- [Sintaxis de workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
- [Contextos como `github.ref`](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)
- [`actions/checkout`](https://github.com/actions/checkout)
- [`docker/build-push-action`](https://github.com/docker/build-push-action)
- [Caché Docker para GitHub Actions](https://docs.docker.com/build/ci/github-actions/cache/)
