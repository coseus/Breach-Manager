import os
import time
import streamlit as st

from dark_mode import init_theme, apply_dark_mode
from store import (
    scan_and_import,
    dedup_all,
    dedup_kind,
    search_in_unique,
    ensure_dirs,
    get_unique_status,
    clean_imports_folder,
    get_counts,
)
from hash_utils import detect_hash_type, is_pwned_password

APP_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_IMPORTS = os.path.join(APP_DIR, "imports")
DEFAULT_STORE = os.path.join(APP_DIR, "store")

st.set_page_config(
    page_title="Breach Manager Local (File-based, Multi-GB)",
    layout="wide",
    page_icon="🔐",
    initial_sidebar_state="expanded",
)

init_theme()
if st.session_state.theme == "dark":
    apply_dark_mode()

ensure_dirs(DEFAULT_STORE)
os.makedirs(DEFAULT_IMPORTS, exist_ok=True)

st.title("Breach Manager Local — File-based (Multi-GB)")
st.caption("Folder drop + dedup global case-sensitive + export separat (users/passwords/emails/hashes). 100% local.")

with st.sidebar:
    st.header("Setări")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("☀ Light", use_container_width=True):
            st.session_state.theme = "light"
            st.rerun()
    with col2:
        if st.button("🌙 Dark", use_container_width=True):
            st.session_state.theme = "dark"
            st.rerun()

    st.divider()
    st.markdown("### Foldere")
    import_dir = st.text_input("Import folder (drop aici fișiere)", value=DEFAULT_IMPORTS)
    store_dir = st.text_input("Store folder (raw/unique/state)", value=DEFAULT_STORE)
    st.caption("Tipuri suportate: txt/csv/log + gz/bz2/xz + zip/7z + tar.*")

tab_import, tab_dedup, tab_search, tab_tools = st.tabs(
    ["Scan & Import", "Build Unique (Dedup)", "Căutare", "Tools"]
)

# ----------------------------
# TAB IMPORT
# ----------------------------
with tab_import:
    st.subheader("Scanare folder și import (manual)")

    pair_seps = st.multiselect(
        "Separatoare perechi (user:pass)",
        [":", ";", "\t", "|", " "],
        default=[":", ";", "\t"],
    )
    chunk_lines = st.number_input(
        "Chunk lines (buffer înainte de append)",
        min_value=10_000,
        max_value=2_000_000,
        value=200_000,
        step=10_000,
    )
    move_done = st.toggle("Mută fișierele importate în _done", value=False)

    if st.button("Scan & Import acum", type="primary", use_container_width=True):
        with st.spinner("Import în curs (streaming)..."):
            stats = scan_and_import(
                store_root=store_dir,
                import_root=import_dir,
                pair_seps=pair_seps,
                move_done=move_done,
                chunk_lines=int(chunk_lines),
            )
        st.success("Gata.")
        st.json(stats)

    st.divider()
    st.markdown("### Status unique (după import, vezi dacă trebuie rebuild)")

    status = get_unique_status(store_dir)

    cols = st.columns(4)
    kinds = ["user", "password", "email", "hash"]
    labels = {"user": "Users", "password": "Passwords", "email": "Emails", "hash": "Hashes"}

    for i, k in enumerate(kinds):
        s = status[k]
        with cols[i]:
            st.markdown(f"**{labels[k]}**")
            if not s["raw_exists"]:
                st.caption("raw: (nu există încă)")
            else:
                if s["outdated"]:
                    st.error("UNIQUE: OUTDATED (needs rebuild)")
                else:
                    st.success("UNIQUE: OK")

                st.caption(
                    "raw mtime: "
                    + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s["raw_mtime"]))
                )
                if s["unique_exists"]:
                    st.caption(
                        "unique mtime: "
                        + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s["unique_mtime"]))
                    )
                else:
                    st.caption("unique: (nu există încă)")

    st.divider()
    st.markdown("### Număr înregistrări (raw vs unique)")

    if st.button("Recalculează numărul înregistrărilor", use_container_width=True):
        with st.spinner("Număr..."):
            counts = get_counts(store_dir)

        cols2 = st.columns(4)
        labels2 = {"user": "Users", "password": "Passwords", "email": "Emails", "hash": "Hashes"}

        for i, k in enumerate(["user", "password", "email", "hash"]):
            with cols2[i]:
                st.metric(
                    label=labels2[k],
                    value=f"{counts[k]['unique']:,}",
                    delta=f"raw: {counts[k]['raw']:,}",
                )

    st.divider()
    st.markdown("### Unde scrie aplicația")
    st.code(
        f"IMPORTS: {os.path.abspath(import_dir)}\n"
        f"STORE/raw: {os.path.abspath(os.path.join(store_dir, 'raw'))}\n"
        f"STORE/unique: {os.path.abspath(os.path.join(store_dir, 'unique'))}\n"
        f"STATE: {os.path.abspath(os.path.join(store_dir, 'state.json'))}",
        language="text",
    )

