from app.core.access import get_permission_codes, is_admin


def can_view_all_provisions(user) -> bool:
    permissions = get_permission_codes(user)
    return (
        is_admin(user)
        or "provisions.view_all" in permissions
        or "provisions.edit_all" in permissions
        or "provisions.review" in permissions
    )


def can_edit_all_provisions(user) -> bool:
    permissions = get_permission_codes(user)
    return is_admin(user) or "provisions.edit_all" in permissions
