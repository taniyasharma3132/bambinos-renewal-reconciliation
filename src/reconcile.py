#!/usr/bin/env python3
"""
Bambinos renewal reconciliation & auto-approval engine (prototype)
------------------------------------------------------------------
Invoice-centric: every PAID invoice is the unit of work. The engine joins it to the
teacher form, booking request and schedule rows, runs deterministic checks, and emits:
  1. auto_approved.csv   -> rows ready for class_schedule_bookings
  2. exceptions.csv      -> flagged invoices with exact reason codes + owner + SLA
  3. messages.json / .md -> drafted WhatsApp / Slack follow-ups
  + invoice_audit.csv (full per-invoice trace), metrics.json (SLA numbers), reason_codes.csv

Design rule: money / identity / capacity checks are DETERMINISTIC. An LLM is only used for
(a) reading free-text teacher remarks and (b) polishing message drafts (see /prompts).
Usage: python src/reconcile.py --data data --out outputs --as-of "2026-11-04 09:00:00"
"""
import argparse, csv, json, re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

TS = "%Y-%m-%d %H:%M:%S"

# severity: FIX = engine repairs it silently (logged) | CONFIRM = one-tap parent confirmation | BLOCK = human decides
CODES = {
 "INVOICE_ID_TYPO":         ("FIX",     "Engine",             0, "Re-link form to the invoice matched on user/student/educator/amount; log the correction"),
 "DUPLICATE_FORM":          ("FIX",     "Engine",             0, "Keep earliest form, suppress the rest"),
 "FORM_APPROVAL_BACKLOG":   ("FIX",     "Engine",             0, "Clean form waiting for Ops approval -> auto-approve"),
 "STUCK_PENDING_ALLOCATION":("FIX",     "Engine",             0, "Same-batch renewal waiting for allocation -> allocate to current batch"),
 "FALSE_BATCH_FULL":        ("FIX",     "Engine",             0, "Renewing student already holds a seat -> net new seats = 0; capacity check must not block"),
 "ORPHANED_INVOICE":        ("CONFIRM", "Parent -> Ops",      4, "Paid invoice, no teacher form: ask parent to confirm same-batch default, nudge teacher, escalate to Ops after 4h"),
 "PAYER_CONTACT_MISMATCH":  ("CONFIRM", "Parent -> Ops",      4, "Payer phone/email/name differs from registered contact: ask registered parent number to confirm"),
 "DISCOUNT_NO_APPROVAL_REF":("BLOCK",   "Ops Lead / Finance", 4, "Discount on invoice without an approval reference: approve or reject"),
 "PARTIAL_PAYMENT":         ("BLOCK",   "Ops Lead / Finance", 4, "Installment paid, balance due: apply partial-payment policy, do not schedule full term"),
 "FORM_AMOUNT_MISMATCH":    ("BLOCK",   "Teacher -> Ops",     4, "Teacher-entered amount differs from amount actually paid"),
 "PAYMENT_NOT_CONFIRMED":   ("BLOCK",   "Payments / Ops",     4, "Invoice not in a paid state: poll gateway, never approve on a screenshot"),
 "BATCH_CHANGE_REQUESTED":  ("BLOCK",   "Ops Scheduling",     6, "Parent wants a different batch/time: needs allocation + parent selection; nobody owns it today"),
 "PRICE_MISMATCH":          ("BLOCK",   "Ops Lead / Finance", 4, "Invoice gross amount differs from list price for the batch"),
 "ID_MISMATCH":             ("BLOCK",   "Ops",                4, "user/class/educator on invoice disagree with master data"),
}

HOMOGLYPHS = {"\u041c":"M","\u0435":"e","\u0430":"a","\u043e":"o","\u0440":"p","\u0441":"c","\u0445":"x",
              "\u0443":"y","\u0456":"i","\u0415":"E","\u0410":"A","\u041d":"H","\u041a":"K","\u0412":"B",
              "\u0422":"T","\u041e":"O","\u0420":"P","\u0421":"C","\u0425":"X"}

def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: (None if v in ("NULL", "") else v) for k, v in r.items()} for r in csv.DictReader(f)]

def ts(s):  return datetime.strptime(s, TS) if s else None
def num(s): return float(s) if s not in (None, "") else None
def hrs(a, b): return round((b - a).total_seconds() / 3600, 2) if a and b else None
def inr(x): return f"₹{x:,.0f}"
def has_homoglyph(s): return bool(s) and any(c in HOMOGLYPHS for c in s)
def norm(s): return "".join(HOMOGLYPHS.get(c, c) for c in (s or "")).lower().strip()

def is_transposition(a, b):
    a, b = str(a), str(b)
    if len(a) != len(b): return False
    d = [i for i in range(len(a)) if a[i] != b[i]]
    return len(d) == 2 and d[1] == d[0] + 1 and a[d[0]] == b[d[1]] and a[d[1]] == b[d[0]]

