#!/usr/bin/env python3
"""
Validates Palo Alto External Dynamic List (EDL) files.

Files validated:
  allow_ip.txt          — IPv4/IPv6 addresses, CIDR ranges, and IP ranges (IP-type EDL)
  deny_ip.txt           — IPv4/IPv6 addresses, CIDR ranges, and IP ranges (IP-type EDL)
  ssl_bypass_domain.txt — Domain-type EDL (decryption bypass)
  whitelist_domain.txt  — URL-type EDL (URL filtering allow list)

Exit codes: 0 = all valid, 1 = one or more errors found.
"""

import ipaddress
import re
import sys
from pathlib import Path

_errors: list[str] = []


def _error(filepath: str, lineno: int, entry: str, message: str) -> None:
    _errors.append(f"  {filepath}:{lineno}: {message} — {entry!r}")


# ─── IP file validation ───────────────────────────────────────────────────────
# Valid formats: IPv4, IPv4 CIDR, IPv6, IPv6 prefix, IPv4 range (start-end)

def _validate_ip_range(entry: str) -> str | None:
    parts = entry.split("-")
    if len(parts) != 2:
        return "invalid IP range (expected start-end, e.g. 192.168.1.1-192.168.1.255)"
    start_str, end_str = parts
    try:
        start = ipaddress.ip_address(start_str.strip())
        end = ipaddress.ip_address(end_str.strip())
    except ValueError as exc:
        return f"invalid IP address in range: {exc}"
    if type(start) is not type(end):
        return "IP range must use the same address family for both start and end"
    if start > end:
        return f"range start ({start_str}) is after range end ({end_str})"
    return None


def _validate_ip_entry(entry: str) -> str | None:
    # Hyphens only appear in IP ranges; IPv4/IPv6 addresses and CIDRs don't use them.
    if "-" in entry and "/" not in entry:
        return _validate_ip_range(entry)
    try:
        ipaddress.ip_network(entry, strict=False)
        return None
    except ValueError:
        return "not a valid IPv4/IPv6 address, CIDR range, or IP range (start-end)"


def validate_ip_file(filepath: str) -> None:
    path = Path(filepath)
    seen: dict[str, int] = {}
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            entry = raw.rstrip("\r\n").strip()
            if not entry or entry.startswith("#"):
                continue
            if entry in seen:
                _error(filepath, lineno, entry, f"duplicate entry (first seen on line {seen[entry]})")
                continue
            seen[entry] = lineno
            err = _validate_ip_entry(entry)
            if err:
                _error(filepath, lineno, entry, err)


# ─── Domain file validation ───────────────────────────────────────────────────
# Used for ssl_bypass_domain.txt (Domain-type EDL)
# Rules:
#   - No protocol prefix, no path (no /)
#   - Lowercase only
#   - Max 255 characters
#   - Wildcards (* and ^) must be the sole character in their dot-separated token
#   - No consecutive * tokens (*.* pattern)
#   - Max 9 consecutive ^ tokens

_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$")


def _validate_domain_token(tok: str) -> str | None:
    if tok in ("*", "^"):
        return None
    if "*" in tok:
        return f"wildcard * must be the sole character in a token, got {tok!r}"
    if "^" in tok:
        return f"wildcard ^ must be the sole character in a token, got {tok!r}"
    if not _LABEL_RE.match(tok):
        return f"invalid label {tok!r} — use lowercase letters, digits, hyphens only (no leading/trailing hyphen)"
    return None


def validate_domain_entry(entry: str) -> str | None:
    if re.match(r"^https?://", entry, re.IGNORECASE):
        return "remove protocol prefix (http:// or https://)"
    if "/" in entry:
        return "paths are not permitted in domain-type EDL entries (no / allowed)"
    if entry != entry.lower():
        return "entry must be lowercase"
    if len(entry) > 255:
        return f"entry exceeds 255 characters ({len(entry)} chars)"

    tokens = entry.split(".")
    if not tokens[0]:
        return "entry cannot start with a dot"

    for tok in tokens:
        if not tok:
            return "consecutive dots or trailing dot found"
        err = _validate_domain_token(tok)
        if err:
            return err

    # Consecutive * wildcards are a performance hazard and are not supported
    for i in range(len(tokens) - 1):
        if tokens[i] == "*" and tokens[i + 1] == "*":
            return "consecutive * wildcards (e.g. *.*) are not permitted"

    # More than 9 consecutive ^ wildcards are not supported by PAN-OS
    cur = max_run = 0
    for tok in tokens:
        cur = cur + 1 if tok == "^" else 0
        max_run = max(max_run, cur)
    if max_run > 9:
        return f"more than 9 consecutive ^ wildcards ({max_run}) — not supported by PAN-OS"

    return None


