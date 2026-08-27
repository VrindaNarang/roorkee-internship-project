# Authentication & role-based access control (see PROJECT_SPEC.md Milestone 11).
#
# Three fixed roles: admin, sales_manager, sales_executive (see
# `app/models/user.py`). Deliberately minimal — JWT bearer tokens, no
# refresh-token rotation, no OAuth/SSO, no password-reset flow — this is
# internal single-tenant software, not a consumer product.
#
# security.py     - password hashing (bcrypt) + JWT encode/decode, no DB access
# auth_service.py  - authenticate_user() + create_access_token(), the DB-touching half
# dependencies.py  - FastAPI dependencies: get_current_user, require_role(*roles)
