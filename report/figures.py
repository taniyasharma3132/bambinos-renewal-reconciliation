import json, csv
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
OUT = "fig/"
NAVY, TEAL, RED, AMBER, GREEN, GREY, LIGHT = "#1f2a44", "#0f8b8d", "#d1495b", "#edae49", "#2a9d5c", "#8d99ae", "#f4f6fa"
M = json.load(open("../outputs/metrics.json"))
EXC = list(csv.DictReader(open("../outputs/exceptions.csv", encoding="utf-8")))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

def inr(x): 
    s = f"{int(x):,}"; 
    # Indian grouping
    n = str(int(x)); 
    if len(n) > 3: n = n[:-3][::-1]; n = ",".join([n[i:i+2] for i in range(0, len(n), 2)])[::-1] + "," + str(int(x))[-3:]
    return "₹" + n

# ---------- 1. funnel ----------
def funnel():
    f = M["funnel"]
    stages = [("Invoices paid (Step 1)", f["invoices_paid"]), ("Teacher form linked (Step 2)", f["form_submitted_exact_link"]),
              ("Form approved by Ops (Step 3)", f["form_approved"]), ("Booking request created", f["booking_request_created"]),
              ("Batch allocated", f["batch_allocated"]), ("Classes scheduled (Step 4)", f["scheduled"])]
    leaks = ["3 lost: 2 orphaned (never filed) + 1 wrong invoice id", "5 forms waiting for Ops, oldest 47.5h", "no loss",
             "3 stuck: pending 64h · false 'batch full' · no owner for batch change", "no loss"]
    fig, ax = plt.subplots(figsize=(8.6, 3.5))
    for i, (n, v) in enumerate(stages):
        y = len(stages) - 1 - i
        ax.barh(y, v, color=TEAL if i in (0, 5) else NAVY, height=0.62)
        ax.text(v + 0.2, y, str(v), va="center", fontweight="bold", color=NAVY)
        if i < 5 and stages[i][1] != stages[i+1][1]:
            ax.text(12.9, y - 0.5, "↓ " + leaks[i], va="center", fontsize=7.6, color=RED)
    ax.set_yticks(range(len(stages))); ax.set_yticklabels([s[0] for s in stages][::-1])
    ax.set_xlim(0, 12.5); ax.set_xticks([]); [ax.spines[s].set_visible(False) for s in ("top", "right", "bottom")]
    ax.set_title("Where 12 paid renewals (1-3 Nov) were at 4 Nov, 09:00", loc="left", fontweight="bold", color=NAVY)
    fig.subplots_adjust(left=0.27, right=0.99, top=0.9, bottom=0.04)
    fig.savefig(OUT + "funnel.png", dpi=200); plt.close(fig)

# ---------- 2. as-is vs to-be ----------
def box(ax, x, y, w, h, text, fc, tc="white", fs=7.6, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012", fc=fc, ec="none"))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", color=tc, fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.25)
def arr(ax, x1, y1, x2, y2, c=NAVY):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, color=c, lw=1.2))