def validate_domain_file(filepath: str) -> None:
    path = Path(filepath)
    seen: dict[str, int] = {}
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            entry = raw.rstrip("\r\n").strip()
            if not entry or entry.startswith("#"):
                continue
            if entry in seen:
                _error(filepath, lineno, entry, f"duplicate entry (first seen on line {seen[entry]})")
                continue
            seen[entry] = lineno
            err = validate_domain_entry(entry)
            if err:
                _error(filepath, lineno, entry, err)


# ─── URL file validation ──────────────────────────────────────────────────────
# Used for whitelist_domain.txt (URL-type EDL)
# Rules:
#   - No protocol prefix
#   - Lowercase only
#   - Max 255 characters
#   - Domain token wildcards: * and ^ must be sole character in dot-separated token
#   - ^ is not permitted in the path portion (after the first /)
#   - * must be sole character in each path segment (split by /)
#   - No consecutive * tokens in the domain portion
#   - Max 9 consecutive ^ tokens in the domain portion

def _validate_url_path_segments(path_part: str) -> str | None:
    for seg in path_part.split("/"):
        if not seg:
            continue
        if "^" in seg:
            return "caret (^) wildcard cannot appear in the path (only in the domain)"
        if "*" in seg and seg != "*":
            return f"wildcard * must be the sole character in a path segment, got {seg!r}"
    return None


def validate_url_entry(entry: str) -> str | None:
    if re.match(r"^https?://", entry, re.IGNORECASE):
        return "remove protocol prefix (http:// or https://)"
    if entry != entry.lower():
        return "entry must be lowercase"
    if len(entry) > 255:
        return f"entry exceeds 255 characters ({len(entry)} chars)"

    domain_part, _, path_part = entry.partition("/")

    if not domain_part:
        return "entry cannot start with /"

    # Validate domain portion
    domain_tokens = domain_part.split(".")
    if not domain_tokens[0]:
        return "domain cannot start with a dot"

    for tok in domain_tokens:
        if not tok:
            return "consecutive dots or trailing dot in domain"
        err = _validate_domain_token(tok)
        if err:
            return err

    for i in range(len(domain_tokens) - 1):
        if domain_tokens[i] == "*" and domain_tokens[i + 1] == "*":
            return "consecutive * wildcards (e.g. *.*) are not permitted in domain"

    cur = max_run = 0
    for tok in domain_tokens:
        cur = cur + 1 if tok == "^" else 0
        max_run = max(max_run, cur)
    if max_run > 9:
        return f"more than 9 consecutive ^ wildcards ({max_run}) — not supported by PAN-OS"

    # Validate path portion
    if path_part:
        err = _validate_url_path_segments(path_part)
        if err:
            return err

    return None


def validate_url_file(filepath: str) -> None:
    path = Path(filepath)
    seen: dict[str, int] = {}
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            entry = raw.rstrip("\r\n").strip()
            if not entry or entry.startswith("#"):
                continue
            if entry in seen:
                _error(filepath, lineno, entry, f"duplicate entry (first seen on line {seen[entry]})")
                continue
            seen[entry] = lineno
            err = validate_url_entry(entry)
            if err:
                _error(filepath, lineno, entry, err)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    root = Path(__file__).parent

    files = [
        (root / "allow_ip.txt",          validate_ip_file),
        (root / "deny_ip.txt",           validate_ip_file),
        (root / "ssl_bypass_domain.txt", validate_domain_file),
        (root / "whitelist_domain.txt",  validate_url_file),
    ]

    missing = [str(p) for p, _ in files if not p.exists()]
    if missing:
        for m in missing:
            print(f"ERROR: required file not found: {m}")
        sys.exit(1)

    for filepath, validator in files:
        validator(str(filepath))

    if _errors:
        print(f"VALIDATION FAILED — {len(_errors)} error(s) found:\n")
        for e in _errors:
            print(e)
        sys.exit(1)

    print("VALIDATION PASSED — all EDL files are valid.")


if __name__ == "__main__":
    main()