def remark_signals(text):
    """Keyword fallback for the LLM remark-reader (prompts/triage_prompt.md)."""
    t = (text or "").lower(); s = []
    if re.search(r"discount|scholarship|waiver", t): s.append("DISCOUNT_MENTIONED")
    if re.search(r"paid from|mother|father|her number|his number|different number", t): s.append("THIRD_PARTY_PAYER")
    if re.search(r"screenshot|processing|pending|deducted|debited", t): s.append("PAYMENT_PROOF_BY_SCREENSHOT")
    if re.search(r"resubmit|froze|again|duplicate", t): s.append("RESUBMISSION")
    if re.search(r"instead|change|shift|different batch", t): s.append("BATCH_CHANGE_INTENT")
    return s

def next_batch_date(as_of, days_csv):
    wd = {"Mon":0,"Tue":1,"Wed":2,"Thu":3,"Fri":4,"Sat":5,"Sun":6}
    want = {wd[x.strip()] for x in days_csv.split(",")}
    d = as_of.date() + timedelta(days=1)
    while d.weekday() not in want: d += timedelta(days=1)
    return d.isoformat()

def end_time(start, minutes=50):
    return (datetime.strptime(start, "%H:%M:%S") + timedelta(minutes=minutes)).strftime("%H:%M:%S")

