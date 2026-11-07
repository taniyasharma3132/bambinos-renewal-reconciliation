import json, csv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

D = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", D + "DejaVuSans.ttf")); pdfmetrics.registerFont(TTFont("DV-B", D + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DV-I", D + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-B")
NAVY, TEAL, RED, AMBER, GREEN, GREY, LIGHT = [colors.HexColor(c) for c in ("#1f2a44", "#0f8b8d", "#d1495b", "#edae49", "#2a9d5c", "#8d99ae", "#f4f6fa")]
M = json.load(open("../outputs/metrics.json")); AUD = list(csv.DictReader(open("../outputs/invoice_audit.csv", encoding="utf-8")))

body = ParagraphStyle("b", fontName="DV", fontSize=8.6, leading=12.4, textColor=colors.HexColor("#222"), spaceAfter=4)
small = ParagraphStyle("s", parent=body, fontSize=7.2, leading=9.6, spaceAfter=0)
cell = ParagraphStyle("c", parent=body, fontSize=7.1, leading=9.3, spaceAfter=0)
cellb = ParagraphStyle("cb", parent=cell, fontName="DV-B", textColor=colors.white)
h1 = ParagraphStyle("h1", fontName="DV-B", fontSize=15, leading=19, textColor=NAVY, spaceBefore=4, spaceAfter=6)
h2 = ParagraphStyle("h2", fontName="DV-B", fontSize=10.5, leading=14, textColor=TEAL, spaceBefore=8, spaceAfter=4)
bul = ParagraphStyle("bu", parent=body, leftIndent=10, bulletIndent=0, spaceAfter=2.5)
note = ParagraphStyle("n", parent=body, fontSize=7.6, leading=10.4, textColor=colors.HexColor("#555"), fontName="DV-I")
P = lambda t, s=body: Paragraph(t, s)
B = lambda t: Paragraph(t, bul, bulletText="•")

def tbl(rows, widths, head=True, zebra=True, extra=None):
    data = [[Paragraph(str(c), cellb if (head and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3.5), ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
          ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#d5d9e2"))]
    if head: st.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0: st.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(st + (extra or []))); return t

def img(path, w_mm):
    from PIL import Image as PI
    iw, ih = PI.open(path).size; return Image(path, width=w_mm * mm, height=w_mm * mm * ih / iw)

def footer(c, d):
    c.saveState(); c.setFont("DV", 7); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "Taniya Sharma · Bambinos.live AI Program Manager (Operations) · Take-home case")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}"); c.restoreState()

doc = BaseDocTemplate("../docs/Bambinos_AI_PM_Ops_Case_Report.pdf", pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=17*mm,
                      title="Re-engineering the Student Renewal → Class Scheduling Pipeline", author="Taniya Sharma")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(18*mm, 17*mm, A4[0] - 36*mm, A4[1] - 33*mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer)])
W = 174; S = []

rev = f"₹{int(M['revenue_not_scheduled_inr']):,}"  # 126,850 (western grouping avoided below)
rev = "₹1,26,850" if M["revenue_not_scheduled_inr"] == 126850 else rev
f = M["funnel"]; tb = M["to_be"]

# ================= PAGE 1: exec summary =================
S += [P("Re-Engineering the Student Renewal → Class Scheduling Pipeline", h1),
      P("AI Program Manager (Operations) · take-home case for Bambinos.live · Deliverables A, B, D (report) + C (working prototype, in the GitHub repo)", note), Spacer(1, 4)]
tiles = [[Paragraph(f"<font size=15 color='#d1495b'><b>1 of 12</b></font><br/>paid renewals reached a scheduled class by the next morning", cell),
          Paragraph(f"<font size=15 color='#d1495b'><b>{rev}</b></font><br/>of paid renewals waiting, oldest 67 h", cell),
          Paragraph(f"<font size=15 color='#edae49'><b>3 of 12</b></font><br/>paid invoices never reached a valid teacher form", cell),
          Paragraph(f"<font size=15 color='#2a9d5c'><b>8 of 12</b></font><br/>would need zero human touch in the redesigned flow", cell)]]
