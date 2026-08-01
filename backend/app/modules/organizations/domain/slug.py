"""Derives a URL/subdomain-safe slug from an organization name.

Per docs/product/WireframeSpec.md §5: "organization slug conflict
resolved automatically... no user-visible slug concept at all." A user
never types or sees a slug — this module only produces candidates for
the application layer to attempt, retrying with a suffix on collision
(app/modules/organizations/application/services.py).

Every candidate this module produces satisfies
app/modules/organizations/domain/entities.py's `_SLUG_PATTERN` (DNS
label rules: lowercase alphanumeric, internal hyphens only, 1-63 chars,
no leading/trailing hyphen) by construction, so `Organization.__post_init__`
never rejects a slug this module generated.
"""

from __future__ import annotations

import re
import uuid

_MAX_SLUG_LENGTH = 63
_NON_ALNUM_RUN = re.compile(r"[^a-z0-9]+")

# Reserves room for "-" plus an 8-hex-character suffix (see
# slug_with_suffix) so a suffixed candidate never exceeds the DNS label
# limit that a bare base candidate is already truncated to respect.
_MAX_BASE_LENGTH = _MAX_SLUG_LENGTH - 9

# Used only if a name produces no usable characters at all (e.g. entirely
# emoji/punctuation) — exceptionally rare, but slugify() must always
# return a valid, non-empty candidate.
_FALLBACK_BASE = "organization"


def slugify(name: str) -> str:
    """The base candidate slug for `name` — no uniqueness guarantee, no
    suffix. Callers needing a fallback candidate after a collision use
    slug_with_suffix() with this same base."""
    candidate = _NON_ALNUM_RUN.sub("-", name.strip().lower()).strip("-")
    if not candidate:
        candidate = _FALLBACK_BASE
    return candidate[:_MAX_BASE_LENGTH].strip("-") or _FALLBACK_BASE


def slug_with_suffix(base: str) -> str:
    """A fallback candidate for retrying after `base` (or a previous
    suffixed candidate) collided — an 8-hex-character random suffix, high
    enough entropy that a second collision is exceptionally unlikely
    without needing to inspect what's already taken."""
    suffix = uuid.uuid4().hex[:8]
    return f"{base[:_MAX_BASE_LENGTH]}-{suffix}"
