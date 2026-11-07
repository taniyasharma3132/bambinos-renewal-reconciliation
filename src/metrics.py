"""SLA / leakage metrics feeding the Ops dashboard."""
import statistics
from reconcile import ts, hrs, num

HARD_TO_BE = {"DISCOUNT_NO_APPROVAL_REF", "PARTIAL_PAYMENT", "BATCH_CHANGE_REQUESTED", "PRICE_MISMATCH", "ID_MISMATCH"}

def compute_metrics(audit, raw, as_of, findings, CODES):
    inv, forms, bks, sch = raw["invoices"], raw["forms"], raw["bookings"], raw["sched"]
    paid = [a for a in audit if a["payment_status"] in ("Paid", "Partially_Paid")]
    inv_by = {i["id"]: i for i in inv}
    inv_ids = set(inv_by)

    exact = {f["invoice_id"] for f in forms if f["invoice_id"] in inv_ids}
    funnel = dict(
        invoices_paid=len(paid),
        form_submitted_exact_link=sum(1 for a in paid if a["invoice_id"] in exact),
        form_approved=len({f["invoice_id"] for f in forms if f["approval_status"] == "Approved"}),
        booking_request_created=len({b["invoice_id"] for b in bks}),
        batch_allocated=len({b["invoice_id"] for b in bks if b["batch_allocated"] == "Yes"}),
        scheduled=len({s["invoice_id"] for s in sch if s["is_cancelled"] != "Yes"}))

    # payment -> form lag (first form per invoice incl. typo-linked)
    lag_form = []
    for a in paid:
        fids = a["form_ids"].replace("(fuzzy)", "").split(",")[0]
        f = next((x for x in forms if x["id"] == fids), None) if fids else None
        if f: lag_form.append(hrs(ts(inv_by[a["invoice_id"]]["paid_at"]), ts(f["created_at"])))
    lag_appr = [hrs(ts(f["created_at"]), ts(f["approved_at"])) for f in forms if f["approved_at"]]
    pend = [hrs(ts(f["created_at"]), as_of) for f in forms if f["approval_status"] == "Pending"]
    tat = [hrs(ts(inv_by[s["invoice_id"]]["paid_at"]), ts(s["created_at"])) for s in sch if s["id"] in {"990101"}]

    not_sched = [a for a in paid if a["decision"] != "COMPLETED"]
    stuck12 = [a for a in not_sched if a["hours_since_payment"] and a["hours_since_payment"] > 12]
    orphan_ids = [a["invoice_id"] for a in paid if a["invoice_id"] not in exact]
    dup_extra = len(forms) - len({f["invoice_id"] for f in forms})
    bad_link = [f["id"] for f in forms if f["invoice_id"] not in inv_ids]

    code_counts, dec_counts = {}, {}
    for a in audit:
        dec_counts[a["decision"]] = dec_counts.get(a["decision"], 0) + 1
        for c in filter(None, a["reason_codes"].split("|")): code_counts[c] = code_counts.get(c, 0) + 1

    zt = [a["invoice_id"] for a in paid if a["decision"] != "COMPLETED" and not (set(a["reason_codes"].split("|")) & (HARD_TO_BE | {"PAYER_CONTACT_MISMATCH"}))]
    zt_done = [a["invoice_id"] for a in paid if a["decision"] == "COMPLETED"]
    soft = [a["invoice_id"] for a in paid if "PAYER_CONTACT_MISMATCH" in a["reason_codes"] and not (set(a["reason_codes"].split("|")) & HARD_TO_BE)]
    hard = [a["invoice_id"] for a in paid if set(a["reason_codes"].split("|")) & HARD_TO_BE]

    stuck_table = sorted(({"invoice_id": a["invoice_id"], "hours_since_payment": a["hours_since_payment"], "stage": a["furthest_stage"],
                           "net_amount": a["net_amount"], "decision": a["decision"], "reason_codes": a["reason_codes"]} for a in not_sched),
                         key=lambda x: -x["hours_since_payment"])
    return dict(
        as_of=str(as_of), invoices_total=len(audit), paid_or_partial=len(paid), failed=len(audit) - len(paid),
        funnel=funnel,
        e2e_scheduled=funnel["scheduled"], e2e_rate_of_paid=round(funnel["scheduled"] / len(paid), 3), e2e_tat_hours=tat,
        orphaned_invoice_ids=orphan_ids, orphaned_invoice_rate=round(len(orphan_ids) / len(paid), 3),
        payment_to_form_hours=dict(values=lag_form, median=statistics.median(lag_form), max=max(lag_form)),
        form_to_approval_hours=dict(values=lag_appr, median=statistics.median(lag_appr), max=max(lag_appr)),
        forms_pending=len(pend), forms_pending_oldest_h=max(pend), forms_pending_over_12h=sum(1 for p in pend if p > 12),
        stuck_over_12h=len(stuck12), stuck_over_12h_ids=[a["invoice_id"] for a in stuck12],
        revenue_not_scheduled_inr=sum(a["net_amount"] for a in not_sched),
        duplicate_form_rows=dup_extra, forms_total=len(forms), forms_citing_missing_invoice=bad_link,
        decision_counts=dec_counts, reason_code_counts=code_counts,
        to_be=dict(already_done=zt_done, zero_touch=zt, soft_verify=soft, human_decision=hard,
                   zero_touch_rate_of_paid=round((len(zt) + len(zt_done)) / len(paid), 3)),
        stuck_table=stuck_table, dataset_findings=findings)
