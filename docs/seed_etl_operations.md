# Seed y operaciones ETL

## Objetivo

El seed reconcilia los datos minimos de seguridad. Puede ejecutarse varias
veces: crea registros faltantes, actualiza descripciones, reactiva registros
base y completa relaciones ausentes.

Toda la reconciliacion usa una sola transaccion. Ante un error se ejecuta
`rollback`, evitando un catalogo parcialmente actualizado.

## Configuracion inicial

Configurar estas variables sin guardar credenciales reales en Git:

```env
SEED_ADMIN_EMAIL=admin@admin.com
SEED_ADMIN_PASSWORD=una-clave-segura
```

`SEED_ADMIN_PASSWORD` solo se utiliza cuando el usuario configurado aun no
existe. El seed no reemplaza contrasenas de usuarios existentes.

## Primer bootstrap

El primer seed se ejecuta por CLI porque todavia no existe un usuario
autenticado:

```powershell
enviroments\Scripts\python.exe -m app.scripts.seed
```

Las siguientes verificaciones tambien pueden hacerse con el mismo comando.
Alternativamente, un administrador autenticado puede ejecutar:

```http
POST /api/verify/seed
```

El endpoint exige el permiso `security.roles.edit`.

## Endpoints ETL

Todas las operaciones ETL requieren `coolbox.etl.execute`:

```text
POST /api/etl/ventas/procesar-ventas
POST /api/etl/ventas/procesar-ventas-rango
POST /api/etl/ventas/procesar-ventas-delta
POST /api/etl/productos/sincronizar
POST /api/etl/tiendas/sincronizar
```

Las cargas usan `POST` porque modifican el warehouse. Una recarga diaria
reemplaza la fecha completa, por lo que repetirla produce el mismo estado
logico.

## Auditoria

La auditoria excluye headers de autenticacion, redacta claves sensibles de
forma recursiva y omite cuerpos mayores a `AUDIT_BODY_MAX_BYTES`. Esto evita
persistir contrasenas o tokens y limita el consumo de memoria.

## Mejoras posteriores

- Agregar una tabla `etl_runs` con estado, fecha, duracion y conteos.
- Bloquear ejecuciones concurrentes para la misma fecha.
- Migrar importes monetarios de `float` a `Numeric/Decimal`.
- Incorporar extraccion por chunks si un dia ya no cabe comodamente en memoria.
- Medir consultas con `EXPLAIN (ANALYZE, BUFFERS)` antes de agregar indices.
