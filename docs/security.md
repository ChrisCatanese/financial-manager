# Encryption & Security — Financial Manager

## Overview

This repository uses **git-crypt** (AES-256-CTR) to transparently encrypt files
containing personally identifiable information (PII), financial data, and
tax return details. Encrypted files appear as normal plaintext when the repo
is unlocked; on GitHub (or any clone without the key) they are opaque binary.

## What's Encrypted

| File | Sensitivity |
|------|-------------|
| `docs/tax-prep-notes-2025.md` | Names, addresses, wages, account numbers |
| `docs/change-log.json` | Component references with PII context |
| `tests/test_2024_validation.py` | Complete 2024 accepted tax return data |
| `tests/test_intake_pipeline.py` | Real document filenames, financial figures |
| `tests/test_checklist.py` | Real names and tax scenarios |
| `tests/test_scanner.py` | Real document filenames with account numbers |
| `src/financial_manager/engine/intake.py` | iCloud paths, family-specific config |
| `src/financial_manager/engine/assembler.py` | Hardcoded addresses, names |
| `src/financial_manager/engine/extractors.py` | Document-specific patterns |
| `src/financial_manager/engine/scanner.py` | Name-specific classification regex |
| `src/financial_manager/engine/checklist.py` | Name references |
| `scripts/assemble_2025.py` | Family-specific references |

Patterns are defined in `.gitattributes`. Any new file matching these patterns
will be automatically encrypted.

## Key Management

| Item | Location |
|------|----------|
| **Symmetric key** | `~/.config/git-crypt/financial-manager.key` |
| **Permissions** | `chmod 600` (owner read/write only) |
| **Backup** | Store a copy in a password manager or secure vault |

> ⚠️ **If you lose this key, the encrypted files cannot be recovered.**
> Back it up to a password manager (1Password, Bitwarden, etc.) immediately.

## Common Commands

```bash
# Check encryption status
git-crypt status

# Lock the repo (encrypt working copies — use before sharing laptop)
git-crypt lock

# Unlock (decrypt working copies)
git-crypt unlock ~/.config/git-crypt/financial-manager.key

# Export key for backup
git-crypt export-key /path/to/backup.key

# Add a GPG user (alternative to symmetric key)
git-crypt add-gpg-user GPG_KEY_ID
```

## Adding New Encrypted Files

1. Add a pattern to `.gitattributes`:
   ```
   path/to/sensitive-file.py filter=git-crypt diff=git-crypt
   ```
2. Stage and commit the `.gitattributes` change
3. Stage and commit the new file — it will be encrypted automatically

## Security Audit (March 2026)

**What was done:**
- Audited all 114 tracked files for PII (names, SSNs, TINs, addresses, wages)
- Identified 12 files containing sensitive data
- Initialized git-crypt with AES-256 encryption
- Encrypted all 12 files
- Scrubbed unencrypted versions from git history using `git-filter-repo`
- Force-pushed clean history to GitHub
- Cleaned up sensitive exports from `/tmp`
- Key stored securely at `~/.config/git-crypt/` with `chmod 600`

**What is NOT in the repo (confirmed clean):**
- No Social Security Numbers (SSN)
- No complete EIN/TIN numbers
- No passwords or API keys
- No `.env` files with secrets

**What IS encrypted:**
- Real names, addresses, employer names
- W-2 wage amounts, 1099 income figures
- Account numbers (Fidelity, bank)
- Complete 2024 tax return line items
- iCloud filesystem paths
- Document filenames with account references

## Handling Sensitive Data Outside the Repo

| Data | Location | Protection |
|------|----------|------------|
| Tax PDFs | iCloud Drive `~/Library/Mobile Documents/.../Tax/` | iCloud encryption + device passcode |
| Exported photos | `/tmp/photo_exports/` | **Delete after use** — no persistent storage |
| OCR results | `/tmp/` | **Delete after use** |
| Bank statements | Do not store in repo — process in memory only |
| git-crypt key | `~/.config/git-crypt/` | File permissions `600` |

## If the Repo Is Cloned Without the Key

Encrypted files will appear as binary blobs starting with `\x00GITCRYPT\x00`.
They cannot be read, diffed, or searched without unlocking.
Non-encrypted files (API code, frontend, config, requirements docs) remain
readable.
