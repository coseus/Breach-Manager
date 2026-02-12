import os
import json
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from importers import expand_paths, iter_lines_from_path
from parsing import parse_line, is_comment_or_empty

KINDS = ("user", "password", "email", "hash")


def ensure_dirs(root: str):
    os.makedirs(root, exist_ok=True)
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    os.makedirs(os.path.join(root, "unique"), exist_ok=True)
    os.makedirs(os.path.join(root, "tmp"), exist_ok=True)


def state_path(root: str) -> str:
    return os.path.join(root, "state.json")


def _default_state() -> Dict:
    return {
        "imported_files": {},
        "meta": {
            "last_import_ts": 0.0,
            "last_dedup_ts": {
                "user": 0.0,
                "password": 0.0,
                "email": 0.0,
                "hash": 0.0,
            },
        },
    }


def load_state(root: str) -> Dict:
    p = state_path(root)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                st = json.load(f)
        except Exception:
            st = _default_state()
    else:
        st = _default_state()

    # backfill pentru state vechi
    st.setdefault("imported_files", {})
    st.setdefault("meta", {})
    st["meta"].setdefault("last_import_ts", 0.0)
    st["meta"].setdefault("last_dedup_ts", {})
    for k in KINDS:
        st["meta"]["last_dedup_ts"].setdefault(k, 0.0)
    return st


def save_state(root: str, state: Dict):
    p = state_path(root)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def file_fingerprint(path: str) -> Tuple[int, float]:
    st = os.stat(path)
    return (int(st.st_size), float(st.st_mtime))


def is_already_imported(state: Dict, path: str) -> bool:
    fp = file_fingerprint(path)
    rec = state.get("imported_files", {}).get(path)
    return rec == {"size": fp[0], "mtime": fp[1]}


def mark_imported(state: Dict, path: str):
    size, mtime = file_fingerprint(path)
    state.setdefault("imported_files", {})[path] = {"size": size, "mtime": mtime}


def raw_path(root: str, kind: str) -> str:
    # users.txt, passwords.txt, emails.txt, hashes.txt
    return os.path.join(root, "raw", f"{kind}s.txt")


def unique_path(root: str, kind: str) -> str:
    return os.path.join(root, "unique", f"{kind}s.unique.txt")


def append_values(root: str, kind: str, values: List[str]):
    p = raw_path(root, kind)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a", encoding="utf-8", errors="ignore") as f:
        for v in values:
            f.write(v)
            f.write("\n")


def _detect_forced_kind_from_path(path: str) -> Optional[str]:
    """
    Dacă fișierul e pus într-un subfolder dedicat:
      imports/passwords/...  => password
      imports/users/...      => user
      imports/emails/...     => email
      imports/hashes/...     => hash
    Atunci forțăm tipul și importăm fiecare linie direct ca acel tip (fără parse).
    """
    lp = path.lower().replace("\\", "/")
    # căutăm secvențe /passwords/ etc.
    for k in KINDS:
        if f"/{k}s/" in lp:
            return k
    return None


