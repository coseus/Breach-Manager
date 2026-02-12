import os
import io
import gzip
import bz2
import lzma
import zipfile
import tarfile
import tempfile
from typing import Iterator, List
import py7zr

SUPPORTED_EXT = (".txt", ".csv", ".log", ".gz", ".bz2", ".xz", ".lzma", ".zip", ".7z", ".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz")

def iter_lines_from_path(path: str) -> Iterator[str]:
    """
    Streaming lines din:
      - plain text
      - .gz/.bz2/.xz
      - .zip (membri)
      - .7z (extract temporar pe disk, apoi citește)
      - tar / tar.gz / tar.bz2 / tar.xz (citește membri ca text)
    """
    lower = path.lower()

    if lower.endswith(".gz") and not lower.endswith(".tar.gz") and not lower.endswith(".tgz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                yield line
        return

    if lower.endswith(".bz2") and not lower.endswith(".tar.bz2"):
        with bz2.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                yield line
        return

    if lower.endswith(".xz") or lower.endswith(".lzma"):
        # poate fi și tar.xz; îl prindem mai jos
        if lower.endswith(".tar.xz"):
            pass
        else:
            with lzma.open(path, "rt", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    yield line
            return

    if lower.endswith(".zip"):
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                if name.endswith("/"):
                    continue
                with z.open(name, "r") as bf:
                    wrapper = io.TextIOWrapper(bf, encoding="utf-8", errors="ignore")
                    for line in wrapper:
                        yield line
        return

    if lower.endswith(".7z"):
        with tempfile.TemporaryDirectory(prefix="bm7z_") as tmpdir:
            with py7zr.SevenZipFile(path, mode="r") as z:
                z.extractall(path=tmpdir)
            for root, _, files in os.walk(tmpdir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    try:
                        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                yield line
                    except Exception:
                        continue
        return

    # tar, tar.gz, tgz, tar.bz2, tar.xz
    if lower.endswith(".tar") or lower.endswith(".tar.gz") or lower.endswith(".tgz") or lower.endswith(".tar.bz2") or lower.endswith(".tar.xz"):
        mode = "r"
        if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
            mode = "r:gz"
        elif lower.endswith(".tar.bz2"):
            mode = "r:bz2"
        elif lower.endswith(".tar.xz"):
            mode = "r:xz"

        with tarfile.open(path, mode) as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                f = tf.extractfile(member)
                if f is None:
                    continue
                try:
                    wrapper = io.TextIOWrapper(f, encoding="utf-8", errors="ignore")
                    for line in wrapper:
                        yield line
                except Exception:
                    continue
        return

    # plain
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            yield line

def expand_paths(base: str) -> List[str]:
    base = os.path.expanduser(base.strip().strip('"').strip("'"))
    if not base or not os.path.exists(base):
        return []
    if os.path.isdir(base):
        out = []
        for root, _, files in os.walk(base):
            for fn in files:
                lf = fn.lower()
                if lf.endswith(SUPPORTED_EXT):
                    out.append(os.path.join(root, fn))
        return sorted(out)
    return [base]