# ----------------------------
# TAB DEDUP
# ----------------------------
with tab_dedup:
    st.subheader("Dedup global case-sensitive (Build unique)")
    st.write("Poți rula dedup doar pe un tip (rapid) sau pe toate (mai lent).")

    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])

    with c1:
        if st.button("Build Users", type="primary", use_container_width=True):
            with st.spinner("Dedup users (sort -u)..."):
                ok, msg = dedup_kind(store_dir, "user")
            st.success(f"OK: {msg}") if ok else st.error(msg)

    with c2:
        if st.button("Build Passwords", type="primary", use_container_width=True):
            with st.spinner("Dedup passwords (sort -u)..."):
                ok, msg = dedup_kind(store_dir, "password")
            st.success(f"OK: {msg}") if ok else st.error(msg)

    with c3:
        if st.button("Build Emails", type="primary", use_container_width=True):
            with st.spinner("Dedup emails (sort -u)..."):
                ok, msg = dedup_kind(store_dir, "email")
            st.success(f"OK: {msg}") if ok else st.error(msg)

    with c4:
        if st.button("Build Hashes", type="primary", use_container_width=True):
            with st.spinner("Dedup hashes (sort -u)..."):
                ok, msg = dedup_kind(store_dir, "hash")
            st.success(f"OK: {msg}") if ok else st.error(msg)

    with c5:
        if st.button("Build ALL", use_container_width=True):
            with st.spinner("Dedup ALL (sort -u)..."):
                res = dedup_all(store_dir)
            st.success("Dedup terminat.")
            st.json(res)

    st.divider()
    st.warning(
        "Notă: nu folosesc download pentru fișiere multi-GB (Streamlit ar încărca în RAM). "
        "Exportul tău este deja pe disk în store/unique/*.unique.txt."
    )
    st.markdown("### Export paths (pe disk)")
    st.code(
        "\n".join(
            [
                os.path.join(store_dir, "unique", "users.unique.txt"),
                os.path.join(store_dir, "unique", "passwords.unique.txt"),
                os.path.join(store_dir, "unique", "emails.unique.txt"),
                os.path.join(store_dir, "unique", "hashes.unique.txt"),
            ]
        ),
        language="text",
    )

# ----------------------------
# TAB SEARCH
# ----------------------------
with tab_search:
    st.subheader("Căutare în unique (rapid, case-sensitive)")
    st.caption("Preferă `rg` dacă există (Kali: de obicei e instalat).")

    q = st.text_input("Caută valoare (fixed string / substring)")
    kind = st.selectbox("În ce?", ["(toate)", "user", "password", "email", "hash"], index=0)
    max_hits = st.number_input("Max rezultate", min_value=10, max_value=5000, value=200, step=10)

    if st.button("Caută", type="primary"):
        k = None if kind == "(toate)" else kind
        ok, out = search_in_unique(store_dir, q, kind=k, max_hits=int(max_hits))
        if not ok:
            st.error(out)
        else:
            if out.strip():
                st.text_area("Rezultate (format: path:line:content)", value=out, height=350)
            else:
                st.info("Nimic găsit.")

    st.divider()
    st.markdown("### Identificare hash")
    hash_in = st.text_input("Pune un hash (sau ceva suspect) ca să-l identifici")
    if hash_in:
        st.info(f"Tip detectat: {detect_hash_type(hash_in)}")

# ----------------------------
# TAB TOOLS
# ----------------------------
with tab_tools:
    st.subheader("Tools")

    st.markdown("### HIBP (Pwned Passwords) — verificare parole (k-anonymity)")
    st.caption("Atenție: face request extern către api.pwnedpasswords.com, dar nu trimite parola în clar.")
    pwd = st.text_input("Parolă de verificat (nu se salvează)", type="password")
    if st.button("Verifică HIBP", type="primary"):
        if not pwd:
            st.warning("Introdu o parolă.")
        else:
            with st.spinner("Verific..."):
                ok = is_pwned_password(pwd)
            if ok:
                st.warning("Parola apare în breșe (pwned).")
            else:
                st.success("Nu a fost găsită în dataset-ul HIBP (sau nu s-a putut verifica).")

    st.divider()
    st.markdown("### Clean imports folder (șterge TOT după import)")
    st.warning(
        "Atenție: șterge definitiv toate fișierele și subfolderele din folderul de import "
        "(inclusiv _done). Nu atinge store/."
    )

    confirm_clean = st.checkbox(
        "Confirm că vreau să șterg TOT din imports (inclusiv _done).",
        value=False,
    )

    if st.button("🧹 Clean imports folder", type="secondary", use_container_width=True):
        if not confirm_clean:
            st.error("Bifează confirmarea ca să continui.")
        else:
            ok, msg = clean_imports_folder(import_dir)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    st.divider()
    st.markdown("### Recomandare Kali (utilitare)")
    st.code(
        "sudo apt update\n"
        "sudo apt install -y ripgrep p7zip-full coreutils\n",
        language="bash",
    )