t = Table(tiles, colWidths=[W/4*mm]*4); t.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), LIGHT), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 7), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7), ("LINEAFTER", (0,0), (-2,-1), 3, colors.white)]))
S += [t, Spacer(1, 6), P("Executive summary", h2),
      P("I analysed the 13 invoices, 12 teacher forms, 4 booking requests and 2 schedule rows in the provided dataset (1-3 Nov 2026, evaluated at the Head of Ops' 4 Nov 09:00 morning view). "
        "<b>The 4-table chain does not leak because people are slow. It leaks because it asks people to re-type data the system already has, with no owner and no clock between steps.</b> "
        "Teachers who do file the form do it fast (median 27 min after payment); Ops approves fast when it looks (median 1.5 h). The damage comes from what falls <i>between</i> those steps."),
      P("What I found", h2),
      B("<b>The teacher form is the main leak.</b> 2 paid invoices have no form at all (84906, 84910), 1 form cites an invoice that does not exist (digits swapped), 1 was submitted twice. Teachers are bimodal: fast, or never."),
      B("<b>Ops approval is a pull queue with no timer.</b> 8 form rows sit pending, all >12 h, oldest 47.5 h. Approved ones took 0.75-2.5 h, so capacity is not the issue; visibility is."),
      B("<b>Two failures are system logic, not human error.</b> A same-batch renewal failed with 'batch full' because the batch is full <i>of the student renewing</i> (5505). A batch-change renewal has no owner at all (5512)."),
      B("<b>Money authority is informal.</b> A 20% discount with no approval trail, a half-paid installment recorded by the teacher as fully paid, and a 'paid' form backed only by a UPI screenshot while the invoice says Failed."),
      P("What I recommend", h2),
      B("<b>Eliminate Step 2 and Step 3 for happy-path renewals.</b> Capture renewal intent when the teacher generates the payment link (batch, plan, discount code); let the verified payment webhook trigger a rules engine that creates the booking and schedule rows and confirms to parent and teacher by WhatsApp."),
      B("<b>Route every exception to exactly one named owner with an SLA timer</b>, using 14 reason codes, with the evidence attached so the owner decides in one click."),
      B("<b>Ship value in week 1 without any automation</b>: a daily 'paid-not-scheduled' list for the Head of Ops, and a fix to the capacity check."),
      P("What I built", h2),
      B("A working reconciliation engine (Python, stdlib only) that outputs auto-approved rows, flagged exceptions with reason codes, and 23 drafted WhatsApp/Slack messages; 13/13 decisions verified by a golden test. Result: <b>5 auto-approved, 3 one-tap parent confirmations, 4 human exceptions, 1 already complete.</b>"),
      P("Caveat I want to be upfront about: 13 invoices over 3 days is a sample, not a population. Every rate in this report is indicative; Day 1-30 of the plan replaces them with 8-12 weeks of production data.", note)]
S.append(PageBreak())

# ================= A =================
S += [P("Deliverable A - Root-cause problem definition &amp; leakage audit", h1),
      P("Method: join every invoice to its form, booking request and schedule rows by ID (and fuzzy-match when IDs fail), then ask at each hop 'what is the first thing that can go wrong here, and who would notice?'. Evidence below is from the dataset, not hypothetical.", body),
      img("fig/funnel.png", 160), Spacer(1, 4), P("A1 · Hidden failure modes found in the data", h2)]
