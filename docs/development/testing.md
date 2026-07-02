# Pruebas

## Ejecutar localmente con Docker

Con los servicios levantados:

```bash
docker compose exec api \
  python -m unittest discover -s tests -p "test_*.py" -v
```

Compilar los modulos:

```bash
docker compose exec api python -m compileall -q app tests
```

Validar OpenAPI:

```bash
docker compose exec api python -c \
  "from app.main import app; print(len(app.openapi()['paths']))"
```

## Probar la misma imagen que CI

Construir el target `test`:

```bash
docker build --target test -t backend-finance:test .
```

Ejecutarlo:

```bash
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

Las pruebas actuales no se conectan a esa base ni a SAP, pero las variables
permiten importar la configuracion completa.

## Añadir una prueba

Crear un archivo:

```text
tests/test_nombre_del_modulo.py
```

Ejemplo:

```python
import unittest


class ExampleTests(unittest.TestCase):
    def test_sum(self):
        self.assertEqual(1 + 1, 2)


if __name__ == "__main__":
    unittest.main()
```

Un comando debe devolver código `0` cuando todo pasa y un código distinto de
`0` cuando algo falla. GitHub Actions utiliza ese código para marcar el step y
el job como correctos o fallidos.
