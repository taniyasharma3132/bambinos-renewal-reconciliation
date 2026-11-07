# Bambinos.live - Renewal → Class Scheduling: Reconciliation & Auto-Approval Engine

Take-home case: *AI Program Manager (Operations)*. This repo is the **working prototype (Deliverable C)** plus supporting
material for the PDF report (Deliverables A, B, D).

## What it does
Takes the 5 masked CSVs in `data/` and, **starting from each paid invoice** (not from the teacher form), reconciles it across
the 4-table chain and outputs:

| Output | File | Content |
|---|---|---|
| 1. Auto-approved | `outputs/auto_approved.csv` | Rows ready for `class_schedule_bookings` (batch, days, time, sessions, verified amount) |
| 2. Flagged exceptions | `outputs/exceptions.csv` | Exact reason codes, evidence string, owner, SLA, priority |
| 3. Drafted follow-ups | `outputs/messages.md` / `.json` | WhatsApp (parent, teacher) and Slack (Ops, Finance, Payments) drafts with send rules |
| Full trace | `outputs/invoice_audit.csv` | Per-invoice stage reached, hours since payment, decision |
| SLA numbers | `outputs/metrics.json` | Funnel, orphan rate, lags, revenue waiting; feeds the dashboard |
| Reason codes | `outputs/reason_codes.csv` | Catalogue: severity, owner, SLA, auto-action |

## Run
```bash
python src/reconcile.py --data data --out outputs --as-of "2026-11-04 09:00:00"
python tests/test_golden.py        # 13/13 hand-verified decisions
```
Python 3.9+, standard library only. `--as-of` is the "morning view" clock (data spans 1-3 Nov 2026).

## Result on the provided data (13 invoices, as of 4 Nov 09:00)
| Decision | Count | Invoices |
|---|---|---|
| COMPLETED end-to-end | 1 | 84901 |
| AUTO_APPROVE | 5 | 84902, 84903, 84905, 84908, 84913 |
| PARENT_CONFIRM (one-tap) | 3 | 84904, 84906, 84910 |
| EXCEPTION (human decides) | 4 | 84907, 84909, 84911, 84912 |

## Reason codes (severity → who acts)
FIX (engine repairs, logged): `INVOICE_ID_TYPO`, `DUPLICATE_FORM`, `FORM_APPROVAL_BACKLOG`, `STUCK_PENDING_ALLOCATION`, `FALSE_BATCH_FULL`
CONFIRM (parent taps): `ORPHANED_INVOICE`, `PAYER_CONTACT_MISMATCH`
BLOCK (human): `DISCOUNT_NO_APPROVAL_REF`, `PARTIAL_PAYMENT`, `FORM_AMOUNT_MISMATCH`, `PAYMENT_NOT_CONFIRMED`, `BATCH_CHANGE_REQUESTED`, `PRICE_MISMATCH`, `ID_MISMATCH`

## Design choices worth knowing
- **IDs, never names.** Invoice 84913's parent name contains Cyrillic look-alike letters (`М`,`е`), so a name match fails silently. The engine joins on IDs and normalises look-alikes only for the contact comparison.
- **Deterministic for money, LLM for words.** The LLM only reads remarks and polishes tone (`prompts/`).
- **Net vs gross.** Teacher forms record the *net* amount; comparing against gross would falsely flag every discounted renewal.
- **A renewing student already holds a seat** (net new seats = 0), so "batch full" must not block a same-batch renewal (84905).
- **Fuzzy re-link** (84913): wrong invoice id is re-linked only if user, student, educator, amount all match and the id differs by a digit transposition.

## Assumptions & limitations (honest list)
1. 13 invoices over 3 days is a **sample, not a population**; rates are indicative, not statistically meaningful.
2. `FALSE_BATCH_FULL` assumes `active_students_count` already includes the renewing student. Confidence is marked MEDIUM and should be validated in shadow mode.
3. No approval table exists, so *any* discount is flagged. A real discount-code table would remove most of these.
4. `proposed_first_session` = next batch day after `--as-of`; the real rule should continue from the student's last scheduled class.
5. Weekend/night behaviour and time zones (GCC/US batches) cannot be inferred from 3 days of data; flagged as open questions in the report.
6. Names in drafted messages are masked because the source data is masked; production resolves them from the DB.
7. Not in scope: writing back to MySQL. The engine outputs CSV/JSON; `docs/n8n_workflow.md` maps it onto an n8n scenario.

## Layout
```
data/      5 source CSVs (unchanged)       src/       reconcile.py, messages.py, metrics.py
prompts/   triage + drafting prompts       tests/     golden test
outputs/   generated results               docs/      n8n workflow spec, report PDF
```