def scan_and_import(
    store_root: str,
    import_root: str,
    pair_seps: List[str],
    move_done: bool = False,
    done_dir_name: str = "_done",
    chunk_lines: int = 200_000,
) -> Dict[str, int]:
    """
    Scanează import_root (folder sau fișier), importă doar fișiere noi (size+mtime),
    scrie în store/raw/*.txt (append-only).

    MOD NOU:
      - dacă fișierul e în subfolder dedicat (passwords/users/emails/hashes),
        forțează tipul și importă fiecare linie direct ca acel tip (fără detectare/parsing).
      - altfel, folosește parse_line() (detectare + perechi user:pass).

    Case-sensitive: NU modificăm valorile.
    """
    ensure_dirs(store_root)
    state = load_state(store_root)

    paths = expand_paths(import_root)
    stats = {k: 0 for k in KINDS}
    stats["files_seen"] = len(paths)
    stats["files_imported"] = 0
    stats["lines_processed"] = 0
    stats["forced_mode_files"] = 0

    imported_any = False

    for path in paths:
        if is_already_imported(state, path):
            continue

        imported_any = True
        stats["files_imported"] += 1

        forced_kind = _detect_forced_kind_from_path(path)
        if forced_kind:
            stats["forced_mode_files"] += 1

        buffers = {k: [] for k in KINDS}
        buffered_lines = 0

        for line in iter_lines_from_path(path):
            if is_comment_or_empty(line):
                continue

            if forced_kind:
                v = line.strip()
                if v:
                    buffers[forced_kind].append(v)
                    stats[forced_kind] += 1
                    stats["lines_processed"] += 1
                    buffered_lines += 1
            else:
                items = parse_line(line, pair_seps=pair_seps)
                if not items:
                    continue

                for val, kind in items:
                    if kind in buffers and val:
                        buffers[kind].append(val)
                        stats[kind] += 1
                stats["lines_processed"] += 1
                buffered_lines += 1

            if buffered_lines >= chunk_lines:
                for k in KINDS:
                    if buffers[k]:
                        append_values(store_root, k, buffers[k])
                        buffers[k].clear()
                buffered_lines = 0

        # flush
        for k in KINDS:
            if buffers[k]:
                append_values(store_root, k, buffers[k])

        mark_imported(state, path)
        save_state(store_root, state)

        if move_done:
            done_dir = os.path.join(os.path.dirname(path), done_dir_name)
            os.makedirs(done_dir, exist_ok=True)
            try:
                shutil.move(path, os.path.join(done_dir, os.path.basename(path)))
            except Exception:
                # dacă nu se poate muta (permisiuni/fs), nu blocăm importul
                pass

    if imported_any:
        state["meta"]["last_import_ts"] = float(__import__("time").time())
        save_state(store_root, state)

    return stats


def has_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def get_unique_status(store_root: str) -> Dict[str, Dict]:
    """
    Status per kind:
      - raw_exists, unique_exists
      - raw_mtime, unique_mtime
      - outdated dacă raw e mai nou decât unique sau dacă ai importat după ultimul dedup pe acel tip.
    """
    ensure_dirs(store_root)
    stt = load_state(store_root)
    last_import_ts = float(stt["meta"].get("last_import_ts", 0.0))
    last_dedup_ts = stt["meta"].get("last_dedup_ts", {})

    out = {}
    for k in KINDS:
        rp = raw_path(store_root, k)
        up = unique_path(store_root, k)

        raw_exists = os.path.exists(rp)
        unique_exists = os.path.exists(up)

        raw_mtime = os.path.getmtime(rp) if raw_exists else 0.0
        unique_mtime = os.path.getmtime(up) if unique_exists else 0.0

        dedup_ts_k = float(last_dedup_ts.get(k, 0.0))

        outdated = False
        if raw_exists:
            if (not unique_exists) or (raw_mtime > unique_mtime):
                outdated = True
            if last_import_ts > dedup_ts_k:
                outdated = True

        out[k] = {
            "raw_path": rp,
            "unique_path": up,
            "raw_exists": raw_exists,
            "unique_exists": unique_exists,
            "raw_mtime": raw_mtime,
            "unique_mtime": unique_mtime,
            "last_import_ts": last_import_ts,
            "last_dedup_ts": dedup_ts_k,
            "outdated": outdated,
        }
    return out


