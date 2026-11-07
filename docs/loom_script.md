# Loom script (2-3 min)
**0:00-0:20 - Context.** "13 invoices, 4 tables. Only 1 of 12 paid renewals was scheduled the next morning; ₹1.27L of paid renewals waiting." Show funnel slide.
**0:20-1:20 - Prototype.** In terminal: `python src/reconcile.py`. Open `outputs/exceptions.csv`. Walk 84911 (form says paid, invoice Failed → hold, poll gateway) and 84913 (typo 84931 → re-linked on 4 matching keys; Cyrillic homoglyph in name).
**1:20-2:00 - Messages.** Open `outputs/messages.md`: parent one-tap for orphan 84906, Slack card for discount 84907, parent confirmation for auto-approved 84903.
**2:00-2:40 - Design + rollout.** Show to-be flow, dashboard, and the 4-wave rollout with the kill-switch. Close: "Eliminate the form, not just automate it."