def flow():
    fig, ax = plt.subplots(figsize=(8.6, 6.0)); ax.set_xlim(0, 1); ax.set_ylim(-0.08, 1); ax.axis("off")
    ax.text(0, 0.99, "AS-IS: 3 manual hand-offs, no clock, no owner", fontweight="bold", color=RED, fontsize=9.5, va="top")
    w = 0.152; xs = [i * 0.1696 for i in range(6)]; y = 0.78; h = 0.14
    labels = [("1 Teacher pitches,\nparent pays\n(invoices)", GREY), ("2 Teacher fills\nform  MANUAL\n(faculty_form)", RED), ("3 Ops verifies\n& approves\nMANUAL", RED),
              ("booking_\nrequests", GREY), ("4 Parent / Ops\npicks batch\nMANUAL", RED), ("Classes\nscheduled", GREEN)]
    for x, (t, c) in zip(xs, labels): box(ax, x, y, w, h, t, c, fs=7)
    for i in range(5): arr(ax, xs[i] + w + 0.002, y + h/2, xs[i+1] - 0.002, y + h/2)
    for x, t in ((xs[1], "orphans · typos\nduplicates"), (xs[2], "queue, no SLA\nweekend gaps"), (xs[4], "false 'batch full'\nbatch change: no owner")):
        ax.text(x + w/2, y - 0.03, t, ha="center", va="top", fontsize=6.8, color=RED)
    ax.plot([0, 1], [0.56, 0.56], color=GREY, lw=0.6, ls="--")
    ax.text(0, 0.535, "TO-BE: intent captured BEFORE payment, rules engine decides, humans handle exceptions only", fontweight="bold", color=GREEN, fontsize=9, va="top")
    ty = 0.30
    box(ax, 0.0, ty, 0.19, 0.14, "0 Teacher taps\n'Send renewal link'\n(batch, plan, discount\ncode pre-filled)", TEAL, fs=7)
    box(ax, 0.225, ty, 0.12, 0.14, "Parent pays\n(Razorpay /\nStripe)", GREY, fs=7)
    box(ax, 0.38, ty, 0.18, 0.14, "Webhook →\nRULES ENGINE\nprice · identity · seat\ndiscount · intent", NAVY, bold=True, fs=6.8)
    arr(ax, 0.192, ty + 0.07, 0.223, ty + 0.07); arr(ax, 0.347, ty + 0.07, 0.378, ty + 0.07)
    outs = [(0.42, GREEN, "AUTO-APPROVE (~67% in sample)\nbooking + schedule rows written,\nWhatsApp confirm to parent & teacher"),
            (0.28, AMBER, "ONE-TAP PARENT CONFIRM (~8%)\npayer differs from registered contact"),
            (0.14, RED, "EXCEPTION → ONE named owner (~25%)\nSlack card + SLA timer + evidence\n(discount · partial · failed · new batch)")]
    for yy, c, t in outs:
        box(ax, 0.63, yy - 0.055, 0.37, 0.11, t, c, tc="white" if c != AMBER else NAVY, fs=6.8)
        arr(ax, 0.562, ty + 0.07, 0.628, yy, c=c)
    ax.text(0, 0.02, "Every decision logs rule_version, evidence and timestamps → event log → Metabase dashboard. Kill-switch reverts to manual.", fontsize=6.8, color=NAVY)
    ax.text(0, -0.03, "Shadow mode first: the engine writes to staging only until it matches Ops decisions for 2 weeks.", fontsize=6.8, color=NAVY)
    fig.savefig(OUT + "flow.png", dpi=200, bbox_inches="tight"); plt.close(fig)

