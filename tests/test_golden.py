"""Golden test: expected decision + reason codes per invoice, hand-verified against the raw CSVs.
Run: python tests/test_golden.py"""
import sys; sys.path.insert(0, "src")
from reconcile import run, ts

EXPECTED = {
 "84901": ("COMPLETED", set()),
 "84902": ("AUTO_APPROVE", {"STUCK_PENDING_ALLOCATION"}),
 "84903": ("AUTO_APPROVE", {"FORM_APPROVAL_BACKLOG"}),
 "84904": ("PARENT_CONFIRM", {"PAYER_CONTACT_MISMATCH", "FORM_APPROVAL_BACKLOG"}),
 "84905": ("AUTO_APPROVE", {"FALSE_BATCH_FULL"}),
 "84906": ("PARENT_CONFIRM", {"ORPHANED_INVOICE"}),
 "84907": ("EXCEPTION", {"DISCOUNT_NO_APPROVAL_REF", "FORM_APPROVAL_BACKLOG"}),
 "84908": ("AUTO_APPROVE", {"DUPLICATE_FORM", "FORM_APPROVAL_BACKLOG"}),
 "84909": ("EXCEPTION", {"PARTIAL_PAYMENT", "FORM_AMOUNT_MISMATCH", "FORM_APPROVAL_BACKLOG"}),
 "84910": ("PARENT_CONFIRM", {"ORPHANED_INVOICE"}),
 "84911": ("EXCEPTION", {"PAYMENT_NOT_CONFIRMED", "FORM_APPROVAL_BACKLOG"}),
 "84912": ("EXCEPTION", {"BATCH_CHANGE_REQUESTED"}),
 "84913": ("AUTO_APPROVE", {"INVOICE_ID_TYPO", "FORM_APPROVAL_BACKLOG"}),
}
audit, *_ = run("data", ts("2026-11-04 09:00:00"))
bad = 0
for a in audit:
    codes = set(filter(None, a["reason_codes"].split("|"))) - {"DATA_HYGIENE_HOMOGLYPH"}
    exp = EXPECTED[a["invoice_id"]]
    ok = (a["decision"], codes) == exp
    bad += not ok
    print(("PASS" if ok else "FAIL"), a["invoice_id"], a["decision"], sorted(codes))
sys.exit(1 if bad else 0)
