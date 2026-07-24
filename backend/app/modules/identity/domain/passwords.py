"""Password hashing and verification.

Argon2id, via argon2-cffi — OWASP's current default recommendation and the
successor to bcrypt (memory-hard, resistant to GPU/ASIC-accelerated
cracking). Security.md does not specify an algorithm; this is a documented
M3 decision, not an assumption.

No framework imports (FastAPI, SQLAlchemy) — per
docs/engineering/EngineeringStandards.md §2.1, this stays in `domain/`
since argon2-cffi is a cryptographic primitive, not infrastructure.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.modules.identity.domain.errors import WeakPasswordError

_hasher = PasswordHasher()

# Security.md specifies no password policy. Minimum length only, no forced
# complexity rules (must contain a symbol/digit/etc.) — this follows NIST
# 800-63B's current guidance, which explicitly recommends length over
# composition rules (composition rules push users toward predictable
# patterns like "Password1!" without meaningfully raising entropy). Not
# doing breach-list checking (e.g. an HaveIBeenPwned range-query lookup) —
# that's a real, valuable addition but a new external network dependency,
# which is more than this milestone's documented scope calls for.
MINIMUM_PASSWORD_LENGTH = 8


def validate_password_policy(plain_password: str) -> None:
    if len(plain_password) < MINIMUM_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MINIMUM_PASSWORD_LENGTH} characters."
        )


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was produced with parameters weaker than the
    hasher's current defaults (e.g. after a future parameter upgrade) —
    callers should re-hash and persist on a successful login when this is
    true. Not exercised by any M3 flow yet since parameters haven't
    changed, but the check costs nothing to have in place now."""
    return _hasher.check_needs_rehash(password_hash)
