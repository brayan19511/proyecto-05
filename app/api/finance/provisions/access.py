from app.core.access import has_permission


def can_view_all_provisions(user) -> bool:
    return has_permission(
        user,
        "provisions.view_all",
        "provisions.edit_all",
        "provisions.review",
    )


def can_edit_all_provisions(user) -> bool:
    return has_permission(user, "provisions.edit_all")