rows = [["#", "Failure mode", "Evidence in the data", "Root cause", "Impact on parent"],
 ["1", "<b>Orphaned invoice</b>", "84906 (₹18,000, 41 h) and 84910 (₹11,000, 22 h): paid, no form in the table", "Process depends on a teacher remembering; no trigger or timer", "Paid, silence, class gap"],
 ["2", "<b>Wrong invoice reference</b>", "Form 3313 cites 84931; the real invoice is 84913 (digits swapped). The pasted link is wrong too", "Free-text re-keying of an ID", "Lookup fails, Ops must chase"],
 ["3", "<b>Duplicate form</b>", "3308 and 3309, same invoice, 5 min apart ('browser froze')", "No idempotency on submit", "Risk of double booking"],
 ["4", "<b>Unclocked approval queue</b>", "8 form rows pending, oldest 47.5 h; approved ones took 0.75-2.5 h", "Ops pulls from a sheet; no SLA or alert", "Class not scheduled"],
 ["5", "<b>False 'batch full'</b>", "Booking 5505: batch 9205 is 6/6, and student 68105 <i>is</i> one of those 6", "Capacity check counts the renewing student as a new seat", "Paid, then told 'full'"],
 ["6", "<b>Stuck allocation</b>", "Booking 5502 'Pending_Batch_Allocation' for 64 h; same batch, 5/6 seats; zero judgement needed", "A human step that needs no human", "Class gap"],
 ["7", "<b>Batch change has no owner</b>", "5512: classbatch_id NULL, 'Awaiting_Parent_Batch_Selection'. No Gita batch at Sat/Sun 11:00 exists in the reference data", "Nobody owns slot offering or capacity", "Waits indefinitely"],
 ["8", "<b>Payer ≠ registered parent</b>", "84904: invoice phone …77, other name and email vs registered …04; only the teacher's remark explains it", "Payment identity is never reconciled", "Delay or wrong account"],
 ["9", "<b>Discount without authority trail</b>", "84907: 20% (₹1,900) 'retention scholarship'; no approval field in any table. Form shows net ₹7,600, so gross-vs-form checks false-alarm", "Discounts are verbal, not coded", "Revenue leakage / disputes"],
 ["10", "<b>Partial payment recorded as full</b>", "84909: installment 1 of 2, ₹5,250 paid of ₹10,500; form says ₹10,500 and 24 sessions", "Teacher records the plan, not the receipt", "Full term on half payment"],
 ["11", "<b>'Paid' without payment truth</b>", "84911: invoice Failed, no gateway id; teacher filed a form 10 min later citing a UPI screenshot", "Screenshot accepted as proof", "Money in limbo or unpaid"],
 ["12", "<b>Data hygiene</b>", "Cyrillic look-alike letters in 84913's parent name; form id 3306 missing from the sequence; Stripe invoices for UAE/US parents stored in INR", "No validation at write time", "Silent match failures"]]
S += [tbl(rows, [6, 27, 55, 50, 36]), Spacer(1, 4),
      P("<b>Not visible in a 3-day sample but certain at hundreds of renewals a week:</b> weekend and night approvals (the sample spans Sun-Tue; 2 of the sampled batches run Sat/Sun); teacher on leave or left; parent pays twice or asks for a refund after approval; siblings under one parent account; mid-term plan upgrades; GCC/US batch times (the schema has no time zone); term-end timing so that a gap opens before the renewed classes start. Also worth asking: invoice 84901 shows only 2 schedule rows for 24 purchased sessions - is scheduling rolling, or incomplete even on the 'good' path?", note),
      P("A2 · Four systemic root causes", h2),
      B("<b>Re-keying:</b> the form re-enters student, class, amount and invoice that already sit in <i>invoices</i>. Every re-key is a typo, a duplicate or a no-show waiting to happen (modes 1-3)."),
      B("<b>No owner, no clock:</b> between each table there is a hand-off, and nothing measures how long a record sits there (modes 4, 6, 7)."),
      B("<b>Business rules live in people's heads:</b> discounts, partial plans, payer identity and 'who counts toward capacity' are applied informally (modes 5, 8-11)."),
      B("<b>Intent is captured after payment, not before:</b> whether the child continues in the same batch is only learned when the form arrives, so nothing can be automated until a human has typed it.")]

