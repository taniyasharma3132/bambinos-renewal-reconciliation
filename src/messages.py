"""Draft WhatsApp / Slack follow-ups from reconciliation results.
Templates are deterministic so they are auditable; in production an LLM polishes tone/language
(see prompts/message_drafting_prompt.md). Names are masked here because the source data is masked;
in production the placeholders resolve from the DB."""
from datetime import datetime
from reconcile import norm, inr, next_batch_date

def tok(name): return norm((name or "there").split(" ")[0]) if False else (name or "there").split(" ")[0]
def t12(t): return datetime.strptime(t, "%H:%M:%S").strftime("%-I:%M %p")
def days_t(days): return days.replace(",", " & ")

def draft_messages(audit, as_of):
    out = []
    def m(iid, channel, role, to, pr, trigger, rule, text):
        out.append(dict(invoice_id=iid, channel=channel, to_role=role, to_contact=to, priority=pr, trigger=trigger, send_rule=rule, text=text))
    for a in audit:
        c = a.get("_ctx")
        if not c: continue
        inv, form, rf, bk, codes, dec, age = c["inv"], c["form"], c["rf"], c["bk"], c["codes"], c["decision"], c["age_h"]
        iid, net = inv["id"], float(inv["net_amount"])
        P, S, E = tok(inv["parent_name"]), tok(rf["student_name_masked"]), rf["educator_name"]
        batch = f"{rf['classbatch_name']} ({days_t(rf['batch_days'])}, {t12(rf['batch_start_time'])})"
        invno = inv["invoice_number"]

        if dec == "AUTO_APPROVE":
            sorry = " Sorry for the wait in confirming this." if age and age > 24 else ""
            m(iid, "WhatsApp", "Parent", inv["mobile"], "P3", "AUTO_APPROVE", "send immediately after schedule rows are written",
              f"Hi {P}, {S}'s renewal is confirmed ✅\n{rf['class_name']} · {batch} with {E}.\nNext class: {next_batch_date(as_of, rf['batch_days'])} (please check the app for the full calendar).{sorry}\nPayment {inr(net)} received · {invno}. Reply HELP if anything looks wrong.")
            continue

        if "ORPHANED_INVOICE" in codes:
            m(iid, "WhatsApp", "Parent", inv["mobile"], "P2", "ORPHANED_INVOICE", "send now; one-tap reply buttons",
              f"Hi {P}, thank you for renewing {S}'s classes 🎉 We've received your payment of {inr(net)} ({invno}).\nShould {S} continue in the same batch?\n{rf['class_name']} · {batch} with {E}\nReply 1 = Yes, continue as is\nReply 2 = I'd like a different day/time")
            m(iid, "WhatsApp", "Teacher", f"educator_id {inv['educator_id']} ({E})", "P2", "ORPHANED_INVOICE", "send now",
              f"Hi {E}, {S}'s renewal payment ({inr(net)}, {invno}) has come through, but we don't see a renewal form from you yet. We've asked the parent to confirm the same batch. If the parent told you about any change in days/time, just reply here with it - no need to fill the form again.")
            m(iid, "Slack #ops-renewals", "Ops agent on shift", "#ops-renewals", "P2", "ORPHANED_INVOICE", "send only if parent has not replied in 4h",
              f"🟠 Paid renewal with no form and no parent confirmation after 4h\nInvoice {iid} · student {inv['student_id']} · {inr(net)} · paid {age:.0f}h ago · teacher {E}\nDefault action ready: same-batch renewal in {rf['classbatch_name']}. Call parent or click Approve default.")
        if "PAYER_CONTACT_MISMATCH" in codes:
            m(iid, "WhatsApp", "Parent (registered number)", rf["registered_mobile_masked"], "P3", "PAYER_CONTACT_MISMATCH", "send now to the REGISTERED number, not the payer number",
              f"Hi, we received a renewal payment of {inr(net)} for {S}'s classes ({invno}) from a phone/email that differs from the one on your account. Just to be safe, please reply YES if this payment was made by you or a family member. Classes will be scheduled right after your reply.")
            m(iid, "Slack #ops-renewals", "Ops agent on shift", "#ops-renewals", "P3", "PAYER_CONTACT_MISMATCH", "send only if no YES in 4h",
              f"🟡 Payer contact mismatch, unconfirmed after 4h\nInvoice {iid} · {inr(net)} · fields differ: see exceptions.csv · teacher remark: '{form['remarks'] if form else ''}'\nAll IDs (student/user/educator/class) and amount match, so risk is low. Confirm with parent by call, then approve.")
        if "DISCOUNT_NO_APPROVAL_REF" in codes:
            disc = float(inv["discount_amount"]); g = float(inv["amount"])
            m(iid, "Slack #ops-leads", "Ops Lead / Finance", "#ops-leads", "P2", "DISCOUNT_NO_APPROVAL_REF", "send now",
              f"🟠 Discount needs approval\nInvoice {iid} · student {inv['student_id']} · list {inr(g)}, discount {inr(disc)} ({disc/g:.0%}), paid {inr(net)}\nTeacher {E} noted: '{form['remarks'] if form else ''}'. No approval reference found. Approve / Reject? (Payment is already taken, so approve-by-default would be the normal outcome; the point is to log who authorised it.)")
            m(iid, "WhatsApp", "Teacher", f"educator_id {inv['educator_id']} ({E})", "P2", "DISCOUNT_NO_APPROVAL_REF", "send now",
              f"Hi {E}, the {disc/g:.0%} retention discount on {S}'s renewal ({invno}) has no approval reference on file. Please reply with who approved it (name/ticket) so Ops can close it today. For future discounts, please use the discount-code link so approval happens before the parent pays.")
        if "PARTIAL_PAYMENT" in codes:
            g = float(inv["amount"])
            m(iid, "Slack #ops-leads", "Ops Lead / Finance", "#ops-leads", "P2", "PARTIAL_PAYMENT", "send now",
              f"🟠 Partial payment, form overstates amount\nInvoice {iid} · {inv['payment_type']} · paid {inr(net)} of {inr(g)} · teacher form says {inr(float(form['amount_paid'])) if form else 'n/a'} paid for 24 sessions\nDecision needed: schedule pro-rata sessions only, or hold until installment 2. Do NOT approve the 24-session form as is.")
            m(iid, "WhatsApp", "Teacher", f"educator_id {inv['educator_id']} ({E})", "P2", "FORM_AMOUNT_MISMATCH", "send now",
              f"Hi {E}, for {S}'s renewal the invoice shows installment 1 of 2 ({inr(net)}), but the form says {inr(g)} was paid. Please don't confirm the full 24 sessions to the parent yet - Ops will confirm the schedule once the balance is cleared.")
            m(iid, "WhatsApp", "Parent", inv["mobile"], "P3", "PARTIAL_PAYMENT", "send now",
              f"Hi {P}, thank you for the first installment of {inr(net)} for {S}'s renewal ({invno}). The second installment of {inr(g-net)} is due by {{due_date}}: {{installment_2_link}}. We'll confirm the next batch of classes as soon as it's received. Reply HELP for any questions.")
        if "PAYMENT_NOT_CONFIRMED" in codes:
            m(iid, "WhatsApp", "Parent", inv["mobile"], "P1", "PAYMENT_NOT_CONFIRMED", "send after gateway poll confirms still not captured",
              f"Hi {P}, we haven't been able to confirm your payment of {inr(net)} for {S}'s renewal - it shows as incomplete on our side. If the amount was deducted from your account, it will either confirm automatically or be refunded by your bank within 2-3 working days, so please don't pay twice. If you'd like to complete it now, here's a fresh secure link: {{new_payment_link}}")
            m(iid, "WhatsApp", "Teacher", f"educator_id {inv['educator_id']} ({E})", "P1", "PAYMENT_NOT_CONFIRMED", "send now",
              f"Hi {E}, {S}'s renewal payment ({invno}) is not confirmed on our side yet, even though a form was submitted with a UPI screenshot. Please hold off on confirming classes with the parent - we're checking with the gateway and will update you within 4 hours.")
            m(iid, "Slack #ops-payments", "Payments owner", "#ops-payments", "P1", "PAYMENT_NOT_CONFIRMED", "send now (engine polls gateway order {} first)".format(inv["gateway_order_id"]),
              f"🔴 Form says paid, invoice says Failed\nInvoice {iid} · order {inv['gateway_order_id']} · {inr(net)} · teacher form 'paid' + UPI screenshot.\nCheck gateway: if captured -> engine auto-approves; if not -> parent already sent a fresh link.")
        if "BATCH_CHANGE_REQUESTED" in codes:
            m(iid, "Slack #ops-scheduling", "Ops scheduling", "#ops-scheduling", "P1" if (age and age > 12) else "P2", "BATCH_CHANGE_REQUESTED", "send now",
              f"🔴 Paid renewal needs a NEW batch, nobody owns it\nInvoice {iid} · student {inv['student_id']} · {inr(net)} · paid {age:.0f}h ago · booking_request {bk['id'] if bk else '-'} status {bk['request_status'] if bk else '-'}\nParent wants {form['preferred_days']} {form['preferred_time_slot'][:5]} (current: {days_t(rf['batch_days'])} {rf['batch_start_time'][:5]}). Reference data shows no {rf['class_name']} batch at that slot: check capacity or open a waitlist/new batch.")
            m(iid, "WhatsApp", "Parent", inv["mobile"], "P2", "BATCH_CHANGE_REQUESTED", "send once Ops has 2-3 slot options",
              f"Hi {P}, thank you for renewing {S}'s classes. You asked for a weekend 11:00 AM slot - we're checking availability with {E}. Options we can offer: {{slot_options}}. Reply with the option number and we'll lock it in. Until then, {S} can keep attending the current batch ({batch}).")
    return out
