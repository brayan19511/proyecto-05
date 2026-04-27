# HISTORIAS DE USUARIO - PROYECTO-05

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