# metrics
S += [P("A3 · Quantifying the risk: metrics and SLAs (broken or invisible today)", h2),
      tbl([["Metric", "Definition", "Sample reading (4 Nov 09:00)", "Proposed SLA / target", "Owner"],
 ["<b>Payment-to-Schedule TAT</b>", "paid_at → first class_schedule_bookings row", "1 of 12 done (1.75 h). 11 open, oldest 66.7 h", "P90 ≤ 4 h; zero-touch ≤ 15 min", "Head of Ops"],
 ["<b>Renewal Completion Rate</b>", "% paid renewals scheduled at the check time", "8% (1/12)", "≥ 95% within 24 h", "Head of Ops"],
 ["<b>Orphaned Invoice Rate</b>", "Paid renewals with no valid linked form after 2 h / paid renewals", "25% (3/12: 2 never filed, 1 wrong id)", "0% once form is removed; ≤ 2% during transition", "Ops + Faculty lead"],
 ["<b>Form-to-Approval Age</b>", "Form created → approved; count and age of pending", "Median 1.5 h; 8 pending, all >12 h, oldest 47.5 h", "Clean forms auto in minutes; manual ≤ 2 h", "Ops lead"],
 ["<b>Stuck Invoices &gt;12 h</b>", "Paid, not scheduled, older than 12 h", "11 of 12 paid", "0 without a named owner and timer", "Ops lead"],
 ["<b>Revenue Waiting</b>", "Σ net_amount of paid, not scheduled", rev + " (11 invoices)", "&lt; 5% of weekly renewal value at 9:00", "Head of Ops"],
 ["<b>Touch Rate</b>", "% renewals needing any manual action", "100% today (teacher form + Ops approval for every one)", "≤ 30% (sample projects ~33%)", "Head of Ops"],
 ["<b>Bad / duplicate form rate</b>", "(duplicate + wrong-id forms) / forms", "17% (2/12)", "0% (form retired)", "Faculty lead"],
 ["<b>False Capacity Failure</b>", "Booking failed 'full' while student already in batch", "25% (1/4 booking requests)", "0%", "Product / Eng"],
 ["<b>Exception SLA breach</b>", "Open exceptions past reason-code SLA", "Not measurable today (no owner, no clock)", "≤ 5%", "Ops lead"],
 ["<b>Class Interruption Days</b>", "First renewed class date − last old-term class date", "Not in the data; instrument in Day 1-30", "≤ 0 days for same-batch", "Head of Ops"]],
 [37, 41, 43, 35, 18]),
 Spacer(1, 6), P("Tiers by revenue exposure: the highest-value stuck items in the sample are GCC/US renewals (84906 ₹18,000, 84908 ₹22,000), which are likely the hardest for Ops to chase across time zones (to confirm with Ops) - one reason to make confirmation self-serve by WhatsApp.", note)]
S.append(PageBreak())

# ================= B =================
S += [P("Deliverable B - AI &amp; no-code re-engineered workflow ('zero-touch')", h1),
      P("B1 · Question each step before automating it", h2),
      tbl([["Step", "Why it exists today", "Verdict", "Redesign"],
 ["1 Invoice", "Parent pays via link", "<b>Keep, enrich</b>", "The teacher generates the link from a 'Send renewal link' button that pre-fills student, batch, plan and price and carries <b>intent</b> (same batch / change request) and an optional <b>discount code</b>. Prevention beats detection: typos, wrong amounts and unauthorised discounts cannot be created."],
 ["2 Teacher form", "Invoice lacks intent; Ops does not trust payment data", "<b>Eliminate</b> (happy path)", "Intent moves to link creation. For legacy flows the form stays optional and pre-filled, then retires after Wave 3. Teachers get an instant 'renewal confirmed, credited to you' message, which removes their reason to skip it."],
 ["3 Ops verification", "Check 'right student, right amount, really paid'", "<b>Automate</b>", "These are deterministic joins on a signature-verified webhook. A rules engine does them in seconds; Ops only sees exceptions."],
 ["4 Batch &amp; schedule", "Someone must pick a batch", "<b>Automate / self-serve</b>", "Same batch: automatic (net new seats = 0). Batch change: a WhatsApp list message of 2-3 Ops-curated slots; Ops intervenes only when no slot exists."]],
 [22, 42, 28, 82]),
 Spacer(1, 4), img("fig/flow.png", 150),
 P("B2 · Zero-touch criteria (all must be true)", h2),
 P("Payment captured and signature verified · gross amount equals list price and discount (if any) matches a valid, approved code · invoice student/user/educator/class IDs match master data · same batch and same slot · payer identity matches or is confirmed · no other open invoice for the student in the last 7 days · renewing student's seat retained. In the sample this is <b>8 of 12 paid renewals (67%)</b>: 84901, 84902, 84903, 84905, 84906, 84908, 84910, 84913. One more (84904) needs a one-tap payer confirmation; three (84907 discount, 84909 partial, 84912 batch change) need a human decision.", body)]
