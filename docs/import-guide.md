# Financial Data Import Guide

How to download your account data and import it into Financial Manager.

---

## Quick Start

```bash
# 1. Download exports from your institutions (see steps below)
# 2. Drop files into your configured folders
# 3. Run the importer
python scripts/import_financial_data.py --year 2025
```

---

## Step 1 — Download Your Data

### Fidelity (Brokerage)

**What to download:** Positions export + Activity/History export

#### Positions (current holdings & cost basis)

1. Log in at [fidelity.com](https://www.fidelity.com)
2. Go to **Accounts & Trade → Portfolio**
3. Click the **download icon** (⤓) in the upper-right of the positions table
4. Select **CSV** format
5. Save to `~/Downloads/Fidelity/`

> The file will be named something like `Portfolio_Positions_Mar-15-2026.csv`.

#### Activity (transactions: buys, sells, dividends, distributions)

1. From the Portfolio page, click **Activity & Orders**
2. Set the date range to cover the full tax year (e.g., 01/01/2025 – 12/31/2025)
3. Click **Download** (CSV)
4. Save to `~/Downloads/Fidelity/`

> The file will be named something like `History_for_Account_Mar-15-2026.csv`.

#### What the importer reads from Fidelity files

| File type | Data extracted |
|-----------|---------------|
| Positions CSV | Holdings: symbol, quantity, cost basis, market value, gain/loss |
| Activity CSV | Transactions: buys, sells, dividends, capital gains distributions, fees |

---

### Wells Fargo (Bank)

**What to download:** Transaction history

1. Log in at [wellsfargo.com](https://www.wellsfargo.com)
2. Go to **Account Summary → your account**
3. Click **Download Account Activity**
4. Set the date range for the full tax year
5. Format: choose **Comma Separated** (CSV)
6. Save to `~/Downloads/Wells Fargo/`

#### What the importer reads from Wells Fargo files

| Data extracted |
|---------------|
| Transactions: date, description, amount (debits & credits) |
| Auto-categorized: interest income, property tax payments, charitable donations, medical expenses |

---

### State Farm (Bank)

**What to download:** Transaction history or year-end statement

1. Log in at [statefarm.com](https://www.statefarm.com)
2. Go to **Banking → Account Activity**
3. Click **Download** or **Export**
4. Select CSV format and the tax-year date range
5. Save to `~/Downloads/State Farm/`

---

### Any Other Bank or Brokerage

Most institutions offer CSV or OFX/QFX downloads. Look for:
- **"Download transactions"**
- **"Export to CSV"**
- **"Download for Quicken"** (this gives you a `.qfx` file — we support that)
- **"Download OFX"**

Save the file to any folder and pass it with `--path`:

```bash
python scripts/import_financial_data.py --path ~/Downloads/my-export.csv
```

---

## Step 2 — Where to Put the Files

The default download folders are configured in `config/user-config.yaml`:

```yaml
accounts:
  - institution: Fidelity
    export_path: "~/Downloads/Fidelity"
  - institution: Wells Fargo
    export_path: "~/Downloads/Wells Fargo"
  - institution: State Farm
    export_path: "~/Downloads/State Farm"
```

**Just save your downloaded files into those folders.** The importer scans them automatically.

You can change these paths to anywhere you like — just update the YAML.

---

## Step 3 — Run the Importer

### Basic (uses your config file)

```bash
python scripts/import_financial_data.py
```

This scans every `export_path` from your accounts in `config/user-config.yaml`.

### Specify a tax year

```bash
python scripts/import_financial_data.py --year 2025
```

### Point at a specific folder or file

```bash
python scripts/import_financial_data.py --path ~/Downloads/Fidelity
python scripts/import_financial_data.py --path ~/Downloads/statement.qfx
```

You can pass `--path` multiple times:

```bash
python scripts/import_financial_data.py \
  --path ~/Downloads/Fidelity \
  --path ~/Downloads/Wells\ Fargo
```

### Include subfolders

```bash
python scripts/import_financial_data.py --recursive
```

### Machine-readable JSON output

```bash
python scripts/import_financial_data.py --json
```

### Verbose logging

```bash
python scripts/import_financial_data.py -v
```

---

## What You Get

The importer prints a summary broken into tax-relevant sections:

```
══════════════════════════════════════════
  Financial Data Import Summary
══════════════════════════════════════════

Interest Income
  Wells Fargo checking     $42.18
  State Farm savings       $18.50
  Total Interest:          $60.68

Dividend Income
  Fidelity - VTSAX         $1,240.00  (qualified: $980.00)
  Fidelity - VIG           $620.50    (qualified: $580.00)
  Total Dividends:         $1,860.50

Capital Gains / Losses
  AAPL  sold 03/15  short-term   +$350.00
  MSFT  sold 07/22  long-term    +$1,200.00
  Net Short-Term:          $350.00
  Net Long-Term:           $1,200.00

Categorized Transactions
  Charitable donations     $2,500.00
  Property tax payments    $14,200.00
  Medical expenses         $3,100.00
```

This data feeds directly into the tax engine for your return calculation.

---

## Supported File Formats

| Format | Extensions | Source |
|--------|-----------|--------|
| Fidelity Positions CSV | `.csv` | Fidelity portfolio download |
| Fidelity Activity CSV | `.csv` | Fidelity transaction history |
| Wells Fargo CSV | `.csv` | Wells Fargo account download |
| Generic Bank CSV | `.csv` | Any bank with Date/Description/Amount columns |
| OFX (Open Financial Exchange) | `.ofx` | Most banks & brokerages |
| QFX (Quicken Financial Exchange) | `.qfx` | "Download for Quicken" option |

The importer **auto-detects** the format from column headers (CSV) or file structure (OFX/QFX). You don't need to tell it which format — just drop the files in.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No supported files found" | Check that your `export_path` points to a folder containing `.csv`, `.ofx`, or `.qfx` files |
| Wrong institution detected | The auto-detection reads column headers. If your bank's CSV has non-standard headers, use OFX/QFX instead |
| Missing transactions | Make sure your date range covers the full tax year when downloading |
| `ModuleNotFoundError: financial_manager` | Run `pip install -e .` from the project root first |
| OFX parsing errors | Install the optional `ofxtools` package: `pip install ofxtools` (the built-in parser handles most files, but `ofxtools` is more robust) |
