# THIS FILE HAS BEEN DELETED — Authentication Stabilization Refactor
#
# app/api/deps.py was a zombie authentication module that was never used
# by the live login flow. It caused:
#
#   1. Swagger UI to show OAuth2 Password Flow (OAuth2PasswordBearer declaration)
#   2. 8 domain routes to validate tokens against the wrong signing key
#      (core.config.SECRET_KEY vs the live dashboard_secret_key)
#
# All importers have been migrated to app/api/v1/auth_deps.py.
# This file is safe to delete from the filesystem.
#
# Deleted: 2026-07-23 | Auth Stabilization Phase
raise ImportError(
    "app.api.deps has been removed. "
    "Import from app.api.v1.auth_deps instead: "
    "get_current_user, require_permission, RequirePermissions"
)
