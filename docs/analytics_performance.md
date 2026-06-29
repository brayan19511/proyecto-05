# Rendimiento de analytics

## Cambios aplicados

### Endpoints sincronicos

Los repositorios usan SQLAlchemy y `psycopg2`, ambos sincronicos. Por esa razon
los routers analytics se declaran con `def`. FastAPI los ejecuta en su
threadpool y evita bloquear el event loop mientras PostgreSQL responde.

### Pool de conexiones

El engine mantiene un numero acotado de conexiones reutilizables:

```env
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

Los valores deben respetar el limite de conexiones del proveedor. Aumentarlos
sin medir puede empeorar una instancia pequena.

`pool_pre_ping` valida conexiones reutilizadas y reduce fallos despues de que
el proveedor cierre una conexion inactiva.

### Auditoria

Cada auditoria completa realiza una escritura inicial y otra final. Los GET de
analytics no generan ese detalle por defecto:

```env
AUDIT_ANALYTICS_REQUESTS=false
```

ETL, autenticacion y gestion de API clients siguen auditados. Las API keys
nunca se almacenan en el payload de auditoria.

### API clients

La busqueda usa el prefijo indexado/unique antes de comparar el hash. El campo
`last_used_at` se persiste como maximo una vez cada 15 minutos por clave, no en
cada consulta.

## Como medir

Antes de agregar indices, ejecutar las consultas lentas con:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT ...;
```

Registrar como minimo:

- tiempo total y percentil 95;
- filas de `fact_ventas`;
- bloques leidos desde disco y cache;
- llamadas por carga del dashboard;
- conexiones activas y tiempo de espera del pool.

## Evolucion recomendada

Cuando `fact_ventas` crezca y las mediciones lo justifiquen:

1. Crear una tabla agregada diaria por fecha, tienda, canal y producto.
2. Refrescarla al terminar cada fecha del ETL.
3. Consultar esa tabla para KPIs, evolucion, top productos y ABC.
4. Precalcular RFM cuando su tiempo sea relevante.
5. Cachear catalogos de filtros por algunos minutos.

Estas medidas suelen aportar mas que aumentar workers, porque evitan repetir
agregaciones sobre toda la tabla de hechos.
