"""Financial data connectors — import tax-relevant data from institution exports.

Imports standard file formats that every bank and brokerage provides for free:

- **CSV**: Fidelity positions/transactions/tax-lots, generic bank exports
- **OFX/QFX**: Open Financial Exchange (standard used by Quicken, GnuCash, etc.)
- **Data mapper**: Converts imported records into tax-pipeline structures

No paid APIs required — all data comes from files you download directly from
your institution's website.  More secure than API aggregators because:
- No third-party intermediary holds your credentials
- Data stays local on your machine
- No API keys, tokens, or subscriptions to manage
- Same data, just exported directly from the institution
"""
