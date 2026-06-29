# Bases externas SQL Server

## Criterio de estructura

Las conexiones y modelos se organizan por sistema y base de datos:

```text
app/
|-- core/db/
|   `-- db_ofisis.py
|-- models/external/
|   `-- ofisis/
|       `-- ecomm/
|           `-- generated_models.py
`-- api/
    `-- sales_channel/
```

`models/external/ofisis/ecomm` representa la ubicacion fisica del dato.
`api/sales_channel` representa el caso de uso que consume el frontend.

Los modelos externos no se importan desde `app.models` y no forman parte del
metadata de Alembic. La aplicacion no debe crear ni migrar estas tablas.

## Configuracion

```env
DB_OFISIS_HOST=10.0.0.5
DB_OFISIS_PORT=1433
DB_OFISIS_USER=
DB_OFISIS_PASSWORD=
DB_OFISIS_DRIVER=ODBC Driver 17 for SQL Server
DB_OFISIS_ENCRYPT=false
DB_OFISIS_TRUST_SERVER_CERTIFICATE=false
DB_OFISIS_ECOMM_DATABASE=EcommDB
```

No se debe guardar una URL completa con credenciales en el repositorio.
`Settings.get_ofisis_database_url()` construye un objeto `URL` y escapa
usuario y contrasena correctamente.

## Agregar otra base Ofisis

1. Agregar una variable como `DB_OFISIS_INVENTORY_DATABASE`.
2. Crear los modelos bajo `models/external/ofisis/inventory`.
3. Crear una dependencia que invoque `get_db_ofisis(nombre_base)`.
4. Mantener la API dentro del dominio funcional correspondiente.
5. No aceptar el nombre de la base desde un parametro HTTP.

Ejemplo de dependencia:

```python
def get_db_ofisis_inventory():
    yield from get_db_ofisis(settings.DB_OFISIS_INVENTORY_DATABASE)
```

## Regenerar modelos

La generacion debe apuntar a una base concreta:

```powershell
sqlacodegen "mssql+pyodbc://usuario:password@host/EcommDB?driver=ODBC+Driver+17+for+SQL+Server" --outfile app/models/external/ofisis/ecomm/generated_models.py
```

Revisar el diff antes de reemplazar el archivo. La logica de negocio nunca
debe escribirse dentro de `generated_models.py`.

## API de canales de venta

Rappi y Peya normal permiten consultar, crear, editar, activar y desactivar:

```text
GET    /api/sales-channels/{canal}/skus
GET    /api/sales-channels/{canal}/skus/{sku}
POST   /api/sales-channels/{canal}/skus
PATCH  /api/sales-channels/{canal}/skus/{sku}
POST   /api/sales-channels/{canal}/skus/{sku}/activate
POST   /api/sales-channels/{canal}/skus/{sku}/deactivate
```

Los valores de `{canal}` implementados son `rappi` y `peya`.

Las promociones Peya permiten eliminacion fisica:

```text
GET    /api/sales-channels/peya/promo-skus
GET    /api/sales-channels/peya/promo-skus/{sku}
POST   /api/sales-channels/peya/promo-skus
DELETE /api/sales-channels/peya/promo-skus/{sku}
```

Permisos:

- `sales_channels.skus.view`
- `sales_channels.skus.edit`

El listado Peya incluye `has_promotion`. El frontend puede usar:

- `POST /api/sales-channels/peya/promo-skus` para agregarla.
- `DELETE /api/sales-channels/peya/promo-skus/{sku}` para eliminarla.

No existe una llave foranea entre las tablas externas. La aplicacion valida
que el SKU exista en `peya_sku` antes de crear su promocion.

## Sincronizacion masiva

Rappi y Peya exponen `POST .../skus/bulk-sync`:

```json
{
  "items": [
    {"sku": "SKU-001", "on/off": "on"},
    {"sku": "SKU-002", "on/off": "off"}
  ],
  "create_missing": true,
  "deactivate_missing": false
}
```

- `create_missing=true`: crea SKU que aun no existen.
- `deactivate_missing=false`: solo modifica filas enviadas.
- `deactivate_missing=true`: tambien desactiva todos los SKU no enviados.
- Toda la lista se confirma en una sola transaccion.
- Una lista con SKU duplicados se rechaza completa.

`deactivate_missing` debe activarse solamente cuando la lista recibida sea
una fotografia completa del canal.

### Snapshot de activos

Cuando el archivo contiene unicamente los SKU que deben quedar activos, usar:

```text
POST /api/sales-channels/rappi/skus/active-snapshot
POST /api/sales-channels/peya/skus/active-snapshot
```

```json
{
  "skus": ["SKU-001", "SKU-002"],
  "create_missing": true
}
```

- Los SKU enviados quedan activos.
- Los SKU existentes que no fueron enviados quedan inactivos.
- `create_missing=true` crea como activos los SKU nuevos.
- `create_missing=false` devuelve los SKU desconocidos en `missing`.
- Una lista vacia o con duplicados es rechazada antes de modificar la base.

## Cache de motores

`@lru_cache` no almacena consultas ni datos de negocio. Conserva una instancia
de `Engine` y una fabrica de sesiones por nombre de base:

```text
get_ofisis_engine("EcommDB") -> Engine EcommDB
get_ofisis_engine("OtraDB")  -> Engine OtraDB
```

Cada `Engine` administra su propio pool de conexiones. Cada solicitud sigue
abriendo y cerrando su propia `Session` mediante `get_db_ofisis()`.
