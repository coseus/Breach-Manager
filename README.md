# 🔐 Breach Manager Local (File-Based, Multi-GB Ready)

A fully local, high-performance breach data manager built for security researchers and pentesters.

Designed for handling **multi-gigabyte leak datasets**, wordlists, combo lists, and hash dumps — without using a traditional database.

---

## 🚀 Features

- ✅ 100% Local (No cloud, no external storage)
- ✅ Handles multi-GB datasets
- ✅ Import from folder (drop-based workflow)
- ✅ Supports compressed files:
    - `.txt`
    - `.csv`
    - `.log`
    - `.gz`
    - `.bz2`
    - `.xz`
    - `.zip`
    - `.7z`
    - `.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`
- ✅ Case-sensitive global deduplication
- ✅ Separate export files:
    - Users
    - Passwords
    - Emails
    - Hashes
- ✅ Fast search (uses `ripgrep` if available)
- ✅ Hash type detection
- ✅ Optional HaveIBeenPwned (k-anonymity API)
- ✅ Clean imports folder (auto delete after processing)
- ✅ Per-type rebuild (no need to dedup everything)

---

## 🧠 Architecture (No Database)

Instead of SQLite or Postgres, this tool uses:

```
store/
 ├── raw/# Append-only raw data
 ├── unique/# Deduplicated final exports
 ├── tmp/# Temp directory for external sorting
 └── state.json# Tracks imported files + metadata
```

### Why file-based?

- No DB overhead
- No WAL growth
- No index bloat
- No RAM spikes
- Scales better for very large wordlists (10GB+)

Deduplication is performed using:

```
LC_ALL=C sort -u
```

This uses disk-based external sorting for stability.

---

## 📂 Import Structure

Default import folder:

```
imports/
```

### Automatic Type Detection

If you put files normally in `imports/`, the parser:

- Splits `user:pass`
- Detects emails
- Detects hashes
- Classifies automatically

---

### 🔥 Forced Type Mode (Recommended for Large Dumps)

You can create dedicated folders:

```
imports/
 ├── passwords/
 ├──users/
 ├── emails/
 └── hashes/
```

If a file is inside one of these folders:

- Every line is imported directly as that type
- No detection or parsing is performed
- Faster and more predictable

Example:

```
imports/passwords/rockyou.txt
imports/users/admin_list.txt
```

---

## 🛠 Installation (Kali Linux Recommended)

```bash
sudo apt updatesudo apt install -y ripgrep p7zip-full coreutils

python3 -m venv .venvsource .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## 🧾 Workflow

1. Drop files into `imports/`
2. Click **Scan & Import**
3. Click **Build Unique**
4. Search or export from:

```
store/unique/
```

Exports are plain text files:

```
users.unique.txt
passwords.unique.txt
emails.unique.txt
hashes.unique.txt
```

---

## 🔎 Search

Uses:

- `ripgrep (rg)` if installed (very fast)
- Python fallback if not

Search is:

- Case-sensitive
- Fixed string
- Multi-file aware

---

## 🧹 Clean Imports

After import, you can safely delete processed files:

- Option to move to `_done`
- Or fully wipe the import folder
- Does NOT touch `store/`

---

## 🔐 HIBP Password Check

Implements k-anonymity API:

- Sends only SHA1 prefix (first 5 chars)
- Never sends the raw password
- Fully compliant with HaveIBeenPwned API design

---

## ⚡ Performance Notes

- Handles multi-GB datasets
- Dedup via external sort (disk-based)
- No RAM spikes
- No database growth issues
- Designed for real-world leak datasets

---

## ⚠ Important Notes

- Base64 is treated as password unless placed in `/hashes/`
- Case-sensitive deduplication
- Download via Streamlit is intentionally disabled for large files
- Exports are taken directly from disk

---

## 🧩 Use Cases

- Leak data aggregation
- Combo list cleaning
- Password intelligence analysis
- Hash collection
- Wordlist preparation
- OSINT research
- Red team lab work

---

## 📜 License

For educational and authorized security research only.
