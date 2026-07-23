# THIS FILE HAS BEEN REMOVED FROM main.py — Authentication Stabilization Refactor
#
# app/domain/security/router.py was a ghost router that caused:
#
#   1. A duplicate POST /api/v1/auth/login route accepting application/x-www-form-urlencoded
#      (OAuth2PasswordRequestForm) while the live endpoint expects application/json
#   2. OAuth2 Password Flow appearing in the Swagger Authorize dialog
#   3. /auth/me using the zombie get_current_user from deps.py (wrong signing key)
#
# This router has been UNREGISTERED from main.py.
# It has zero importers remaining in the codebase.
# This file is safe to delete from the filesystem.
#
# Removed from main.py: 2026-07-23 | Auth Stabilization Phase
raise ImportError(
    "app.domain.security.router has been removed from the application. "
    "The live auth routes are in app/api/v1/auth.py."
)
