# Alcance por empresa y área (user_area_access)

## Decisión de diseño

El catálogo de áreas (`master.areas`) es **global**: no lleva `company_id`. Áreas
como TI, Marketing u Operaciones se repiten en todas las sociedades, y
duplicarlas por empresa obligaría a mantener N catálogos.

El amarre con la empresa vive en la tabla de asignación:

```
security.user_area_access
  id
  user_id     -> security.auth.id
  company_id  -> master.companies.id
  area_id     -> master.areas.id   (NULL = todas las áreas de esa empresa)
  active                            (borrado lógico)
```

Una fila significa **"este usuario opera en el área X de la empresa Y"**.

Se eligió una sola tabla en lugar de dos (`user_companies` + `user_areas`)
porque con dos tablas el alcance resultante es el producto cartesiano: un
usuario con empresas {A, B} y áreas {TI, MKT} obtendría TI de B aunque no
corresponda. Con el par explícito eso no puede pasar.

Unicidad: en Postgres los NULL no colisionan en un UNIQUE normal, así que se
usan dos índices únicos parciales — `uq_user_area_access_area`
(`WHERE area_id IS NOT NULL`) y `uq_user_area_access_company`
(`WHERE area_id IS NULL`).

## Resolución del alcance

`app/core/scope.py` centraliza la lógica para que cualquier módulo la reutilice:

| Función | Uso |
|---|---|
| `get_user_scope(db, user, *perms_ver_todo)` | Resuelve el `UserScope` del usuario |
| `scope_condition(model, scope)` | Condición SQL sobre `model.company_id` / `model.area_id` |
| `apply_scope_filter(query, model, scope)` | Aplica la condición a un query |
| `assert_in_scope(scope, company_id, area_id)` | Valida al crear/editar (lanza 403) |

El `UserScope` tiene tres estados:

- **Sin restricción** (`unrestricted`): admin o alguno de los permisos `*_all`
  indicados. No se filtra nada.
- **Con alcance**: se filtra por las empresas completas y los pares
  (empresa, área) asignados.
- **Vacío**: el usuario no tiene accesos configurados. **No se filtra y no se
  bloquea**, para no romper a quienes todavía no tienen alcance asignado. La
  restricción empieza a aplicar recién cuando se le configura un alcance
  explícito al usuario.

## Visibilidad en documentos (provisiones / gastos)

Al listar, la condición es un OR de:

1. Lo creado por el usuario (`created_by`).
2. Lo compartido explícitamente (`provision_access`).
3. Lo que caiga dentro de su alcance de empresa/área.

Quien tiene `provisions.view_all` / `edit_all` (o es admin) ve todo. La bandeja
de revisión se limita al alcance del revisor.

Al crear, `assert_in_scope` valida que el par (empresa, área) del documento esté
dentro del alcance, y además se exige que la empresa y el área estén **activas**.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/security/user-areas` | Lista accesos (filtros: `user_id`, `company_id`, `area_id`, `active`) |
| GET | `/api/security/user-areas/me` | Alcance del usuario autenticado |
| GET | `/api/security/user-areas/{user_id}` | Alcance de un usuario, agrupado empresa > áreas |
| POST | `/api/security/user-areas` | Asigna un acceso (reactiva si ya existía inactivo) |
| PUT | `/api/security/user-areas/{user_id}` | Reemplaza el alcance completo del usuario |
| POST | `/api/security/user-areas/{access_id}/activate` | Reactiva |
| POST | `/api/security/user-areas/{access_id}/deactivate` | Desactiva |

`GET /api/security/auth/me` devuelve además `companies` (árbol empresa > áreas) y
`unrestricted_scope`, para que el front arme combos y filtros sin llamadas extra.

## Maestros: sin borrado físico

Empresas, áreas y monedas se **desactivan**, nunca se borran. Cada una expone
`POST .../{id}/activate` y `POST .../{id}/deactivate`; el `DELETE` queda como
alias deprecado de `deactivate`.

Reglas asociadas:

- Los listados devuelven solo activos por defecto (`?active=false` o
  `?active=` para ver los inactivos).
- No se puede desactivar una empresa o área con registros activos asociados
  (provisiones, conceptos o accesos) — responde 409.
- Como el código sigue ocupado por el registro inactivo, al intentar crear uno
  con el mismo código el error indica que hay que reactivarlo.
- Las validaciones de negocio usan `get_active_company_by_id` /
  `get_active_area_by_id`: no se puede apuntar a un maestro dado de baja.