# ---------- 3. dashboard ----------
def dashboard():
    fig = plt.figure(figsize=(10.2, 7.0), facecolor="white")
    fig.text(0.02, 0.965, "Renewals Control Tower - Head of Operations, daily 9:00 view", fontsize=13, fontweight="bold", color=NAVY, va="top")
    fig.text(0.02, 0.93, f"Data: provided sample (1-3 Nov) · as of {M['as_of'][:16]} · illustrative layout built from the prototype's real output", fontsize=8, color=GREY, va="top")
    tiles = [("Paid, not scheduled", f"{M['paid_or_partial'] - M['e2e_scheduled']}", f"of {M['paid_or_partial']} paid", RED),
             ("Stuck > 12h", f"{M['stuck_over_12h']}", "target 0 unowned", RED),
             ("Oldest waiting", f"{M['stuck_table'][0]['hours_since_payment']:.0f} h", f"invoice {M['stuck_table'][0]['invoice_id']}", RED),
             ("Revenue waiting", inr(M['revenue_not_scheduled_inr']), "paid, class not booked", AMBER),
             ("Orphaned invoices", f"{len(M['orphaned_invoice_ids'])}", f"{M['orphaned_invoice_rate']:.0%} of paid", AMBER),
             ("Unapproved forms", f"{M['forms_pending']}", f"oldest {M['forms_pending_oldest_h']:.0f} h", AMBER)]
    for i, (t, v, s, c) in enumerate(tiles):
        ax = fig.add_axes([0.02 + i * 0.1635, 0.76, 0.152, 0.14]); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.06", fc=LIGHT, ec="none", transform=ax.transAxes))
        ax.add_patch(FancyBboxPatch((0, 0), 0.035, 1, boxstyle="square,pad=0", fc=c, ec="none", transform=ax.transAxes))
        ax.text(0.1, 0.8, t, fontsize=7.6, color=GREY, transform=ax.transAxes, va="center")
        ax.text(0.1, 0.46, v, fontsize=15, fontweight="bold", color=NAVY, transform=ax.transAxes, va="center")
        ax.text(0.1, 0.13, s, fontsize=7, color=c, transform=ax.transAxes, va="center")
    # funnel
    f = M["funnel"]; names = ["Paid", "Form linked", "Approved", "Booking req.", "Allocated", "Scheduled"]
    vals = [f["invoices_paid"], f["form_submitted_exact_link"], f["form_approved"], f["booking_request_created"], f["batch_allocated"], f["scheduled"]]
    ax = fig.add_axes([0.095, 0.47, 0.27, 0.22])
    ax.barh(range(6)[::-1], vals, color=[TEAL] + [NAVY] * 4 + [GREEN], height=0.6)
    for y, v in zip(range(6)[::-1], vals): ax.text(v + 0.2, y, v, va="center", fontsize=8, fontweight="bold")
    ax.set_yticks(range(6)[::-1]); ax.set_yticklabels(names, fontsize=8); ax.set_xticks([]); ax.set_xlim(0, 13.5)
    [ax.spines[s].set_visible(False) for s in ("top", "right", "bottom")]; ax.set_title("Pipeline funnel (live)", loc="left", fontsize=9, fontweight="bold", color=NAVY)
    # aging
    hrs = [r["hours_since_payment"] for r in M["stuck_table"]]
    b = [sum(1 for h in hrs if h < 12), sum(1 for h in hrs if 12 <= h < 24), sum(1 for h in hrs if 24 <= h < 48), sum(1 for h in hrs if h >= 48)]
    ax = fig.add_axes([0.47, 0.47, 0.2, 0.22])
    ax.bar(["<12h", "12-24h", "24-48h", ">48h"], b, color=[GREEN, AMBER, RED, RED], width=0.6)
    for i, v in enumerate(b): ax.text(i, v + 0.15, v, ha="center", fontsize=8, fontweight="bold")
    ax.set_yticks([]); [ax.spines[s].set_visible(False) for s in ("top", "right", "left")]; ax.tick_params(labelsize=8)
    ax.set_title("Aging of paid-not-scheduled", loc="left", fontsize=9, fontweight="bold", color=NAVY)
    # hours saved
    ax = fig.add_axes([0.73, 0.47, 0.25, 0.22]); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.05", fc=LIGHT, ec="none", transform=ax.transAxes))
    ax.text(0.06, 0.88, "Ops hours saved / week", fontsize=8.5, fontweight="bold", color=NAVY, transform=ax.transAxes)
    ax.text(0.06, 0.55, "≈ 108 h", fontsize=19, fontweight="bold", color=GREEN, transform=ax.transAxes)
    ax.text(0.06, 0.30, "MODELLED at 400 renewals/wk\n(replaced by measured value\nafter the Day-30 time study)", fontsize=7, color=GREY, transform=ax.transAxes, va="center")
    # exception queue table
    ax = fig.add_axes([0.02, 0.05, 0.96, 0.37]); ax.axis("off")
    ax.text(0, 1.0, "Exception queue - one owner per card, SLA timer running", fontsize=9, fontweight="bold", color=NAVY, va="top")
    cols = ["Invoice", "Prio", "Reason code(s)", "Owner", "₹ paid", "Hrs since pay", "SLA", "Next action (auto-drafted)"]
    cx = [0.0, 0.065, 0.115, 0.385, 0.53, 0.605, 0.70, 0.745]
    for x, c in zip(cx, cols): ax.text(x, 0.88, c, fontsize=7.4, fontweight="bold", color=GREY, va="top")
    acts = {"84906": "WhatsApp parent: same batch?", "84910": "WhatsApp parent: same batch?", "84904": "Confirm payer via registered no.",
            "84907": "Approve/reject 20% discount", "84909": "Decide pro-rata vs hold; fix form", "84911": "Poll gateway; send fresh link", "84912": "Offer 2-3 slots to parent"}
    pc = {"P1": RED, "P2": AMBER, "P3": GREEN}
    rows = sorted(EXC, key=lambda r: (r["priority"], -float(r["hours_since_payment"])))
    for i, r in enumerate(rows):
        y = 0.78 - i * 0.105
        ax.add_patch(FancyBboxPatch((0, y - 0.045), 1, 0.09, boxstyle="round,pad=0,rounding_size=0.01", fc=LIGHT if i % 2 == 0 else "white", ec="none"))
        vals = [r["invoice_id"], r["priority"], r["reason_codes"].replace("|", " + "), r["owner"].split(";")[0], inr(float(r["amount_inr"])), f"{float(r['hours_since_payment']):.0f} h", f"{r['sla_hours']} h", acts.get(r["invoice_id"], "")]
        for x, v, j in zip(cx, vals, range(8)):
            ax.text(x + 0.004, y, v, fontsize=7.2, va="center", color=pc[r["priority"]] if j == 1 else NAVY, fontweight="bold" if j == 1 else "normal")
    fig.savefig(OUT + "dashboard.png", dpi=200); plt.close(fig)