def run(data_dir, as_of, orphan_after_h=2.0, approval_sla_h=2.0):
    d = Path(data_dir)
    invoices = [r for r in load(d/"1_invoices.csv") if not r["deleted_at"]]
    forms    = [r for r in load(d/"2_faculty_form_unapproved.csv") if not r["deleted_at"]]
    bookings = [r for r in load(d/"3_booking_requests.csv") if not r["deleted_at"]]
    sched    = [r for r in load(d/"4_class_schedule_bookings.csv") if not r["deleted_at"]]
    ref      = {r["student_id"]: r for r in load(d/"reference_active_batches_and_students.csv") if not r["deleted_at"]}
    inv_ids  = {r["id"] for r in invoices}

    forms_by_inv, bk_by_inv, sc_by_inv = defaultdict(list), defaultdict(list), defaultdict(list)
    for f in forms: forms_by_inv[f["invoice_id"]].append(f)
    for b in bookings: bk_by_inv[b["invoice_id"]].append(b)
    for s in sched:
        if s["is_cancelled"] != "Yes": sc_by_inv[s["invoice_id"]].append(s)

    audit, auto_rows, exc_rows, findings = [], [], [], []
    ids = sorted(int(f["id"]) for f in forms)
    for gap in sorted(set(range(ids[0], ids[-1]+1)) - set(ids)):
        findings.append(f"faculty_form id {gap} missing from the id sequence (deleted / failed submit?) - check audit log")
    for tbl, rows in (("invoices", invoices), ("faculty_form_unapproved", forms)):
        for r in rows:
            for k, v in r.items():
                if has_homoglyph(v):
                    findings.append(f"{tbl} id {r['id']}: field '{k}' contains Cyrillic look-alike characters -> name matching would silently fail")

    for inv in invoices:
        iid, sid = inv["id"], inv["student_id"]
        rf = ref.get(sid)
        paid_at, created, status = ts(inv["paid_at"]), ts(inv["created_at"]), inv["payment_status"]
        net, gross, disc = num(inv["net_amount"]), num(inv["amount"]), num(inv["discount_amount"]) or 0
        age_h = hrs(paid_at or created, as_of)
        codes, detail, fixes = [], {}, []
        def add(code, why): codes.append(code); detail[code] = why

        fl = sorted(forms_by_inv.get(iid, []), key=lambda f: f["created_at"])
        form = fl[0] if fl else None
        if not fl and status != "Failed":
            for c in [f for f in forms if f["invoice_id"] not in inv_ids and f["student_id"] == sid and f["user_id"] == inv["user_id"]]:
                if is_transposition(c["invoice_id"], iid) and c["educator_id"] == inv["educator_id"] and abs(num(c["amount_paid"]) - net) < 0.01:
                    form = c
                    add("INVOICE_ID_TYPO", f"form {c['id']} cites invoice {c['invoice_id']} (does not exist); digits transposed vs {iid}; user/student/educator/amount all match")
                    fixes.append("INVOICE_ID_TYPO")
        if len(fl) > 1:
            add("DUPLICATE_FORM", f"forms {[f['id'] for f in fl]} all cite invoice {iid}; keeping {fl[0]['id']}")
            fixes.append("DUPLICATE_FORM")

        bk  = (bk_by_inv.get(iid) or [None])[0]
        scs = sc_by_inv.get(iid, [])
        if scs:
            audit.append(dict(invoice_id=iid, student_id=sid, payment_status=status, net_amount=net, paid_at=inv["paid_at"],
                form_ids=",".join(f["id"] for f in fl), form_status=form["approval_status"] if form else "",
                booking_request=bk["id"] if bk else "", booking_status=bk["request_status"] if bk else "",
                scheduled_rows=len(scs), furthest_stage="5_scheduled", hours_since_payment=age_h,
                decision="COMPLETED", reason_codes="", note="end-to-end done; payment->schedule TAT %.2fh" % hrs(paid_at, ts(scs[0]["created_at"]))))
            continue

        if status == "Failed":
            claim = num(form["amount_paid"]) if form else None
            add("PAYMENT_NOT_CONFIRMED", "invoice payment_status=Failed, no gateway_payment_id" +
                (f"; teacher form {form['id']} nevertheless claims {inr(claim)} paid (remark: '{form['remarks']}')" if claim else ""))
        elif status == "Partially_Paid":
            add("PARTIAL_PAYMENT", f"{inv['payment_type']}: paid {inr(net)} of {inr(gross)}")

        if status in ("Paid", "Partially_Paid"):
            if rf and abs(gross - num(rf["standard_fee_24_sessions_inr"])) > 0.01:
                add("PRICE_MISMATCH", f"gross {inr(gross)} vs list {inr(num(rf['standard_fee_24_sessions_inr']))}")
            if disc > 0:
                add("DISCOUNT_NO_APPROVAL_REF", f"discount {inr(disc)} ({disc/gross:.0%} of {inr(gross)}); no approval reference in any table; teacher remark: '{form['remarks'] if form else ''}'")
            if form and abs(num(form["amount_paid"]) - net) > 0.01:
                add("FORM_AMOUNT_MISMATCH", f"form {form['id']} says {inr(num(form['amount_paid']))} paid, invoice net_amount is {inr(net)}")

        if rf:
            if (inv["user_id"], inv["class_id"], inv["educator_id"]) != (rf["user_id"], rf["class_id"], rf["educator_id"]):
                add("ID_MISMATCH", "user/class/educator on invoice differ from master data")
            diff = [n for n, a, b in (("mobile", inv["mobile"], rf["registered_mobile_masked"]),
                                      ("email", inv["email"], rf["registered_email_masked"]),
                                      ("parent_name", inv["parent_name"], rf["parent_name_masked"])) if norm(a) != norm(b)]
            if diff:
                add("PAYER_CONTACT_MISMATCH", f"{'/'.join(diff)} on invoice differ from registered parent record" +
                    (f"; teacher remark: '{form['remarks']}'" if form and form['remarks'] else ""))

        if not form and status in ("Paid", "Partially_Paid") and age_h is not None and age_h >= orphan_after_h:
            add("ORPHANED_INVOICE", f"paid {age_h:.1f}h ago, no faculty form linked by id or by fuzzy match")

        if form and rf:
            same = form["continue_same_batch"] == "Yes"
            pref_ok = form["preferred_days"] == rf["batch_days"] and form["preferred_time_slot"] == rf["batch_start_time"]
            if (not same) or not pref_ok:
                add("BATCH_CHANGE_REQUESTED", f"continue_same_batch={form['continue_same_batch']}; wants {form['preferred_days']} {form['preferred_time_slot'][:5]} vs current {rf['batch_days']} {rf['batch_start_time'][:5]}; booking_request {bk['request_status'] if bk else 'not created'}, classbatch_id={(bk or {}).get('classbatch_id')}")
        if bk and bk["request_status"] == "Failed_Batch_Full" and rf and form and form["continue_same_batch"] == "Yes":
            add("FALSE_BATCH_FULL", f"booking {bk['id']} failed 'batch full' ({rf['active_students_count']}/{rf['max_batch_size']}) but student {sid} is ALREADY one of those active students; net new seats = 0")
            fixes.append("FALSE_BATCH_FULL")
        if bk and bk["request_status"] == "Pending_Batch_Allocation":
            add("STUCK_PENDING_ALLOCATION", f"booking {bk['id']} pending allocation for {hrs(ts(bk['created_at']), as_of):.1f}h")
            fixes.append("STUCK_PENDING_ALLOCATION")
        if form and form["approval_status"] == "Pending" and not bk:
            a = hrs(ts(form["created_at"]), as_of)
            if a and a > approval_sla_h:
                add("FORM_APPROVAL_BACKLOG", f"form {form['id']} pending Ops approval for {a:.1f}h")
                fixes.append("FORM_APPROVAL_BACKLOG")

        info = ["DATA_HYGIENE_HOMOGLYPH"] if any(has_homoglyph(v) for t in (inv, form or {}) for v in t.values()) else []

        sev = {CODES[c][0] for c in codes}
        decision = "EXCEPTION" if "BLOCK" in sev else ("PARENT_CONFIRM" if "CONFIRM" in sev else "AUTO_APPROVE")
        confidence = "MEDIUM (assumes the renewing student's seat is retained - validate in shadow week)" if "FALSE_BATCH_FULL" in codes else "HIGH"

        stage = "1_invoice_paid"
        if form: stage = "2_form_submitted"
        if form and form["approval_status"] == "Approved": stage = "3_form_approved"
        if bk: stage = "4_booking_request"
        last_touch = ts((bk or form or {}).get("updated_at")) if (bk or form) else (paid_at or created)
        audit.append(dict(invoice_id=iid, student_id=sid, payment_status=status, net_amount=net, paid_at=inv["paid_at"],
            form_ids=",".join(f["id"] for f in fl) or (form["id"] + "(fuzzy)" if form else ""),
            form_status=form["approval_status"] if form else "", booking_request=bk["id"] if bk else "",
            booking_status=bk["request_status"] if bk else "", scheduled_rows=0, furthest_stage=stage,
            hours_since_payment=age_h, decision=decision, reason_codes="|".join(codes + info),
            note=f"hours since last record update: {hrs(last_touch, as_of)}",
            _ctx=dict(inv=inv, form=form, rf=rf, bk=bk, codes=codes, decision=decision, age_h=age_h, detail=detail)))

        if decision == "AUTO_APPROVE":
            auto_rows.append(dict(invoice_id=iid, source_form_id=form["id"] if form else "", source_booking_request_id=bk["id"] if bk else "",
                student_id=sid, user_id=inv["user_id"], educator_id=inv["educator_id"], class_id=inv["class_id"],
                classbatch_id=rf["current_classbatch_id"], booking_type="Regular_Renewal",
                sessions_to_schedule=(form or {}).get("sessions_purchased", 24), batch_days=rf["batch_days"],
                start_time=rf["batch_start_time"], end_time=end_time(rf["batch_start_time"]),
                proposed_first_session=next_batch_date(as_of, rf["batch_days"]), amount_verified_inr=net,
                auto_fixes="|".join(fixes), confidence=confidence, hours_since_payment=age_h))
        else:
            pr = "P1" if (decision == "EXCEPTION" and age_h and age_h > 24) or "PAYMENT_NOT_CONFIRMED" in codes else ("P2" if decision == "EXCEPTION" else "P3")
            human = [c for c in codes if CODES[c][0] != "FIX"]
            exc_rows.append(dict(invoice_id=iid, student_id=sid, decision=decision, priority=pr,
                reason_codes="|".join(human), auto_fixed="|".join(fixes),
                owner="; ".join(sorted({CODES[c][1] for c in human})), sla_hours=min(CODES[c][2] for c in human),
                hours_since_payment=age_h, amount_inr=net, evidence=" || ".join(f"{c}: {detail[c]}" for c in codes),
                remark_signals="|".join(remark_signals(form["remarks"])) if form else ""))
    return audit, auto_rows, exc_rows, findings, dict(forms=forms, bookings=bookings, invoices=invoices, sched=sched, ref=ref)

