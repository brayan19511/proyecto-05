
# Casos de uso para el modulo Auth
## 1. MÓDULO: AUTH & AUTORIZACIÓN

### 1.1 Autenticación Unificada
**Como:** Usuario del ecosistema.  
**Quiero:** Iniciar sesión con una única cuenta.  
**Para:** Acceder a los distintos roles y aplicaciones según los permisos que me han sido brindados.

#### 1.1.1 Criterios de Aceptación (AC)
1. **Validación de Credenciales:** El sistema debe validar que el `email` tenga formato correcto y la `password` coincida con el hash en la base de datos.
2. **Generación de Token:** El JWT resultante debe contener:
   - `token`: ID del usuario (UUID).
   - `token_type`: ID del usuario (UUID).
   - `user_id`: Estado actual del usuario.
   - `roles`: Lista de `system_names` de los roles que tiene activos en ese momento.
3. **Control de Estado:** Si el usuario tiene `active: false`, el sistema debe denegar el acceso con un error **401 Unauthorized**, incluso si la contraseña es correcta.
4. **Seguridad:** La contraseña nunca debe ser devuelta en ninguna respuesta del API.


### 1.2 Gestion de datos
**Como:** Usuario del ecosistema.  
**Quiero:** ver mis datos relacionado a mi usuario como roles y datos informativos.  
**Para:** visualizar que mis datos esten correctamente.
#### 1.2.1 Criterios de Aceptación (AC)
1. **Validación de datos:** El sistema mostrara los datos del usuario, siendo estos como los roles, datos informativos y a esta se podran ser editos
2. **Seguridad:** No se permitira la modificacion o repeticion de datos como correo y tipo de documento, asi mismo tampoco se podra eliminar de la base de datos solo se desactivara