S.append(PageBreak())

S += [P("B3 · Smart exception handling: detect, triage, alert exactly one owner", h2),
      P("Each reason code carries a detection rule, an automatic first action, one accountable owner and an SLA. The engine attaches the evidence string, so the owner never has to open four tables.", body),
      tbl([["Reason code", "Detection rule", "Automatic first action", "Owner → escalation", "SLA"],
 ["PAYER_CONTACT_MISMATCH", "Invoice phone/email/name ≠ registered record, IDs match", "WhatsApp the <b>registered</b> number: 'reply YES'", "Parent → Ops agent", "4 h"],
 ["ORPHANED_INVOICE", "Paid, no form linked (id or fuzzy) after 2 h", "Parent one-tap 'same batch?' + teacher nudge", "Parent → Ops agent → Ops lead", "4 h"],
 ["DISCOUNT_NO_APPROVAL_REF", "discount_amount &gt; 0 with no valid code", "Slack card to Ops lead; teacher asked for approver", "Ops lead / Finance", "4 h"],
 ["PARTIAL_PAYMENT", "payment_status = Partially_Paid", "Hold full-term booking; draft pro-rata option; parent instalment link", "Ops lead / Finance", "4 h"],
 ["FORM_AMOUNT_MISMATCH", "Form amount ≠ invoice net_amount", "Teacher told to correct; engine trusts invoice", "Teacher → Ops", "4 h"],
 ["PAYMENT_NOT_CONFIRMED", "Invoice not Paid but form says paid", "Poll gateway order; if captured → auto-approve, else fresh link to parent", "Payments → Ops lead", "4 h"],
 ["BATCH_CHANGE_REQUESTED", "continue_same_batch = No, or slot ≠ current", "Offer 2-3 slots by WhatsApp; Slack card if none exist", "Ops scheduling", "6 h"],
 ["PRICE_MISMATCH / ID_MISMATCH", "Gross ≠ list price; IDs disagree with master", "Block, alert; never auto-fix money or identity", "Ops lead", "4 h"],
 ["<i>Auto-fixed, logged only:</i> INVOICE_ID_TYPO, DUPLICATE_FORM, FORM_APPROVAL_BACKLOG, STUCK_PENDING_ALLOCATION, FALSE_BATCH_FULL", "Secondary-key match; earliest-wins; clean form past 2 h; same-batch pending; renewing student already holds the seat", "Fix and write evidence to the audit log", "Engine (random 5% daily audit by Ops)", "0"]],
 [36, 42, 48, 32, 16]),
 P("B4 · Where AI is used, and where it is deliberately not", h2),
 B("<b>Deterministic rules decide money, identity and capacity.</b> An LLM cannot approve a payment, which makes the system auditable and cheap."),
 B("<b>LLM #1 - remark reader:</b> turns free text ('Mother paid from her number', 'UPI processing screenshot', Hinglish) into structured signals that lower or raise risk. Prompt: prompts/triage_prompt.md."),
 B("<b>LLM #2 - message drafter:</b> adapts tone and language (English / Hindi / Hinglish) around a locked template; facts are injected, never generated. Prompt: prompts/message_drafting_prompt.md."),
 P("B5 · Guardrails that stop automation from making things worse", h2),
 B("<b>Shadow mode first</b> (writes to staging, compared daily against Ops decisions); the bot can only create rows, never edit or delete; every write stamps rule_version and evidence."),
 B("<b>Idempotency</b> on gateway_payment_id (no double bookings); <b>kill-switch</b> flag reverts to manual; auto-pause if a wrong-schedule or double-booking event occurs."),
 B("<b>Message hygiene:</b> max 2 parent messages per invoice per day, quiet hours 21:00-08:00 for parents, send to the <i>registered</i> number for identity checks, amounts verified against the invoice before send."),
 P("Tooling: n8n (self-hosted) or Make for orchestration, MySQL read/write via a service account, WhatsApp Business API templates, Slack, Metabase on the read replica. Node-by-node mapping: docs/n8n_workflow.md.", note)]