def write_csv(path, rows):
    if not rows: return
    keys = [k for k in rows[0] if not k.startswith("_")]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

if __name__ == "__main__":
    from messages import draft_messages
    from metrics import compute_metrics
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data"); ap.add_argument("--out", default="outputs")
    ap.add_argument("--as-of", default="2026-11-04 09:00:00")
    a = ap.parse_args()
    as_of = ts(a.as_of); out = Path(a.out); out.mkdir(exist_ok=True, parents=True)
    audit, auto_rows, exc_rows, findings, raw = run(a.data, as_of)
    msgs = draft_messages(audit, as_of)
    metrics = compute_metrics(audit, raw, as_of, findings, CODES)
    write_csv(out/"invoice_audit.csv", audit); write_csv(out/"auto_approved.csv", auto_rows); write_csv(out/"exceptions.csv", exc_rows)
    (out/"messages.json").write_text(json.dumps(msgs, indent=2, ensure_ascii=False), encoding="utf-8")
    (out/"metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out/"reason_codes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["code","severity","owner","sla_hours","auto_action"])
        for c,(s,o,h,t) in CODES.items(): w.writerow([c,s,o,h,t])
    md = [f"# Drafted follow-ups (as of {a.as_of})\n"]
    for m in msgs:
        body = m["text"].replace("\n", "\n> ")
        md.append(f"### Invoice {m['invoice_id']} · {m['channel']} → {m['to_role']} · {m['priority']} · {m['trigger']}\n> {body}\n")
    (out/"messages.md").write_text("\n".join(md), encoding="utf-8")
    print(f"as-of {a.as_of}: {len(audit)} invoices | auto-approved {len(auto_rows)} | flagged {len(exc_rows)} | completed {sum(1 for x in audit if x['decision']=='COMPLETED')} | messages {len(msgs)}")
