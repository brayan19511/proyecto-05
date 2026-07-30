from collections.abc import Iterable

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user


ADMIN_ROLE_NAME = "Admin"


def get_active_role_names(user) -> set[str]:
    return {
        link.role.name
        for link in user.user_roles_links
        if link.active and link.role
    }


def get_permission_codes(user) -> set[str]:
    return {permission.code for permission in user.permissions}


def is_admin(user) -> bool:
    return ADMIN_ROLE_NAME in get_active_role_names(user)


def has_any_permission(user, permission_codes: Iterable[str]) -> bool:
    return bool(get_permission_codes(user).intersection(permission_codes))


def has_permission(user, *permission_codes: str) -> bool:
    """True si el usuario es admin o tiene alguno de los permisos indicados."""
    return is_admin(user) or has_any_permission(user, permission_codes)


class AnyPermissionChecker:
    def __init__(self, *permission_codes: str, detail: str | None = None):
        if not permission_codes:
            raise ValueError("At least one permission code is required")

        self.permission_codes = frozenset(permission_codes)
        # Mensaje 403 personalizado; si no se indica se lista los permisos.
        self.detail = detail or (
            "No tienes ninguno de los permisos requeridos: "
            f"{', '.join(sorted(self.permission_codes))}"
        )

    def __call__(self, current_user=Depends(get_current_user)):
        if has_permission(current_user, *self.permission_codes):
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self.detail,
        )


def require_any_permission(
    *permission_codes: str,
    detail: str | None = None,
) -> AnyPermissionChecker:
    return AnyPermissionChecker(*permission_codes, detail=detail)