S.append(PageBreak())

# ================= C summary =================
S += [P("Deliverable C - Working prototype: results on the provided dataset", h1),
      P("Repo: <b>github.com/&lt;your-username&gt;/bambinos-renewal-reconciliation</b> · run <font name='DV-B'>python src/reconcile.py</font> · 13/13 golden test passing. The engine starts from each <i>invoice</i> so it also catches the ones with no form.", body)]
dec = {"AUTO_APPROVE": "AUTO-APPROVE", "COMPLETED": "COMPLETE", "PARENT_CONFIRM": "PARENT CONFIRM", "EXCEPTION": "EXCEPTION"}
act = {"84901": "No action; end-to-end in 1.75 h", "84902": "Allocate to current batch; schedule; WhatsApp confirm",
       "84903": "Auto-approve clean form; schedule; confirm", "84904": "WhatsApp registered number; Slack only if no YES in 4 h",
       "84905": "Override false 'full' (net new seats 0); schedule; confirm", "84906": "Parent one-tap + teacher nudge; Slack to Ops at 4 h",
       "84907": "Slack Ops lead: approve/reject 20% discount; ask teacher for approver", "84908": "Dedupe 3309; auto-approve 3308; schedule; confirm",
       "84909": "Hold full term; Ops decides pro-rata; teacher corrects form; parent instalment link", "84910": "Parent one-tap + teacher nudge; Slack at 4 h",
       "84911": "Poll gateway; fresh link to parent; teacher told to hold", "84912": "Offer slots to parent; Slack Ops scheduling (no matching batch in data)",
       "84913": "Re-link 3313 → 84913 (all keys match); auto-approve; schedule"}
rows = [["Invoice", "₹ net", "Engine decision", "Reason codes", "What happens next"]]
for a in AUD:
    codes = a["reason_codes"].replace("|", ", ").replace("DATA_HYGIENE_HOMOGLYPH", "homoglyph (info)")
    rows.append([a["invoice_id"], f"{float(a['net_amount']):,.0f}", f"<b>{dec[a['decision']]}</b>", codes or "-", act[a["invoice_id"]]])
col = {"AUTO-APPROVE": GREEN, "COMPLETE": GREY, "PARENT CONFIRM": AMBER, "EXCEPTION": RED}
extra = []
for i, r in enumerate(rows[1:], 1):
    k = r[2].replace("<b>", "").replace("</b>", ""); extra.append(("TEXTCOLOR", (2, i), (2, i), col[k]))
S += [tbl(rows, [14, 14, 26, 56, 64], extra=extra), Spacer(1, 5),
      P("Things the engine caught that a human skim would likely miss: the Cyrillic homoglyph in 84913's name (a name-based lookup fails silently); that 84907's form amount equals <i>net</i> not gross; that 84908's duplicate was filed 5 minutes apart; that 84905's 'full' batch includes the renewing student; that the form for 84913 points to a non-existent invoice yet matches 84913 on user, student, educator and amount.", body),
      P("<b>Known limits:</b> FALSE_BATCH_FULL assumes the active count already includes the renewing student (confidence marked MEDIUM, validate in shadow mode); no approval table exists, so every discount is flagged; the proposed first-session date is simplified; the engine outputs CSV/JSON rather than writing back to MySQL.", note),
      P("2-3 minute Loom outline (optional deliverable): (1) 20 s: the 13 invoices and the funnel; (2) 60 s: run the script, open exceptions.csv and show 84911 and 84913; (3) 40 s: open messages.md, show the parent and Ops drafts; (4) 20 s: dashboard and rollout plan. Script in docs/loom_script.md.", note)]
S.append(PageBreak())