def _run_sort_u(src: str, dst: str, tmpdir: str) -> Tuple[bool, str]:
    if not has_cmd("sort"):
        return False, "Nu există 'sort' în PATH. (Pe Kali ar trebui să existe.)"

    # LC_ALL=C => sort rapid byte-wise; case-sensitive by default.
    cmd = [
        "bash",
        "-lc",
        f'LC_ALL=C sort -u -S 50% --parallel="$(nproc 2>/dev/null || echo 2)" -T "{tmpdir}" "{src}" -o "{dst}"',
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, dst
    except subprocess.CalledProcessError as e:
        return False, f"sort -u a eșuat: {e.stderr[:4000]}"


def dedup_kind(store_root: str, kind: str) -> Tuple[bool, str]:
    """
    Dedupe global (case-sensitive) pentru un singur tip folosind sort -u.
    Actualizează state.meta.last_dedup_ts[kind] la succes.
    """
    if kind not in KINDS:
        return False, f"Kind invalid: {kind}"

    ensure_dirs(store_root)
    stt = load_state(store_root)

    src = raw_path(store_root, kind)
    dst = unique_path(store_root, kind)
    tmpdir = os.path.join(store_root, "tmp")
    os.makedirs(tmpdir, exist_ok=True)

    if not os.path.exists(src):
        return False, f"Nu există sursă: {src}"

    ok, msg = _run_sort_u(src, dst, tmpdir)
    if ok:
        stt["meta"]["last_dedup_ts"][kind] = float(__import__("time").time())
        save_state(store_root, stt)
        return True, msg
    return False, msg


def dedup_all(store_root: str) -> Dict[str, str]:
    results = {}
    for k in KINDS:
        ok, msg = dedup_kind(store_root, k)
        results[k] = msg if ok else f"ERROR: {msg}"
    return results


def search_in_unique(store_root: str, query: str, kind: Optional[str] = None, max_hits: int = 200) -> Tuple[bool, str]:
    """
    Caută în fișierele unique. Preferă ripgrep (rg). Fallback: python scan (lent).
    """
    if not query:
        return True, ""

    if kind:
        paths = [unique_path(store_root, kind)]
    else:
        paths = [unique_path(store_root, k) for k in KINDS]

    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return False, "Nu există fișiere unique. Rulează întâi Dedup (Build unique)."

    if has_cmd("rg"):
        cmd = ["rg", "-n", "--fixed-strings", "--no-mmap", "--max-count", str(max_hits), query] + paths
        try:
            out = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
            return True, out.strip()
        except Exception as ex:
            return False, f"Eroare rg: {ex}"

    # fallback python (lent la GB-uri)
    hits = []
    try:
        for p in paths:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, start=1):
                    if query in line:
                        hits.append(f"{p}:{i}:{line.rstrip()}")
                        if len(hits) >= max_hits:
                            break
            if len(hits) >= max_hits:
                break
        return True, "\n".join(hits)
    except Exception as ex:
        return False, f"Eroare fallback search: {ex}"


def clean_imports_folder(import_root: str) -> Tuple[bool, str]:
    """
    Șterge TOT conținutul din import_root (fișiere + foldere, inclusiv _done).
    NU șterge import_root în sine.
    """
    path = os.path.expanduser(import_root.strip().strip('"').strip("'"))
    if not path:
        return False, "Import folder gol."
    if not os.path.exists(path):
        return False, f"Nu există: {path}"
    if not os.path.isdir(path):
        return False, f"Nu e folder: {path}"

    deleted_files = 0
    deleted_dirs = 0
    errors = 0

    for name in os.listdir(path):
        p = os.path.join(path, name)
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
                deleted_dirs += 1
            else:
                os.remove(p)
                deleted_files += 1
        except Exception:
            errors += 1

    msg = f"Șters: {deleted_files} fișiere, {deleted_dirs} foldere. Erori: {errors}."
    return (errors == 0), msg


def count_lines(path: str) -> int:
    """
    Numără linii folosind wc -l (rapid, fără RAM spike).
    Fallback la Python dacă wc nu există.
    """
    if not os.path.exists(path):
        return 0

    if has_cmd("wc"):
        try:
            result = subprocess.run(
                ["wc", "-l", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            return int(result.stdout.strip().split()[0])
        except Exception:
            pass

    # fallback (mai lent)
    count = 0
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for _ in f:
            count += 1
    return count


def get_counts(store_root: str) -> Dict[str, Dict[str, int]]:
    """
    Returnează numărul de înregistrări raw și unique pentru fiecare tip.
    """
    out: Dict[str, Dict[str, int]] = {}
    for k in KINDS:
        rp = raw_path(store_root, k)
        up = unique_path(store_root, k)
        out[k] = {
            "raw": count_lines(rp) if os.path.exists(rp) else 0,
            "unique": count_lines(up) if os.path.exists(up) else 0,
        }
    return out
