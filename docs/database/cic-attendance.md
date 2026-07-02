# Asistencia desde CIC

La API consulta marcas de asistencia en la base externa SQL Server `dbcoolbox`.
Es una integracion de solo lectura y no forma parte de las migraciones Alembic.

## Configuracion

```env
DB_CIC_HOST=
DB_CIC_PORT=1433
DB_CIC_USER=
DB_CIC_PASSWORD=
DB_CIC_DRIVER=ODBC Driver 17 for SQL Server
DB_CIC_ENCRYPT=false
DB_CIC_TRUST_SERVER_CERTIFICATE=false
DB_CIC_DATABASE=dbcoolbox
```

En produccion se recomienda un usuario SQL con permiso `SELECT` solamente
sobre `rash.FASI_TA_MARCA_TXT_COOLBOX`.

## Endpoints

```text
GET /api/attendance/marks
POST /api/attendance/marks/search
```

El `GET` es apropiado para consultas simples o manuales. El `POST /search`
es el recomendado para el frontend cuando consulta varios colaboradores:
continua siendo una operacion de solo lectura, pero evita URLs extensas y no
expone los documentos en el historial del navegador o logs del proxy.

Parametros del `GET`:

- `document_number`: obligatorio y repetible; maximo 100 documentos.
- `date_from`: fecha inicial inclusiva, opcional.
- `date_to`: fecha final inclusiva, opcional.
- `limit`: 1 a 5000, por defecto 1000.
- `offset`: desplazamiento, por defecto 0.

Ejemplo:

```text
/api/attendance/marks?document_number=44420440&date_from=2026-07-01&date_to=2026-07-31
```

Para varios documentos:

```text
/api/attendance/marks?document_number=44420440&document_number=72534705
```

Busqueda masiva desde el frontend:

```json
{
  "document_numbers": [44420440, 72534705],
  "date_from": "2026-07-01",
  "date_to": "2026-07-31",
  "limit": 1000,
  "offset": 0
}
```

Respuesta:

```json
{
  "items": [
    {
      "sequence_id": 10,
      "document_number": 44420440,
      "marked_at": "2026-07-01T08:00:00",
      "mark_date": "2026-07-01",
      "row_number": 1,
      "mark_type": "INGRESO"
    }
  ],
  "total": 1,
  "limit": 1000,
  "offset": 0,
  "has_more": false
}
```

La numeracion se reinicia por documento y dia. Las filas impares son
`INGRESO` y las pares son `SALIDA`. `items` se mantiene plano para facilitar
ordenamiento, filtros, paginacion y exportacion en una grilla. El frontend
puede agruparlo por `document_number` y `mark_date` para una vista diaria.

## Seguridad

Permiso:

```text
attendance.marks.view
```

El seed crea el rol `Asistencia Consulta`. La auditoria registra usuario,
ruta, estado y duracion, pero redacta el documento y el cuerpo de respuesta.

## Rendimiento

La consulta filtra antes de calcular `ROW_NUMBER`. Si la tabla no cuenta con
un indice equivalente, un DBA debe evaluar:

```sql
CREATE INDEX IX_FASI_MARCA_DOCUMENTO_FECHA
ON rash.FASI_TA_MARCA_TXT_COOLBOX (
    IN_NUMERO_DOCUMENTO,
    DT_FECHA_MARCA
)
INCLUDE (IN_SECUENCIA_CARGA);
```

No ejecutar el indice sin revisar antes espacio, carga de escritura y planes
de ejecucion en el servidor CIC.
