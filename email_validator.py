"""
email_validator.py
~~~~~~~~~~~~~~~~~~
A clean, self-contained email address validator with no third-party dependencies.

Features
--------
- RFC 5321/5322 compliant structural checks
- Local-part & domain validation (length limits, allowed characters)
- TLD sanity check
- Quoted local-parts support
- Helpful, typed error messages via a custom exception
- Convenience `is_valid()` predicate for simple True/False checks
- `suggest_fix()` to catch common domain typos (gmail.con → gmail.com)
- `validate_many()` for batch validation returning separated valid/invalid lists
- `EmailAddress.is_disposable` flag for throwaway-domain detection
"""

import difflib
import re
from dataclasses import dataclass
from typing import NamedTuple


__all__ = [
    "EmailAddress",
    "EmailValidationError",
    "ValidationResult",
    "validate_email",
    "validate_many",
    "suggest_fix",
    "is_valid",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class EmailValidationError(ValueError):
    """Raised when an email address fails validation."""

    def __init__(self, email: str, reason: str) -> None:
        self.email = email
        self.reason = reason
        super().__init__(f"Invalid email {email!r}: {reason}")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmailAddress:
    """Represents a successfully validated email address."""

    raw: str          # Original input (whitespace-stripped)
    local: str        # Part before the '@'
    domain: str       # Part after the '@'

    @property
    def normalised(self) -> str:
        """Lower-case domain; preserve local-part casing (RFC 5321 §2.4)."""
        return f"{self.local}@{self.domain.lower()}"

    @property
    def is_disposable(self) -> bool:
        """Return ``True`` if the domain is a well-known disposable/throwaway provider."""
        return self.domain.lower() in _DISPOSABLE_DOMAINS

    def __str__(self) -> str:
        return self.raw


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# A small but representative set of known disposable/throwaway email domains.
_DISPOSABLE_DOMAINS: frozenset[str] = frozenset({
    "mailinator.com", "guerrillamail.com", "guerrillamail.net",
    "guerrillamail.org", "guerrillamail.de", "guerrillamail.biz",
    "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "spam4.me", "trashmail.com", "trashmail.me", "trashmail.net",
    "yopmail.com", "yopmail.fr", "cool.fr.nf", "jetable.fr.nf",
    "nomail.xl.cx", "mega.zik.dj", "speed.1s.fr", "courriel.fr.nf",
    "moncourrier.fr.nf", "monemail.fr.nf", "monmail.fr.nf",
    "throwam.com", "throwam.net", "dispostable.com",
    "mailnull.com", "spamgourmet.com", "spamgourmet.net",
    "tempmail.com", "temp-mail.org", "10minutemail.com",
    "fakeinbox.com", "maildrop.cc", "sharklasers.com",
})

# Common real domains used for typo-correction suggestions.
_WELL_KNOWN_DOMAINS: tuple[str, ...] = (
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk",
    "outlook.com", "hotmail.com", "live.com", "icloud.com",
    "me.com", "mac.com", "protonmail.com", "proton.me",
    "fastmail.com", "hey.com", "aol.com", "zoho.com",
    "yandex.com", "mail.com", "gmx.com", "gmx.net",
)

# Allowed characters in an *unquoted* local part (RFC 5321 §4.1.2)
_LOCAL_UNQUOTED_RE = re.compile(r'^[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~.-]+$')

# Each label in the domain (between dots)
_DOMAIN_LABEL_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$')


def _validate_local(local: str, email: str) -> None:
    """Validate the local part of an email address."""
    if not local:
        raise EmailValidationError(email, "local part is empty")

    if len(local) > 64:
        raise EmailValidationError(
            email, f"local part exceeds 64 characters (got {len(local)})"
        )

    # Quoted local-part  →  "anything goes" (within reason)
    if local.startswith('"') and local.endswith('"'):
        inner = local[1:-1]
        # Disallow unescaped double-quotes inside
        if re.search(r'(?<!\\)"', inner):
            raise EmailValidationError(
                email, "quoted local part contains unescaped double-quote"
            )
        return  # quoted form is otherwise valid

    # Unquoted local-part
    if local.startswith('.') or local.endswith('.'):
        raise EmailValidationError(email, "local part must not start or end with '.'")

    if '..' in local:
        raise EmailValidationError(email, "local part must not contain consecutive dots")

    if not _LOCAL_UNQUOTED_RE.match(local):
        raise EmailValidationError(
            email, "local part contains invalid characters"
        )


def _validate_domain(domain: str, email: str) -> None:
    """Validate the domain part of an email address."""
    if not domain:
        raise EmailValidationError(email, "domain is empty")

    if len(domain) > 253:
        raise EmailValidationError(
            email, f"domain exceeds 253 characters (got {len(domain)})"
        )

    # IP-address literals like [192.168.1.1] are technically valid but unusual
    if domain.startswith('[') and domain.endswith(']'):
        return  # Accept IP literals as-is (full IP validation is out of scope)

    labels = domain.split('.')

    if len(labels) < 2:
        raise EmailValidationError(email, "domain must have at least two labels (e.g. example.com)")

    for label in labels:
        if not label:
            raise EmailValidationError(email, "domain contains an empty label (consecutive dots?)")

        if len(label) > 63:
            raise EmailValidationError(
                email, f"domain label {label!r} exceeds 63 characters"
            )

        if not _DOMAIN_LABEL_RE.match(label):
            raise EmailValidationError(
                email, f"domain label {label!r} contains invalid characters or format"
            )

    # TLD must be all-alpha (no digits) per IANA convention
    tld = labels[-1]
    if not re.match(r'^[a-zA-Z]{2,}$', tld):
        raise EmailValidationError(
            email, f"TLD {tld!r} must be at least 2 alphabetic characters"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ValidationResult(NamedTuple):
    """Return type of :func:`validate_many`."""
    valid: list[EmailAddress]
    errors: list[tuple[str, str]]   # (original_input, reason)


def suggest_fix(email: str) -> str | None:
    """
    Return a suggested correction for *email* if a common domain typo is
    detected, otherwise return ``None``.

    Only the domain part is corrected; the local-part is left untouched.

    Examples
    --------
    >>> suggest_fix("alice@gmial.com")
    'alice@gmail.com'
    >>> suggest_fix("alice@gmail.com") is None
    True
    """
    email = email.strip()
    if '@' not in email:
        return None
    local, domain = email.rsplit('@', 1)
    matches = difflib.get_close_matches(
        domain.lower(), _WELL_KNOWN_DOMAINS, n=1, cutoff=0.8
    )
    if matches and matches[0] != domain.lower():
        return f"{local}@{matches[0]}"
    return None


def validate_many(emails: list[str]) -> ValidationResult:
    """
    Validate a list of email addresses in one call.

    Parameters
    ----------
    emails:
        An iterable of raw email strings.

    Returns
    -------
    ValidationResult
        A named-tuple with two fields:

        * ``valid``  — list of :class:`EmailAddress` objects for every
          address that passed.
        * ``errors`` — list of ``(original_input, reason)`` pairs for
          every address that failed.
    """
    valid: list[EmailAddress] = []
    errors: list[tuple[str, str]] = []
    for raw in emails:
        try:
            valid.append(validate_email(raw))
        except EmailValidationError as exc:
            errors.append((raw, exc.reason))
        except TypeError as exc:
            errors.append((str(raw), str(exc)))
    return ValidationResult(valid=valid, errors=errors)


def validate_email(email: str) -> EmailAddress:
    """
    Validate *email* and return an :class:`EmailAddress` on success.

    Raises
    ------
    EmailValidationError
        If the address is structurally invalid, with a human-readable reason.
    TypeError
        If *email* is not a ``str``.
    """
    if not isinstance(email, str):
        raise TypeError(f"email must be a str, got {type(email).__name__!r}")

    email = email.strip()

    if not email:
        raise EmailValidationError(email, "address is empty")

    if len(email) > 320:
        raise EmailValidationError(
            email, f"total address exceeds 320 characters (got {len(email)})"
        )

    at_count = email.count('@')
    if at_count == 0:
        raise EmailValidationError(email, "missing '@' symbol")
    if at_count > 1:
        raise EmailValidationError(email, "multiple '@' symbols found")

    local, domain = email.split('@', 1)
    _validate_local(local, email)
    _validate_domain(domain, email)

    return EmailAddress(raw=email, local=local, domain=domain)


def is_valid(email: str) -> bool:
    """Return ``True`` if *email* is valid, ``False`` otherwise (never raises)."""
    try:
        validate_email(email)
        return True
    except (EmailValidationError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Demo / manual testing
# ---------------------------------------------------------------------------

def _demo() -> None:
    test_cases = [
        # (address,                          expect_valid)
        ("alice@example.com",                True),
        ("bob.smith+tag@subdomain.org",      True),
        ('"quoted local"@domain.io',         True),
        ("user@[192.168.1.1]",               True),
        ("UPPER@CASE.EDU",                   True),
        ("x" * 65 + "@example.com",          False),  # local too long
        ("missing-at-sign.com",              False),
        ("double@@at.com",                   False),
        ("dot..dot@example.com",             False),
        (".starts-with-dot@example.com",     False),
        ("no-tld@example",                   False),
        ("bad-tld@example.123",              False),
        ("empty-domain@",                    False),
        ("@no-local.com",                    False),
        ("spaces in local@domain.com",       False),
        ("",                                 False),
    ]

    width = max(len(addr) for addr, _ in test_cases) + 2
    print(f"\n{'Email':<{width}}  {'Expected':<10}  {'Result':<10}  Status")
    print("-" * (width + 35))

    passed = failed = 0
    for addr, expected in test_cases:
        valid = is_valid(addr)
        status = "✅ PASS" if valid == expected else "❌ FAIL"
        result_label = "valid" if valid else "invalid"
        expected_label = "valid" if expected else "invalid"
        print(f"{addr!r:<{width}}  {expected_label:<10}  {result_label:<10}  {status}")
        if valid == expected:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(test_cases)} test cases.")

    # ------------------------------------------------------------------
    # suggest_fix demo
    # ------------------------------------------------------------------
    typos = [
        "alice@gmial.com",
        "bob@yahooo.com",
        "carol@outloook.com",
        "dave@gmail.com",        # already correct → no suggestion
        "eve@totallymadeup.zz",  # no close match → no suggestion
    ]
    print("\n── suggest_fix ────────────────────────────────────")
    for t in typos:
        fix = suggest_fix(t)
        arrow = f"→ {fix}" if fix else "(no suggestion)"
        print(f"  {t!r:<35}  {arrow}")

    # ------------------------------------------------------------------
    # validate_many demo
    # ------------------------------------------------------------------
    batch = [
        "good@example.com",
        "also.good+filter@sub.domain.org",
        "bad-no-at-sign",
        "double@@fail.com",
        "disposable@mailinator.com",
    ]
    result = validate_many(batch)
    print("\n── validate_many ──────────────────────────────────")
    print(f"  Valid ({len(result.valid)}):")
    for addr in result.valid:
        tag = "  ⚠ disposable" if addr.is_disposable else ""
        print(f"    ✅  {addr.normalised}{tag}")
    print(f"  Errors ({len(result.errors)}):")
    for raw, reason in result.errors:
        print(f"    ❌  {raw!r}  →  {reason}")
    print()


if __name__ == "__main__":
    _demo()