# ---------- 4. savings ----------
def savings():
    asis = {"Teacher fills form": 4.0, "Ops verify + approve": 6.0, "Ops scheduling": 2.5, "Chasing / exceptions": 7.5}
    tobe = {"Teacher adds intent to link": 0.5, "Ops: soft verify (8%)": 0.25, "Ops: human decisions (25%)": 3.0}
    fig, ax = plt.subplots(figsize=(7.6, 2.5))
    cols = [NAVY, RED, AMBER, GREY]; left = 0
    for (k, v), c in zip(asis.items(), cols):
        ax.barh(1, v, left=left, color=c, height=0.5); ax.text(left + v/2, 1, f"{v:g}", ha="center", va="center", color="white", fontsize=8); left += v
    ax.text(left + 0.3, 1, f"{left:g} min / renewal", va="center", fontweight="bold", color=NAVY)
    left2 = 0
    for (k, v), c in zip(tobe.items(), [TEAL, AMBER, GREEN]):
        ax.barh(0, v, left=left2, color=c, height=0.5); left2 += v
    ax.text(left2 + 0.3, 0, f"{left2:g} min / renewal", va="center", fontweight="bold", color=GREEN)
    ax.set_yticks([0, 1]); ax.set_yticklabels(["To-be (base)", "As-is"]); ax.set_xlim(0, 24); ax.set_xticks([])
    [ax.spines[s].set_visible(False) for s in ("top", "right", "bottom")]
    ax.legend([plt.Rectangle((0,0),1,1,color=c) for c in cols], list(asis), ncol=4, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.28), frameon=False)
    fig.subplots_adjust(left=0.14, right=0.98, top=0.8, bottom=0.05); fig.savefig(OUT + "savings.png", dpi=200); plt.close(fig)

if __name__ == "__main__":
    funnel(); flow(); dashboard(); savings(); print("figures ok")
