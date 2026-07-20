from app.domain.security.models import UserRole

# ── Role/Permission Mappings ───────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.platform_admin: {"*"},
    UserRole.org_owner:      {"*"},
    UserRole.executive:      {"view_all", "view_roi", "view_reports"},
    UserRole.ops_manager:    {"view_all", "manage_users", "edit_friction", "edit_context"},
    UserRole.team_lead:      {"view_all", "edit_friction", "manage_team"},
    UserRole.employee:       {"view_assigned", "edit_assigned"},
    UserRole.reader:         {"view_all"},
    UserRole.service:        {"*"},
    
    # Legacy fallbacks
    UserRole.founder:        {"*"},
    UserRole.admin:          {"*"},
    UserRole.sales:          {"edit_memory", "add_note", "change_lead_stage", "view_all"},
    UserRole.support:        {"edit_memory", "add_note", "view_all"},
}

class AuthorizationEngine:
    @staticmethod
    def role_can(role: UserRole, permission: str) -> bool:
        """Return True if this role has the requested permission."""
        perms = ROLE_PERMISSIONS.get(role, set())
        return "*" in perms or permission in perms

# Alias for backwards compatibility
role_can = AuthorizationEngine.role_can
