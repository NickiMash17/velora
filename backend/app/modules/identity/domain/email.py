"""Email normalization.

Lowercase + strip surrounding whitespace only. Deliberately NOT doing
provider-specific normalization (e.g. Gmail's dot-insensitivity or
plus-addressing collapse) — those rules aren't universal across
providers and would make two genuinely different addresses collide.
Case alone is enough to guarantee 'Foo@Example.com' and
'foo@example.com' resolve to the same account, which is what "enforce
email uniqueness" actually requires in practice (the `users.email`
UNIQUE constraint is case-sensitive at the database level).

This is the ONE place normalization happens — registration, login, and
uniqueness checks all call this rather than each doing their own
lowercasing, so they can't drift apart.
"""

from __future__ import annotations


def normalize_email(email: str) -> str:
    return email.strip().lower()
