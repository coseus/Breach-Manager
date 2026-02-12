import hashlib
import re
import requests

def detect_hash_type(h: str) -> str:
    """
    Case-sensitive dedup nu are legătură cu hash type; aici doar identificăm.
    32-hex poate fi md5 sau ntlm => 'md5_or_ntlm'
    """
    if not h:
        return "necunoscut"
    s = h.strip()
    sl = s.lower()

    if s.startswith(("$2a$", "$2b$", "$2y$")):
        return "bcrypt"
    if s.startswith("$1$"):
        return "md5crypt"
    if s.startswith("$6$"):
        return "sha512crypt"

    if re.fullmatch(r"[0-9a-f]+", sl):
        if len(sl) == 32:
            return "md5_or_ntlm"
        if len(sl) == 40:
            return "sha1"
        if len(sl) == 64:
            return "sha256"
        if len(sl) == 128:
            return "sha512"

    # Base64 heuristic
    if re.fullmatch(r"[A-Za-z0-9+/=]{8,}", s) and len(s) % 4 in (0, 2, 3):
        return "base64"

    return "necunoscut"

def is_pwned_password(password: str) -> bool:
    """
    HIBP Pwned Passwords Range API (k-anonymity).
    Nu trimite parola în clar, doar prefix SHA1 (5 chars).
    """
    if not password:
        return False
    sha1 = hashlib.sha1(password.encode("utf-8", errors="ignore")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    try:
        r = requests.get(
            f"https://api.pwnedpasswords.com/range/{prefix}",
            headers={"User-Agent": "BreachManagerLocalFileBased/1.0"},
            timeout=10,
        )
        if r.status_code != 200:
            return False
        for line in r.text.splitlines():
            h, _count = line.split(":", 1)
            if h == suffix:
                return True
        return False
    except Exception:
        return False
