import re
from typing import Iterable, List, Tuple, Optional
from hash_utils import detect_hash_type

COMMENT_PREFIXES = ("#", "//", ";", "--")

def is_comment_or_empty(line: str) -> bool:
    s = line.strip()
    return (not s) or s.startswith(COMMENT_PREFIXES)

def normalize_email_parts(email: str) -> Optional[tuple[str, str]]:
    # case-sensitive dedup: NU lower-case. păstrăm exact cum e.
    if "@" in email and email.count("@") == 1:
        local, dom = email.split("@", 1)
        return (local, dom)
    return None

def infer_single_token(token: str) -> Tuple[str, str]:
    """
    Returnează (value, kind) unde kind ∈ {user, email, password, hash}
    Heuristici:
      - email dacă are un singur @
      - hash dacă detect_hash_type != necunoscut (și pare clar)
      - user dacă e alfanumeric simplu (max 64)
      - altfel: password
    """
    t = token.strip()
    if not t:
        return ("", "password")

    if "@" in t and t.count("@") == 1:
        return (t, "email")

    ht = detect_hash_type(t)
    if ht not in ("necunoscut", "base64"):
        return (t, "hash")

    # user heuristic
    if re.fullmatch(r"[A-Za-z0-9._-]{2,}", t) and len(t) <= 64:
        return (t, "user")

    return (t, "password")

def parse_line(line: str, pair_seps: List[str]) -> List[Tuple[str, str]]:
    """
    Parsează o linie și întoarce o listă de (value, kind).
    Case-sensitive: nu modificăm value.
    Acceptă:
      - user:pass / email:pass / user;pass etc. (pair_seps)
      - altfel: split tokens pe whitespace/virgulă
    """
    s = line.strip("\n\r")
    if is_comment_or_empty(s):
        return []

    # încercăm perechi
    for sep in pair_seps:
        if sep in s:
            left, right = s.split(sep, 1)
            left = left.strip()
            right = right.strip()
            out = []
            if left:
                out.append(infer_single_token(left))
            if right:
                # dacă arată ca hash, pune hash; altfel password
                ht = detect_hash_type(right)
                if ht not in ("necunoscut", "base64"):
                    out.append((right, "hash"))
                else:
                    out.append((right, "password"))
            return [(v, k) for (v, k) in out if v]

    # linie simplă: poate conține mai multe item-uri
    tokens = [t for t in re.split(r"[,\s]+", s.strip()) if t]
    out2 = []
    for t in tokens:
        v, k = infer_single_token(t)
        if v:
            out2.append((v, k))
    return out2