# ================= D =================
S += [P("Deliverable D - Dashboard, SOP and 30-60-90 plan", h1), P("D1 · The Head of Operations' 9:00 dashboard", h2), img("fig/dashboard.png", W),
      P("Refresh every 15 minutes from the event log (Metabase on the read replica, or Google Sheets for week 1). Red/amber thresholds: any P1 item or any unowned stuck invoice turns the header red. Click-through opens the exception card with the evidence. 'Hours saved' is a model until the time study replaces it with measured values.", note),
      P("D2 · SOP: who does what, when", h2),
      tbl([["Role", "Daily responsibility", "Rule of thumb"],
 ["<b>Head of Ops</b>", "9:00 five-minute scan of the six tiles; asks 'why is anything red'", "Zero P1 left at 18:00; weekly review of SLA breaches"],
 ["<b>Ops lead</b>", "9:15 assigns P1/P2 cards; owns discounts, partial plans, price mismatches; 5% random audit of auto-approvals", "Decide in the card: Approve / Reject / Call parent. Three clicks max"],
 ["<b>Ops agent (on shift)</b>", "Works payer confirmations, orphan escalations and batch-change slots; sweeps at 11:00, 15:00, 18:00", "Never edit the booking tables by hand; use the card so the audit log stays complete"],
 ["<b>Weekend on-call agent</b>", "10:00-18:00 for P1/P2 only (weekend batches exist, e.g. 9205 and 9208)", "Automated steps run 24x7; the SLA clock does too"],
 ["<b>Teacher</b>", "Sends renewals only through the link button; discounts only through a code; replies to nudges", "Never accept payment screenshots; ask the parent to retry the link"],
 ["<b>Finance</b>", "Approves discount codes in advance; clears partial-payment decisions", "Policy lives in a code table, not in chat"]], [28, 86, 60]),
 P("SOP for any exception card: (1) read the one-line evidence; (2) choose Approve / Reject / Reach out; (3) the engine updates the tables, messages the parties, closes the card and logs who decided. A card that is not touched by 50% of its SLA pings the owner; at 100% it pings the next level; at 200% it reaches the Head of Ops.", body)]
S.append(PageBreak())

S += [P("D3 · Change management: 200+ teachers, 10 Ops, no broken live schedules", h2),
      tbl([["Wave", "Scope", "Entry gate", "Exit gate / rollback trigger"],
 ["<b>0 Shadow</b> (wk 1-4)", "Engine runs on real data, writes to staging, customer-facing messages OFF. Ops keep working as today", "Read access and data checks complete", "≥ 95% agreement with Ops decisions on 2 weeks of data; every disagreement explained"],
 ["<b>1 Pilot</b> (wk 5-8)", "~20 teachers from 2 categories; same-batch, fully-paid renewals only; WhatsApp confirmations on", "Wave 0 gate met; capacity-logic fix live", "0 double bookings, wrong-schedule rate &lt; 1%; else auto-pause and revert to manual for that cohort"],
 ["<b>2 Scale</b> (wk 9-11)", "All teachers, same-batch happy path; payer confirm, orphan and failed-payment flows", "Wave 1 gate met; Ops trained on cards", "Touch rate falling; P90 TAT ≤ 6 h"],
 ["<b>3 Complete</b> (wk 11-13)", "Link-with-intent for all; slot picker for batch change; legacy form retired", "Teacher adoption &gt; 90%", "Orphan rate 0; P90 TAT ≤ 4 h"]], [28, 62, 38, 46]),
 B("<b>Protecting live classes:</b> the bot only inserts rows; schedule writes go through the same validation as Ops' today; nothing is auto-scheduled for a slot that starts within 2 hours without an Ops check; Ops can undo any bot booking within 24 h; a feature flag per teacher cohort and a global kill-switch."),
 B("<b>Teachers (200+):</b> one 3-minute video and a one-page WhatsApp card in English and Hindi; 10 category champions who answer first-line questions; and a visible win: every confirmed renewal sends the teacher an instant 'credited to you' message. A teacher who sees it works stops skipping the step."),
 B("<b>Ops (10):</b> the job shifts from data entry to exception ownership. Train on the card flow, name an owner per reason code, retire the approval sheet only after Wave 2, and share the hours-saved number so the change reads as capacity returned, not headcount at risk."),
 B("<b>Parents:</b> they only see better service: instant confirmation, one-tap choices, and never a request to pay twice."),
 P("D4 · 30-60-90 day plan", h2),
 tbl([["", "Days 1-30: see it and stop the bleeding", "Days 31-60: automate the happy path", "Days 61-90: scale and retire the form"],
 ["<b>Do</b>", "Baseline on 8-12 weeks of production data (replace this sample's rates); 2-day time-and-motion study; daily 'paid-not-scheduled' list and dashboard v1 in Sheets/Metabase; fix the capacity check; discount-code table and partial-payment policy; shadow-mode engine", "Link-with-intent button; webhook → engine → booking/schedule for same-batch full-pay renewals in the pilot cohort; WhatsApp confirmations; exception cards live with SLA timers", "All teachers on link flow; slot picker for batch change; retire the form and the approval sheet; monthly rule review; hand over a playbook to Ops"],
 ["<b>Measure</b>", "Baseline TAT, orphan rate, touch rate, class interruption days", "Zero-touch ≥ 50%; P90 TAT ≤ 6 h; wrong-schedule rate &lt; 1%", "Zero-touch ≥ 65%; P90 TAT ≤ 4 h; orphan rate 0; ≥ 80 Ops h/week returned"],
 ["<b>Risk to watch</b>", "Data access delays; sample not representative", "Teacher adoption; parents ignoring WhatsApp", "Edge cases (siblings, refunds, time zones) outnumber the sample"]], [18, 52, 52, 52]),
 P("D5 · Time and cost savings (model, assumptions explicit)", h2),
 img("fig/savings.png", 128),
 P("Assumptions (all to be replaced by the Day-30 time study): 400 renewals/week (the brief says 'hundreds'); minutes per renewal as shown: teacher form 4, Ops verify and approve 6, Ops scheduling 2.5 averaged across renewals, chasing 7.5 averaged; to-be uses the sample's mix (67% zero-touch, 8% soft verify at 3 min, 25% human decision at 12 min) plus 0.5 min for the teacher to add intent to the link. "
   "<b>Result: ≈ 20 → 3.75 min per renewal, ≈ 108 Ops-and-teacher hours saved per week</b> (≈ 99 h in a conservative case with 50% zero-touch), roughly 2.5-2.7 FTE-equivalent on a 10-person Ops team, before a 90-day ramp factor. "
   "Run cost is modest: n8n self-hosted or low-tier cloud, Metabase OSS, and about 3 WhatsApp template messages per exception (≈ 400 × 35% × 3 ≈ 420 messages/week at the assumed volume; price per conversation to be quoted by the WhatsApp provider). "
   "Not modelled but likely larger: retention from fewer class interruptions, and recovered revenue from discounts and partial payments being governed.", body)]
