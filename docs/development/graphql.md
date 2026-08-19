# GraphQL sobre ICG

Modulo de consulta para las ventas de ICG. Vive en `app/api/graphql/` y se
expone en un solo endpoint: `POST /api/graphql`.

Esta guia esta escrita para aprender el modulo desde cero. Si ya lo conoces y
solo vas a extenderlo, salta a las tres recetas:
[columnas](#5-las-columnas-dos-niveles),
[relaciones](#6-como-agregar-una-relacion),
[filtros](#7-como-agregar-un-filtro).

## 1. Por que GraphQL aqui

La consulta tipica de ventas en ICG une 14 tablas:

```sql
SELECT TOP 100 * FROM ALBVENTACAB T0
INNER JOIN ALBVENTALIN T1 ON ...
INNER JOIN TESORERIA T2 ON ...
LEFT JOIN ALBVENTACAMPOSLIBRES T3 ON ...
-- y 10 joins mas
```

Trae **todo siempre**, aunque el cliente solo quiera el numero de documento y
el total. Con GraphQL cada JOIN se vuelve un campo que solo se ejecuta si el
cliente lo pide:

```graphql
query {
  documentosVenta(
    desde: "2026-08-01"
    hasta: "2026-08-01"
    tipodoc: [5, 13]
    limite: 100
  ) {
    numserie
    numalbaran
    totalNeto
    tesoreria { codformapago importe }
    lineas {
      codarticulo
      unidades
      articulo {
        descripcion
        marca { descripcion }
        seccion { descripcion }
        familia { descripcion }
      }
    }
  }
}
```

Esa consulta ejecuta **7 SELECT simples con IN** en lugar de un JOIN de 14
tablas. Y si el cliente solo pide `numserie` y `totalNeto`, ejecuta **1**.

## 2. Los cuatro conceptos que hay que entender

### Schema

El catalogo de lo que se puede consultar. Se arma solo, a partir de los type
hints de Python. Para verlo:

```bash
python -c "from app.api.graphql import schema; print(schema.as_str())"
```

### Tipo (`@strawberry.type`)

Una clase = una tabla. Los atributos son campos que salen de la fila; los
metodos con `@strawberry.field` son relaciones.

```python
@strawberry.type
class LineaVenta:
    codarticulo: str | None      # sale de la fila
    unidades: float

    @strawberry.field            # relacion: solo corre si la piden
    async def articulo(self, info: strawberry.Info) -> Articulo | None:
        fila = await info.context["loaders"].articulo.load(self.codarticulo)
        return Articulo.desde_fila(fila) if fila else None
```

Strawberry convierte los nombres a camelCase en el schema: `total_neto` en
Python se consulta como `totalNeto`.

### Resolver

El codigo que devuelve el valor de un campo. En este modulo **ningun resolver
tiene SQL**: siempre llama al repositorio o a un loader.

### DataLoader (lo unico no obvio, y es obligatorio)

Sin loaders, pedir 100 documentos con sus lineas ejecuta 100 consultas (el
problema **N+1**). Un DataLoader junta las claves que se pidieron en el mismo
instante y hace **una** consulta con la lista completa.

```
Sin loader:  100 documentos -> 100 SELECT de lineas -> 100 SELECT de articulos
Con loader:  100 documentos ->   1 SELECT de lineas ->   1 SELECT de articulos
```

La regla de una funcion de lote: devuelve una lista **del mismo largo y en el
mismo orden** que las claves que recibio.

## 3. Los archivos

```text
app/api/graphql/
├── router.py        # schema + endpoint (empieza a leer aqui)
├── query.py         # queries raiz: puntos de entrada y filtros
├── types/
│   ├── documento.py # DocumentoVenta, LineaVenta, Tesoreria, TipoDoc
│   └── articulo.py  # Articulo, Marca, Seccion, Familia, Subfamilia
├── loaders.py       # DataLoaders: resuelven el N+1
├── repository.py    # TODO el SQL contra ICG
├── columnas.py      # catalogo de columnas por tabla (2 niveles)
├── context.py       # usuario + repo + loaders, por request
├── permissions.py   # permiso graphql.icg.view
└── converters.py    # Decimal/datetime -> tipos de GraphQL
```

Orden sugerido para leerlo: `router.py` -> `query.py` -> `types/documento.py`
-> `loaders.py` -> `repository.py`.

## 4. Probarlo

Abre <http://localhost:8000/api/graphql> en el navegador. Aparece GraphiQL, un
editor con autocompletado y la pestania **Docs** para explorar el schema.

Para ejecutar consultas necesitas credenciales. En la pestania de **headers**
de GraphiQL:

```json
{ "Authorization": "Bearer <tu-token>" }
```

El usuario necesita el permiso `graphql.icg.view` (o el rol Admin).

Sin token el schema se explora igual, pero la consulta responde
`No autenticado`. Es a proposito: permite aprender el schema sin acceso a los
datos.

### Errores en GraphQL

GraphQL responde **HTTP 200 casi siempre**. Los errores vienen dentro del
cuerpo:

```json
{ "data": null, "errors": [{ "message": "No tienes permiso ..." }] }
```

Si estas depurando, revisa `errors` antes que el codigo HTTP.

## 5. Las columnas: dos niveles

ALBVENTACAB tiene 106 columnas y ALBVENTALIN 100. Exponerlas todas como
campos tipados seria escribir 400 lineas para que nadie use el 80%. La solucion
son dos niveles, y `columnas.py` es la unica fuente de la verdad: un
`CatalogoColumnas` por tabla, con su nivel 1 y su nivel 2.

Estado actual:

| Tabla | Nivel 1 (campos tipados) | Nivel 2 (camposExtra) | Total |
|---|---|---|---|
| ALBVENTACAB | 41 | 65 | 106 |
| ALBVENTALIN | 42 | 58 | 100 |

**Para agregar una tabla nueva** (por ejemplo TESORERIA): se declaran sus dos
tuplas de columnas y se crea su `CatalogoColumnas` al final de `columnas.py`.
Nada mas: `disponibles()` y `validar()` ya vienen hechos.

### Nivel 1: campos con nombre y tipo

Las columnas de uso real. Estan en el tuple `base` del catalogo de su tabla
(`COLUMNAS_BASE` para la cabecera, `COLUMNAS_LINEA_BASE` para la linea), que
**es** el SELECT del repositorio, y tienen su campo en el type con tipo,
descripcion y autocompletado en GraphiQL.

Agregar una son **dos pasos**:

1. **`columnas.py`**: el nombre en `COLUMNAS_BASE`. Una palabra.

   ```python
   "TOTALCOSTE",
   "PUNTOSACUM",   # nueva
   ```

2. **`types/documento.py`**: el atributo con su tipo, y la linea en
   `desde_fila`.

   ```python
   puntos_acumulados: float

   # dentro de desde_fila:
   puntos_acumulados=a_float(fila.get("puntosacum")),
   ```

No hay tercer paso: el SELECT y el schema se regeneran solos.

### Nivel 2: `camposExtra`, sin tocar codigo

Para el resto de la tabla, el cliente pide las columnas por nombre y las recibe
en un objeto JSON:

```graphql
query {
  documentosVenta(
    desde: "2026-08-17"
    hasta: "2026-08-17"
    columnas: ["SALA", "MESA", "NUMCOMENSALES", "ESTADODELIVERY"]
  ) {
    numserie
    camposExtra
  }
}
```

```json
{ "camposExtra": { "SALA": -1, "MESA": -1, "NUMCOMENSALES": 0, "ESTADODELIVERY": null } }
```

Los nombres se validan contra `COLUMNAS_ALBVENTACAB` (lista blanca) antes de
entrar al SQL, asi que **no hay `SELECT *` ni concatenacion de texto ajeno**.
Un nombre inventado responde `Columnas desconocidas en ALBVENTACAB: ...`.

Lo mismo aplica a las lineas, con `columnasLinea`:

```graphql
documentosVenta(desde: "...", hasta: "...", columnasLinea: ["NUMKG", "CARGO1"]) {
  lineas { descripcion camposExtra }
}
```

`columnasLinea` vale para **todas** las lineas de la consulta (no se puede
pedir un juego distinto por documento), porque el DataLoader trae todas las
lineas con un solo SELECT.

Para descubrir que hay disponible en cada tabla:

```graphql
query {
  columnasDocumentoVenta
  columnasLineaVenta
}
```

### Cual usar

| | Nivel 1 (campo propio) | Nivel 2 (camposExtra) |
|---|---|---|
| Tipado | Si (Int, Float, Boolean, Date) | No, JSON |
| Autocompletado en GraphiQL | Si | No |
| Nombre | en espaniol, legible | el de ICG, en mayuscula |
| Costo de agregar | 2 archivos, 3 lineas | ninguno |

La regla: **empieza en el nivel 2 y promueve al nivel 1 lo que se use seguido.**
Promover es agregar el nombre a `COLUMNAS_BASE` y escribir su campo; el cliente
deja de verlo en `camposExtra` automaticamente.

### Detalles al agregar una columna

- El repositorio devuelve las claves **en minuscula**, aunque en ICG esten en
  mayuscula: `fila.get("puntosacum")`.
- Usa `fila.get(...)` y no `fila[...]`: si la columna no existe en esa
  instalacion de ICG, el campo queda en `null` en lugar de romper la consulta.
- Elige el conversor correcto de `converters.py`. Tres convenciones de ICG que
  ya estan resueltas ahi:

  | Columna | Valor crudo en ICG | Conversor | Resultado |
  |---|---|---|---|
  | `FACTURADO`, `TIQUET`, `LINEAOCULTA` | char `'T'` / `'F'` | `a_booleano` | `true` / `false` |
  | `HORA`, `HORAFIN` | `1899-12-30 15:22:29` | `a_hora` | `"15:22:29"` |
  | `FECHATRASPASO`, `FECHAENTREGA` | `1899-12-30 00:00:00` | `a_fecha` | `null` |
  | `IDPROMOCION`, `ABONODE_NUMALBARAN` | `-1` | `a_entero` | `null` |
  | `COLOR`, `TALLA` | `'.'` | `a_texto(..., vacios=("."))` | `null` |

**En ICG casi nada es NULL: cada tipo tiene su propio valor de "sin dato".**
Es la trampa mas facil de pisar en este modulo. Sin traducirlos, una linea que
no abona a nada devolveria `documentoOrigenNumero: -1` y un articulo sin color
devolveria `color: "."`, y el frontend tendria que conocer esas convenciones.

- `N`, `NFAC` y `ABONODE_N` son **caracteres** (`'B'`), no numeros.
  `NUMALBARAN`, `NUMFAC` y `NUMLIN` si son enteros.
- `HORA` se comporta distinto segun la tabla: en ALBVENTACAB viene con la fecha
  centinela (`1899-12-30 15:22:29`) y en ALBVENTALIN con la fecha real
  (`2024-02-21 12:50:32`). `a_hora` devuelve solo la hora en los dos casos.

## 6. Como agregar una relacion

Una relacion es un JOIN a otra tabla. Ejemplo que quedo pendiente a proposito:
`ARTICULOSCAMPOSLIBRES`
(`LEFT JOIN ARTICULOSCAMPOSLIBRES ARTC ON ART.CODARTICULO = ARTC.CODARTICULO`).

1. **Repositorio** (`repository.py`): un metodo que recibe la lista de claves y
   devuelve un dict indexado por clave.

   ```python
   def campos_libres_articulo_por_codigo(self, codigos: list[str]) -> dict[str, Fila]:
       filas = self._ejecutar(
           """
           SELECT ac.CODARTICULO, ac.<TUS_COLUMNAS>
           FROM ARTICULOSCAMPOSLIBRES ac WITH (NOLOCK)
           WHERE ac.CODARTICULO IN :codigos
           """,
           {"codigos": list(codigos)},
           expandibles=("codigos",),
       )
       return {fila["codarticulo"]: fila for fila in filas}
   ```

2. **Loader** (`loaders.py`): agregalo al dataclass `Loaders` y a
   `construir_loaders`. Es una linea, porque `loader_de_uno` (relacion N:1) y
   `loader_de_lista` (relacion 1:N) ya hacen el trabajo.

3. **Tipo** (`types/articulo.py`): el nuevo `@strawberry.type` con su
   `desde_fila`, y un `@strawberry.field` en `Articulo` que use el loader.

4. **Prueba** (`tests/test_graphql_icg.py`): agrega el metodo al `RepoFalso` y
   el campo a `CONSULTA_COMPLETA`. El test
   `test_los_loaders_agrupan_las_consultas` verifica que se consulte una sola
   vez.

## 7. Como agregar un filtro

Los filtros van **solo en el query raiz** (`query.py` + el metodo `documentos`
del repositorio). Las relaciones nunca filtran: son loaders y deben poder
agrupar claves libremente.

### Filtro de varios valores (arreglo)

`tipodoc` es el ejemplo: un documento tiene **un** tipo, pero el filtro acepta
**varios**.

```graphql
documentosVenta(desde: "...", hasta: "...", tipodoc: [17, 18]) { ... }
```

En Python el tipo del argumento es la lista, y en el repositorio se vuelve un
`IN` declarando el parametro como expandible:

```python
if tipodoc:                                   # lista vacia = sin filtro
    condiciones.append("c.TIPODOC IN :tipodoc")
    params["tipodoc"] = list(tipodoc)
    expandibles.append("tipodoc")
```

`expandibles` convierte `IN :tipodoc` en `IN (?, ?, ?)` con tantos placeholders
como valores. Cualquier filtro se vuelve arreglo con este mismo patron de tres
lineas (por ejemplo `tienda` -> `tiendas`).

Ojo con la diferencia: el **campo** `tipodoc` de un documento sigue siendo un
`Int`. Lo que se vuelve arreglo es el **argumento** del filtro.

### Filtro por una columna que no esta en la tabla principal

Es el caso del numero de pedido: no esta en `ALBVENTACAB` sino en
`FACTURASVENTACAMPOSLIBRES.NRO_PEDIDO` y en
`ALBVENTACAMPOSLIBRES.PEDIDOVTEX`.

La solucion es un **EXISTS**, no un JOIN:

```python
if pedido is not None:
    condiciones.append(
        "("
        " EXISTS ("
        "  SELECT 1 FROM FACTURASVENTACAMPOSLIBRES fp WITH (NOLOCK)"
        "  WHERE fp.NUMSERIE = c.NUMSERIE"
        "  AND fp.NUMFACTURA = c.NUMFAC"
        "  AND fp.NRO_PEDIDO = :pedido"
        " ) OR EXISTS ("
        "  SELECT 1 FROM ALBVENTACAMPOSLIBRES ap WITH (NOLOCK)"
        "  WHERE ap.NUMSERIE = c.NUMSERIE"
        "  AND ap.NUMALBARAN = c.NUMALBARAN"
        "  AND ap.PEDIDOVTEX = :pedido"
        " )"
        ")"
    )
    params["pedido"] = pedido
```

Por que EXISTS y no JOIN:

- **No duplica filas.** Un JOIN a una tabla con varias coincidencias
  multiplicaria los documentos devueltos.
- **No obliga a traer la tabla.** El filtro es independiente de si el cliente
  pidio `camposLibresFactura` en la consulta.
- **Se combina sin pensar.** Cada filtro es un bloque que se suma con AND; el
  orden no importa.

Filtros disponibles hoy: `tienda` (por `ALBVENTALIN.CODALMACEN`), `tipodoc`
(arreglo), `pedido` (las dos tablas de campos libres) y `canalVenta`
(`FACTURASVENTACAMPOSLIBRES.CANAL_VENTA`, sin distinguir mayusculas ni
espacios).

### Filtro por documentos puntuales (claves compuestas)

Un documento de ICG **no se identifica con un solo texto**. `"F001-123"` es
ambiguo: no se sabe si `123` es `NUMALBARAN` o `NUMFAC`, porque son dos
numeraciones distintas de la misma serie. Partir ese texto en el servidor seria
adivinar.

Por eso el filtro es una lista de objetos (un `@strawberry.input`), no una lista
de textos:

```graphql
query {
  documentosVenta(documentos: [
    { numserie: "001", numalbaran: 1 }      # por albaran
    { numserie: "001", numfac: 500 }        # por factura
    { numserie: "002", numalbaran: 7, numfac: 9 }   # tiene que cumplir ambos
  ]) {
    numserie
    numalbaran
    numfac
    lineas { codarticulo unidades }
  }
}
```

`numserie` es obligatorio; hay que indicar `numalbaran` o `numfac` (o los dos).
Si no viene ninguno, la consulta se rechaza con un mensaje explicito en lugar de
devolver la serie completa.

**Cuando se usa `documentos`, el rango de fechas es opcional.** El filtro de
fechas existe para que nadie barra la tabla entera; si ya pediste claves
exactas, el barrido esta acotado por definicion. Igual puedes combinar ambos.

En el SQL cada clave es un bloque, unidos con OR:

```sql
WHERE (
      (c.NUMSERIE = :doc0_serie AND c.NUMALBARAN = :doc0_alb)
   OR (c.NUMSERIE = :doc1_serie AND c.NUMFAC     = :doc1_fac)
)
```

Lo unico que se interpola en el texto es el indice (`doc0`, `doc1`), que sale de
`enumerate`. Los valores siempre viajan en `params`. Tope: 100 documentos por
consulta.

Si el frontend ya maneja el formato `SERIE-NUMERO` de la capa silver, la
conversion se hace **en el cliente**, que es quien sabe cual de las dos
numeraciones tiene. El servidor no adivina.

### Reglas al agregar filtros

- **Nunca interpoles un valor en el SQL.** Solo se concatenan fragmentos fijos
  escritos en el codigo; los valores viajan siempre en `params`. El test
  `test_ningun_valor_se_interpola_en_el_sql` lo verifica.
- **Describe el argumento** con `strawberry.argument(description=...)`: esa
  descripcion aparece en GraphiQL y es la documentacion que va a leer quien
  consuma la API.
- **Verifica el SQL con un test**, no con la base. Ver la clase
  `SqlDeFiltrosTests`: usa una sesion falsa y revisa el texto generado.
- Si algun dia hay mas de 8 filtros, se agrupan en un `@strawberry.input`
  (`filtro: FiltroDocumentos`) en lugar de seguir sumando argumentos sueltos.

## 8. ORM o SQL escrito a mano

**En este modulo: SQL a mano. En Postgres: ORM.** La regla corta es *el ORM se
usa donde somos duenios del schema*.

Por que no ORM contra ICG:

| Razon | Detalle |
|---|---|
| No somos duenios del schema | ICG es de un tercero, no lo migramos con Alembic. Los modelos serian solo un espejo que hay que mantener a mano cuando ICG cambie. |
| Claves compuestas sin FK declaradas | Casi todo une por 2 a 4 columnas y sin foreign keys. Declarar eso en el ORM es mas codigo que el SELECT. |
| El lazy loading pelea con GraphQL | Las relaciones del ORM cargan sola una fila a la vez: reintroduce el N+1 justo donde los DataLoaders lo resolvieron, y encima de forma silenciosa. |
| Solo leemos | El ORM brilla en escrituras (unit of work, identity map, cascadas). Aqui no escribimos nada. |
| Consistencia con el proyecto | Todo el acceso a ICG que ya existe usa SQL con `text()`: `app/services/ingestion/extractor.py`, `app/services/ingestion/catalog.py`, los repositorios de libro mayor. |
| Los WHERE son especificos de T-SQL | `WITH (NOLOCK)`, `TOP (n)`, `DATEADD`. Expresarlos por ORM los vuelve mas dificiles de leer, no mas faciles. |

Donde el ORM si conviene y ya se usa: las tablas propias en Postgres
(`app/models/`), con Alembic para las migraciones. Ahi tenemos control del
schema, hay escrituras y las relaciones son de verdad.

Punto medio si algun dia los filtros dinamicos se vuelven incomodos:
**SQLAlchemy Core** (objetos `Table` y `select()`, sin mapear clases). Da
composicion de condiciones sin el peso del ORM. Hoy no hace falta: armar la
lista `condiciones` es mas legible para cualquier programador que un query
builder.

## 9. Reglas del modulo

1. **Un tipo = una tabla.** Nombres en espaniol, como el resto del proyecto.
2. **Ningun resolver tiene SQL.** Todo el SQL en `repository.py`.
3. **Toda relacion pasa por un DataLoader.** Sin excepcion, o vuelve el N+1.
4. **Los filtros van solo en el query raiz.** Las relaciones no filtran.
5. **Todo query raiz exige rango de fechas o claves exactas, y tiene techo
   de `limite`.** Hoy: maximo 31 dias, 500 filas, 100 documentos (`query.py`).
6. **Sin mutaciones.** Las escrituras siguen en REST, donde ya estan la
   auditoria y los jobs.
7. **Sin `SELECT *`** y sin valores interpolados en el SQL.

## 10. Lo que este modulo NO hace

- **No reemplaza REST.** Los endpoints existentes siguen igual.
- **No hace agregaciones** (sumas por canal, por tienda, ticket promedio). Eso
  se queda en `/api/analytics`, que consulta la capa silver ya pre-agregada.
  GraphQL sirve para navegar el detalle documento por documento.
- **No lee la capa bronze/silver/gold.** Consulta ICG directo. Son modulos
  distintos a proposito.

## 11. Limites de seguridad activos

| Limite | Valor | Donde |
|---|---|---|
| Profundidad maxima de anidamiento | 8 niveles | `router.py` |
| Tamanio maximo de la consulta | 2000 tokens | `router.py` |
| Filas por consulta | 500 | `query.py` |
| Rango de fechas | 31 dias | `query.py` |
| Valores en el filtro `tipodoc` | 50 | `query.py` |
| Documentos por clave exacta | 100 | `query.py` |
| Columnas de `camposExtra` | lista blanca de ALBVENTACAB | `columnas.py` |
| Permiso | `graphql.icg.view` | `permissions.py` |

## 12. Pruebas

```bash
python -m pytest tests/test_graphql_icg.py -q
```

Usan un repositorio falso y una sesion falsa, asi que **corren sin conexion a
ICG**. Cubren tres cosas:

- Que el grafo se arme bien y que los permisos bloqueen.
- Que los loaders agrupen las consultas (cuentan las llamadas al repositorio).
- Que el SQL de los filtros sea el esperado (`SqlDeFiltrosTests`).
