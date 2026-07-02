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
        |-- sku/          CRUD y sincronizacion compartida.
        |-- imports/      Lectura y orquestacion de Excel.
        |-- rappi/        Registro de rutas Rappi por pais.
        `-- peya/         SKU y promociones exclusivas de Peya.
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

Rappi y Peya normal permiten consultar, crear, editar, activar y desactivar.
Las rutas usan códigos ISO 3166-1 alpha-2 para el país:

```text
GET    /api/sales-channels/{pais}/{proveedor}/skus
GET    /api/sales-channels/{pais}/{proveedor}/skus/{sku}
POST   /api/sales-channels/{pais}/{proveedor}/skus
PATCH  /api/sales-channels/{pais}/{proveedor}/skus/{sku}
POST   /api/sales-channels/{pais}/{proveedor}/skus/{sku}/activate
POST   /api/sales-channels/{pais}/{proveedor}/skus/{sku}/deactivate
```

Las combinaciones implementadas son:

- `pe/rappi`: Rappi Peru, tabla `rappi_sku`.
- `mx/rappi`: Rappi Mexico, tabla `mx_rappi_sku`.
- `pe/peya`: PedidosYa Peru, tabla `peya_sku`.

Las promociones Peya permiten eliminacion fisica:

```text
GET    /api/sales-channels/pe/peya/promo-skus
GET    /api/sales-channels/pe/peya/promo-skus/{sku}
POST   /api/sales-channels/pe/peya/promo-skus
DELETE /api/sales-channels/pe/peya/promo-skus/{sku}
```

Permisos:

- `sales_channels.skus.view`
- `sales_channels.skus.edit`
- `sales_channels.skus.import`
- `sales_channels.promotions.view`
- `sales_channels.promotions.edit`
- `sales_channels.promotions.import`

Roles iniciales:

- `Canales Venta Consulta`: consulta SKU y promociones.
- `Canales Venta Importador`: previsualiza e importa archivos.
- `Canales Venta Admin`: consulta, CRUD manual e importaciones.

El listado Peya incluye `has_promotion`. El frontend puede usar:

- `POST /api/sales-channels/pe/peya/promo-skus` para agregarla.
- `DELETE /api/sales-channels/pe/peya/promo-skus/{sku}` para eliminarla.

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
POST /api/sales-channels/pe/rappi/skus/active-snapshot
POST /api/sales-channels/mx/rappi/skus/active-snapshot
POST /api/sales-channels/pe/peya/skus/active-snapshot
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

## Agregar un país o proveedor

`channel_registry.py` contiene las combinaciones públicas permitidas. Para
agregar Peya México se debe:

1. Generar o agregar el modelo de la tabla externa.
2. Declarar `PEYA_MEXICO` con país `mx`, proveedor `peya` y su modelo.
3. Añadirlo a `SALES_CHANNELS`.
4. Registrar su router usando los prefijos calculados por la definición.

No se debe recibir desde HTTP el nombre de la base o tabla. País y proveedor
solo resuelven configuraciones declaradas por el backend.

## Importar Excel

El frontend envia `multipart/form-data`; no debe convertir el archivo a
base64. El backend procesa temporalmente el libro y no lo almacena.

Para SKU normales:

```text
POST /api/sales-channels/{pais}/{proveedor}/skus/import/preview
POST /api/sales-channels/{pais}/{proveedor}/skus/import
```

Campos:

- `file`: archivo `.xlsx`.
- `mode`: `active_snapshot` o `status_update`.
- `create_missing`: `true` o `false`.
- `expected_sha256`: opcional en `import`; debe ser el hash de `preview`.

`active_snapshot` necesita solamente la columna `sku`. Los SKU presentes
quedan activos y los omitidos se desactivan.

`status_update` necesita `sku` y una columna `active`, `is_active`, `on`,
`on_off` u `on/off`. Acepta `on/off`, `true/false`, `1/0`,
`activo/inactivo` y `si/no`.

Para promociones Peya:

```text
POST /api/sales-channels/pe/peya/promo-skus/import/preview
POST /api/sales-channels/pe/peya/promo-skus/import
```

El archivo contiene solo `sku`. Los presentes quedan como promociones y los
omitidos se eliminan de `peya_promo_sku`. Un SKU que no exista en `peya_sku`
bloquea la importacion completa.

Ejemplo para JavaScript:

```javascript
const form = new FormData();
form.append("file", file);
form.append("mode", "active_snapshot");
form.append("create_missing", "true");

await fetch(
  "/api/sales-channels/pe/rappi/skus/import/preview",
  { method: "POST", body: form }
);
```

La respuesta indica:

- `preview=true`: solo calculo; se ejecuto rollback.
- `can_apply=false`: hay errores que deben corregirse.
- `applied=true`: la transaccion fue confirmada.
- `sha256`: huella del archivo procesado.

Restricciones:

- Solo `.xlsx`.
- Maximo 5 MB y 20000 filas.
- No se admiten SKU vacios ni duplicados.
- Nginx debe permitir al menos 6 MB mediante `client_max_body_size 6m`.