S.append(PageBreak())

S += [P("Open questions for the live case review &amp; limitations", h1),
      B("Is the 'active_students_count' inclusive of the renewing student? My FALSE_BATCH_FULL fix depends on it."),
      B("Is the full 24-session term scheduled at once, or rolling? (84901 shows 2 rows for 24 purchased sessions.)"),
      B("What is the discount-approval policy today, and who may authorise a retention discount? What is the partial-payment rule (pro-rata sessions or hold)?"),
      B("How are time zones for GCC/US batches stored? Are Stripe invoices for non-India parents genuinely in INR?"),
      B("How many renewals per week, and what share are same-batch? The 67% zero-touch figure rests on 12 invoices."),
      B("What happens to a seat between term end and renewal; is it held, or released to a waitlist?"),
      P("Limitations", h2),
      P("Small, masked, 3-day sample; no weekend, night or refund behaviour observable; no real WhatsApp, Slack or MySQL connections were made, so the prototype produces drafts and CSVs, not live actions; the time-savings model rests on stated assumptions, not a measured study. Everything is built so these gaps close in the first 30 days.", body),
      P("Appendix · Repository contents", h2),
      tbl([["Path", "Purpose"], ["src/reconcile.py, messages.py, metrics.py", "Engine, drafted follow-ups, SLA metrics"], ["outputs/", "auto_approved.csv, exceptions.csv, messages.md/.json, invoice_audit.csv, metrics.json, reason_codes.csv"],
            ["prompts/", "triage_prompt.md (remark reader), message_drafting_prompt.md"], ["tests/test_golden.py", "13 hand-verified decisions"], ["docs/", "n8n_workflow.md, loom_script.md, this report"]], [62, 112])]
doc.build(S); print("pdf built")
