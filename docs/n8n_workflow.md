# To-Be workflow as an n8n (or Make) scenario - node by node

Trigger: **Razorpay / Stripe webhook `payment.captured`** (signature-verified, idempotency key = gateway_payment_id)

| # | Node | What it does | Replaces today's step |
|---|------|--------------|------------------------|
| 1 | Webhook | Receives captured payment; rejects bad signature | Teacher pasting invoice link (Step 2) |
| 2 | MySQL: upsert `invoices` | Idempotent write, sets `is_renewal` from link metadata | Step 1 (unchanged) |
| 3 | MySQL: read renewal intent | Payment link carries `student_id, classbatch_id, continue_same_batch, plan, discount_code` (created by the teacher's "Send renewal link" button) | The renewal form (Step 2) |
| 4 | Code node: **rules engine** | Same checks as `src/reconcile.py`: price list, net vs paid, identity, discount code validity, partial payment, capacity (net new seats), batch intent | Ops manual verification (Step 3) |
| 5 | Switch on decision | `AUTO_APPROVE` / `PARENT_CONFIRM` / `EXCEPTION` | - |
| 6a | MySQL: insert `booking_requests` (approved) + `class_schedule_bookings` | Writes to a **staging flag** in shadow mode; real tables once switched on | Steps 3-4 for happy path |
| 6b | WhatsApp API (template msg w/ buttons) | Parent confirm / one-tap batch choice / confirmation | Ops chasing parents |
| 6c | Slack: post to the owner channel by reason code, with a "Resolve" link | Routes exception to ONE named owner | Ops hunting through sheets |
| 7 | Wait + IF (timer per SLA) | Escalate to next owner at SLA breach; page the Head of Ops at 2x SLA | No clock exists today |
| 8 | Google Sheets / Metabase sink | Append event log (stage timestamps) -> dashboard | Invisible funnel today |
| 9 | Error workflow | Any node failure -> Slack #ops-alerts + payment stays in `PENDING_REVIEW` (never silently dropped) | - |

**Safe-by-default rules:** the engine can only *create* rows, never edit or delete; every write carries `created_by='renewal_bot'` and a `rule_version`; a single feature flag (`RENEWAL_BOT_ENABLED`) reverts everything to the manual flow.
**LLM calls (nodes 4b & 6b only):** remark reader (`prompts/triage_prompt.md`) and tone polish (`prompts/message_drafting_prompt.md`). No LLM output is ever used to decide money, identity or capacity.
