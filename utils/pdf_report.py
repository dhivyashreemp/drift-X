from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime


# ── Colour palette ────────────────────────────────────────────────────────────
C_NAVY      = colors.HexColor("#1e293b")
C_INDIGO    = colors.HexColor("#4f46e5")
C_INDIGO_LT = colors.HexColor("#e0e7ff")
C_GREEN     = colors.HexColor("#16a34a")
C_GREEN_LT  = colors.HexColor("#dcfce7")
C_AMBER     = colors.HexColor("#d97706")
C_AMBER_LT  = colors.HexColor("#fef3c7")
C_RED       = colors.HexColor("#dc2626")
C_RED_LT    = colors.HexColor("#fee2e2")
C_BLUE_LT   = colors.HexColor("#eff6ff")
C_SLATE     = colors.HexColor("#64748b")
C_LIGHT     = colors.HexColor("#f8fafc")
C_BORDER    = colors.HexColor("#e2e8f0")
PAGE_W      = A4[0] - 4 * cm   # usable width


def _safe(text, max_len=1200):
    if not text:
        return ""
    t = str(text)
    # Replace Unicode chars that Helvetica cannot render (would show as ■)
    _REPLACEMENTS = [
        ("—", "--"),   # em dash  —
        ("–", "-"),    # en dash  –
        ("‒", "-"),    # figure dash
        ("‑", "-"),    # non-breaking hyphen
        ("‐", "-"),    # hyphen
        ("―", "--"),   # horizontal bar
        ("’", "'"),    # right single quote '
        ("‘", "'"),    # left single quote '
        ("“", '"'),    # left double quote "
        ("”", '"'),    # right double quote "
        ("…", "..."),  # ellipsis …
        ("·", "-"),    # middle dot
        ("•", "-"),    # bullet •
        (" ", " "),    # non-breaking space
        ("→", "->"),   # arrow →
        ("←", "<-"),   # left arrow ←
        ("×", "x"),    # multiplication sign ×
        ("é", "e"),    # é
        ("à", "a"),    # à
        ("❤", "<3"),   # heart
    ]
    for src, dst in _REPLACEMENTS:
        t = t.replace(src, dst)
    # Strip any remaining non-Latin-1 chars (keeps ReportLab happy)
    t = t.encode("latin-1", errors="replace").decode("latin-1")
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t[:max_len]


_TYPE_LABEL_MAP = {
    "security vulnerability": "Security Risk",
    "security": "Security Risk",
    "requirement drift": "Requirement Mismatch",
    "drift": "Requirement Mismatch",
    "feature completeness": "Incomplete Feature",
    "completeness": "Incomplete Feature",
    "guideline violation": "Best Practice Violation",
    "guideline": "Best Practice Violation",
    "code quality": "Code Quality Issue",
    "error handling": "Error Handling Gap",
    "testing gap": "Missing Tests",
    "testing": "Missing Tests",
    "critical feature loss": "Critical Feature Removed",
    "feature loss": "Feature Removed",
}


def _friendly_type(raw_type: str) -> str:
    key = raw_type.lower().strip()
    for k, v in _TYPE_LABEL_MAP.items():
        if k in key:
            return v
    return raw_type


def _score_color(score):
    if score >= 80:
        return C_GREEN, C_GREEN_LT, "PASSED"
    if score >= 60:
        return C_AMBER, C_AMBER_LT, "WARNING"
    return C_RED, C_RED_LT, "FAILED"


# ── Score bar flowable ────────────────────────────────────────────────────────
class ScoreBar(Flowable):
    def __init__(self, score, width=PAGE_W, height=14):
        super().__init__()
        self.score = min(100, max(0, float(score)))
        self.width = width
        self.height = height

    def draw(self):
        w, h, s = self.width, self.height, self.score
        # Background track
        self.canv.setFillColor(C_BORDER)
        self.canv.roundRect(0, 0, w, h, 4, fill=1, stroke=0)
        # Filled portion — gradient-like via zones
        fill_w = w * s / 100
        if fill_w > 0:
            if s < 60:
                self.canv.setFillColor(C_RED)
            elif s < 80:
                self.canv.setFillColor(C_AMBER)
            else:
                self.canv.setFillColor(C_GREEN)
            self.canv.roundRect(0, 0, fill_w, h, 4, fill=1, stroke=0)
        # Threshold markers
        for pct, label in [(60, "60"), (80, "80")]:
            x = w * pct / 100
            self.canv.setStrokeColor(colors.white)
            self.canv.setLineWidth(1.5)
            self.canv.line(x, 0, x, h)
        # Score label inside bar
        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 8)
        self.canv.drawString(6, 3, f"{s:.0f} / 100")


# ── Styles factory ────────────────────────────────────────────────────────────
def _make_styles():
    base = getSampleStyleSheet()
    def s(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    return {
        "title":    s("T", "Heading1", fontSize=22, textColor=colors.white,
                       fontName="Helvetica-Bold", spaceAfter=2),
        "subtitle": s("ST", fontSize=10, textColor=colors.HexColor("#cbd5e1"),
                       fontName="Helvetica"),
        "h2":       s("H2", "Heading2", fontSize=14, spaceBefore=16, spaceAfter=6,
                       textColor=C_NAVY, fontName="Helvetica-Bold",
                       borderPad=4, borderColor=C_BORDER),
        "h3":       s("H3", "Heading3", fontSize=11, spaceBefore=10, spaceAfter=4,
                       textColor=C_INDIGO, fontName="Helvetica-Bold"),
        "body":     s("B", fontSize=11, textColor=C_NAVY, leading=16),
        "small":    s("Sm", fontSize=9, textColor=C_SLATE, leading=13),
        "code":     s("Co", fontSize=9, fontName="Courier",
                       backColor=colors.HexColor("#f1f5f9"),
                       leftIndent=8, rightIndent=8, leading=13),
        "bold":     s("Bd", fontSize=11, fontName="Helvetica-Bold", textColor=C_NAVY),
        "center":   s("Ctr", fontSize=10, alignment=TA_CENTER, textColor=C_SLATE),
        "tag_red":  s("TR", fontSize=9, fontName="Helvetica-Bold",
                       textColor=C_RED, alignment=TA_CENTER),
        "tag_grn":  s("TG", fontSize=9, fontName="Helvetica-Bold",
                       textColor=C_GREEN, alignment=TA_CENTER),
        "tag_amb":  s("TA", fontSize=9, fontName="Helvetica-Bold",
                       textColor=C_AMBER, alignment=TA_CENTER),
        "remediation": s("Rem", fontSize=10, textColor=colors.HexColor("#1e40af"),
                          backColor=C_BLUE_LT, leftIndent=10, rightIndent=10,
                          spaceBefore=4, leading=15),
    }


# ── Section header ────────────────────────────────────────────────────────────
def _section(title, styles, icon=""):
    elems = []
    elems.append(Spacer(1, 0.3 * cm))
    elems.append(Paragraph(f"{icon}  {title}" if icon else title, styles["h2"]))
    elems.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=4))
    return elems


# ── Issue card ────────────────────────────────────────────────────────────────
_LABEL_W = 3.5 * cm

def _issue_card(idx, issue, styles):
    raw_type = issue.get("type", "Issue")
    itype  = _friendly_type(_safe(raw_type, 80))
    desc   = _safe(issue.get("description", ""), 800)
    ev     = _safe(issue.get("evidence", ""), 600)
    reason = _safe(issue.get("reasoning", ""), 800)
    remed  = _safe(issue.get("remediation", ""), 1000)

    is_security = "security" in raw_type.lower()
    critical = is_security or any(w in raw_type.lower() for w in
                   ["loss", "drift", "violation", "missing", "failed", "error handling", "testing"])
    bg   = colors.HexColor("#fff1f2") if is_security else (C_RED_LT if critical else C_AMBER_LT)
    tag  = colors.HexColor("#be123c") if is_security else (C_RED if critical else C_AMBER)
    icon = "🔒" if is_security else ("🚨" if critical else "⚠")

    rows = [
        [
            Paragraph(f"{icon} #{idx}", styles["bold"]),
            Paragraph(f"<b>{itype}</b>", styles["bold"]),
        ],
        [
            Paragraph("What happened", styles["small"]),
            Paragraph(desc, styles["body"]),
        ],
    ]
    if ev:
        rows.append([
            Paragraph("Where in code", styles["small"]),
            Paragraph(ev, styles["code"]),
        ])
    if reason:
        rows.append([
            Paragraph("Why it matters", styles["small"]),
            Paragraph(reason, styles["body"]),
        ])
    if remed:
        rows.append([
            Paragraph("Recommended Fix", styles["small"]),
            Paragraph(remed, styles["remediation"]),
        ])

    t = Table(rows, colWidths=[_LABEL_W, PAGE_W - _LABEL_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), bg),
        ("BACKGROUND",   (0, 1), (-1, -1), C_LIGHT),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LINEABOVE",    (0, 0), (-1, 0), 2.5, tag),
    ]))
    return KeepTogether([t, Spacer(1, 0.25 * cm)])


# ── Page number callback ──────────────────────────────────────────────────────
def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_SLATE)
    page_num = canvas.getPageNumber()
    canvas.drawRightString(A4[0] - 2 * cm, 0.7 * cm, f"Page {page_num}")
    canvas.drawString(2 * cm, 0.7 * cm, "Drift-X — Confidential Quality Report")
    canvas.restoreState()


# ── Main generator ────────────────────────────────────────────────────────────
def generate_pdf_report(results, history_results=None, module_results=None,
                        repo_url="", branch="", module_name=""):

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title="Drift-X Analysis Report",
    )
    st = _make_styles()
    story = []

    score = 0.0
    try:
        score = max(0.0, min(100.0, float(results.get("score", 0))))
    except Exception:
        pass

    score_clr, score_bg, verdict = _score_color(score)
    issues = results.get("issues", [])
    critical_issues = [i for i in issues if any(
        w in i.get("type", "").lower() for w in
        ["loss", "drift", "violation", "missing", "failed", "security", "error handling", "testing"]
    )]
    feature_changes = (history_results or {}).get("feature_changes", [])
    losses = [c for c in feature_changes if "loss" in c.get("status", "").lower()]

    # ── Cover header band ────────────────────────────────────────────────────
    header_rows = [[
        Paragraph("🛡 Drift-X", st["title"]),
        Paragraph("Unified Quality Analysis Report", st["subtitle"]),
    ]]
    header_t = Table(header_rows, colWidths=[5 * cm, PAGE_W - 5 * cm])
    header_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [6, 6, 0, 0]),
    ]))
    story.append(header_t)

    # ── Meta row ─────────────────────────────────────────────────────────────
    repo_display = _safe(repo_url, 80).replace("https://github.com/", "")
    meta_cells = [f"📁 {repo_display}"]
    if branch:
        meta_cells.append(f"🌿 {_safe(branch)}")
    if module_name:
        meta_cells.append(f"🔍 {_safe(module_name)}")
    meta_cells.append(f"🕐 {datetime.now().strftime('%Y-%m-%d  %H:%M')}")

    meta_row = [[Paragraph(c, st["small"]) for c in meta_cells]]
    col_w = PAGE_W / len(meta_cells)
    meta_t = Table(meta_row, colWidths=[col_w] * len(meta_cells))
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#334155")),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
        ("LINEBELOW",     (0, 0), (-1, -1), 3, C_INDIGO),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 0.5 * cm))

    # ── Score card ────────────────────────────────────────────────────────────
    score_label = Paragraph(
        f'<font size="40" color="{score_clr.hexval()}"><b>{score:.0f}</b></font>'
        f'<font size="18" color="{C_SLATE.hexval()}"> / 100</font>',
        ParagraphStyle("SL", alignment=TA_CENTER, leading=52, spaceBefore=4, spaceAfter=4)
    )
    verdict_label = Paragraph(
        f'<font size="20" color="{score_clr.hexval()}"><b>{verdict}</b></font>',
        ParagraphStyle("VL", alignment=TA_CENTER, leading=28, spaceBefore=2, spaceAfter=2)
    )
    threshold_note = Paragraph("Pass threshold: 80 / 100", st["center"])

    score_card = Table(
        [[score_label],
         [verdict_label],
         [Spacer(1, 0.3 * cm)],
         [ScoreBar(score, PAGE_W - 1.6 * cm)],
         [Spacer(1, 0.15 * cm)],
         [threshold_note]],
        colWidths=[PAGE_W]
    )
    score_card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), score_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 1.5, score_clr),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [6, 6, 6, 6]),
    ]))
    story.append(score_card)
    story.append(Spacer(1, 0.4 * cm))

    # ── Stats bar ─────────────────────────────────────────────────────────────
    risk = (history_results or {}).get("deployment_risk", "Unknown")
    risk_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "⚪")

    stats = [
        ("Total Issues",    str(len(issues)),          C_INDIGO),
        ("Critical Issues", str(len(critical_issues)), C_RED if critical_issues else C_GREEN),
        ("Feature Losses",  str(len(losses)),           C_RED if losses else C_GREEN),
        ("Deploy Risk",     f"{risk_icon} {risk}",      C_SLATE),
    ]
    stat_cells = []
    for label, val, clr in stats:
        stat_cells.append(
            Paragraph(
                f'<font size="18" color="{clr.hexval()}"><b>{val}</b></font>'
                f'<br/><font size="8" color="{C_SLATE.hexval()}">{label}</font>',
                ParagraphStyle("SC", alignment=TA_CENTER, leading=22)
            )
        )
    stats_t = Table([stat_cells], colWidths=[PAGE_W / 4] * 4)
    stats_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(stats_t)
    story.append(Spacer(1, 0.4 * cm))

    # ── Executive summary table ───────────────────────────────────────────────
    story.extend(_section("Executive Summary", st, "📋"))

    security_issues = [i for i in issues if "security" in i.get("type", "").lower()]
    testing_gaps    = [i for i in issues if "testing" in i.get("type", "").lower()]
    eh_gaps         = [i for i in issues if "error" in i.get("type", "").lower()]

    exec_rows = [
        ["Overall Score", f"{score:.0f} / 100  —  {verdict}"],
        ["Total Issues Found", str(len(issues))],
        ["Critical Issues", str(len(critical_issues))],
        ["Security Risks", str(len(security_issues))],
        ["Error Handling Gaps", str(len(eh_gaps))],
        ["Testing Gaps", str(len(testing_gaps))],
        ["Feature Losses", str(len(losses))],
        ["Repository", _safe(repo_url, 100).replace("https://github.com/", "github.com/")],
        ["Branch / Version", _safe(branch, 60) if branch else "default"],
        ["Analysis Date", datetime.now().strftime("%d %B %Y, %H:%M")],
    ]
    exec_t = Table(
        [[Paragraph(r[0], st["bold"]), Paragraph(r[1], st["body"])] for r in exec_rows],
        colWidths=[4.5 * cm, PAGE_W - 4.5 * cm]
    )
    exec_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [C_LIGHT, colors.white]),
        ("GRID",           (0, 0), (-1, -1), 0.4, C_BORDER),
        ("LEFTPADDING",    (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 10),
        ("TOPPADDING",     (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
        ("TEXTCOLOR",      (0, 0), (0, -1), C_SLATE),
    ]))
    story.append(exec_t)
    story.append(Spacer(1, 0.4 * cm))

    summary_text = _safe(results.get("summary", "No summary available."), 2000)
    story.append(Paragraph("<b>Analysis Overview</b>", st["bold"]))
    story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(summary_text, st["body"]))

    # ── Gate decision banner ──────────────────────────────────────────────────
    story.append(Spacer(1, 0.3 * cm))
    if score >= 80:
        gate_text = "QUALITY GATE PASSED  --  Code is ready for deployment."
        gate_bg, gate_clr = C_GREEN_LT, C_GREEN
    elif score >= 60:
        gate_text = "QUALITY GATE WARNING  --  Improvements recommended before deployment."
        gate_bg, gate_clr = C_AMBER_LT, C_AMBER
    else:
        gate_text = "QUALITY GATE FAILED  --  Critical fixes required before deployment."
        gate_bg, gate_clr = C_RED_LT, C_RED

    gate_t = Table(
        [[Paragraph(gate_text, ParagraphStyle(
            "GT", fontSize=10, fontName="Helvetica-Bold",
            textColor=gate_clr, alignment=TA_CENTER
        ))]],
        colWidths=[PAGE_W]
    )
    gate_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), gate_bg),
        ("BOX",           (0, 0), (-1, -1), 1.5, gate_clr),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(gate_t)
    story.append(Spacer(1, 0.3 * cm))

    # ── Issues ────────────────────────────────────────────────────────────────
    if issues:
        story.append(PageBreak())
        story.extend(_section(f"Issues Found  —  {len(issues)} total, {len(critical_issues)} critical", st, "🚨"))

        # Summary table with friendly labels
        type_counts = {}
        for iss in issues:
            label = _friendly_type(iss.get("type", "Other"))
            type_counts[label] = type_counts.get(label, 0) + 1
        if type_counts:
            tc_data = [["Category", "Count"]] + [[_safe(k, 80), str(v)] for k, v in type_counts.items()]
            tc_t = Table(tc_data, colWidths=[PAGE_W - 3 * cm, 3 * cm])
            tc_t.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), C_NAVY),
                ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",     (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, colors.white]),
                ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ]))
            story.append(tc_t)
            story.append(Spacer(1, 0.4 * cm))

        # Critical first
        sorted_issues = sorted(
            enumerate(issues, 1),
            key=lambda x: 0 if any(w in x[1].get("type", "").lower()
                                   for w in ["loss", "drift", "violation", "missing", "failed"]) else 1
        )
        for idx, issue in sorted_issues:
            story.append(_issue_card(idx, issue, st))

    else:
        story.extend(_section("Issues", st, "✅"))
        story.append(Paragraph("No issues found. Code is fully compliant.", st["body"]))

    # ── Feature Evolution ─────────────────────────────────────────────────────
    if history_results and "error" not in history_results:
        story.append(PageBreak())
        story.extend(_section("Feature Evolution", st, "🧬"))

        meta      = history_results.get("analysis_metadata", {})
        base_h    = str(meta.get("base_commit", "—"))[:8]
        head_h    = str(meta.get("head_commit", "—"))[:8]
        evo_sum   = _safe(history_results.get("summary", ""), 800)
        n_changes = len(feature_changes)
        n_losses  = len(losses)
        n_replace = len([c for c in feature_changes if "replacement" in c.get("status", "").lower()])

        evo_stats = Table(
            [[Paragraph(f"<b>{n_changes}</b><br/>Total Changes", st["center"]),
              Paragraph(f"<b>{n_losses}</b><br/>Feature Losses", st["center"]),
              Paragraph(f"<b>{n_replace}</b><br/>Replacements", st["center"]),
              Paragraph(f"<b>{base_h} → {head_h}</b><br/>Commit Range", st["center"])]],
            colWidths=[PAGE_W / 4] * 4
        )
        evo_stats.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("TEXTCOLOR",     (0, 1), (0, 1), C_RED if n_losses else C_GREEN),
        ]))
        story.append(evo_stats)
        story.append(Spacer(1, 0.3 * cm))

        if evo_sum:
            story.append(Paragraph(evo_sum, st["body"]))
            story.append(Spacer(1, 0.3 * cm))

        for change in feature_changes:
            fname   = _safe(change.get("feature_name", "Unknown Feature"), 120)
            status  = change.get("status", "")
            sev     = change.get("severity", "Medium")
            impact  = _safe(change.get("impact", ""), 600)
            rep     = _safe(change.get("replacement_logic", ""), 600)
            remed   = _safe(change.get("remediation", ""), 800)
            is_loss = "loss" in status.lower() or "missing" in status.lower()

            sev_clr = {"Critical": C_RED, "High": C_AMBER, "Medium": C_SLATE, "Low": C_GREEN}.get(sev, C_SLATE)
            bg = C_RED_LT if is_loss else C_GREEN_LT
            icon = "❌" if is_loss else "🔄"

            rows = [[
                Paragraph(f"{icon} <b>{fname}</b>", st["bold"]),
                Paragraph(
                    f'Status: <b>{status}</b>  |  '
                    f'Severity: <font color="{sev_clr.hexval()}"><b>{sev}</b></font>',
                    st["body"]
                ),
            ]]
            if impact:
                rows.append([Paragraph("Impact", st["small"]), Paragraph(impact, st["body"])])
            if rep:
                rows.append([Paragraph("Replacement", st["small"]), Paragraph(rep, st["body"])])
            if remed:
                rows.append([Paragraph("Recommended Fix", st["small"]), Paragraph(remed, st["remediation"])])

            ct = Table(rows, colWidths=[_LABEL_W, PAGE_W - _LABEL_W])
            ct.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), bg),
                ("BACKGROUND",   (0, 1), (-1, -1), C_LIGHT),
                ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("LINEABOVE",    (0, 0), (-1, 0), 2, C_RED if is_loss else C_GREEN),
            ]))
            story.append(KeepTogether([ct, Spacer(1, 0.2 * cm)]))

    # ── Module Analysis ───────────────────────────────────────────────────────
    if module_results:
        story.append(PageBreak())
        mod_name = _safe(module_results.get("module_name", ""), 60)
        story.extend(_section(f"Module Analysis: {mod_name}", st, "🔍"))

        analysis  = module_results.get("analysis", {})
        mod_score = analysis.get("compliance_score")
        ms_clr, ms_bg, ms_verdict, ms_icon = _score_color(float(mod_score or 0))

        mod_stats = Table([[
            Paragraph(f"<b>{module_results.get('file_count', 0)}</b><br/>Module Files", st["center"]),
            Paragraph(f"<b>{module_results.get('usage_count', 0)}</b><br/>Referenced In", st["center"]),
            Paragraph(
                f'<font color="{ms_clr.hexval()}"><b>{mod_score if mod_score is not None else "N/A"}</b></font>'
                f'<br/>Module Score',
                st["center"]
            ),
        ]], colWidths=[PAGE_W / 3] * 3)
        mod_stats.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(mod_stats)
        story.append(Spacer(1, 0.3 * cm))

        if analysis.get("module_purpose"):
            story.append(Paragraph("<b>Purpose:</b>", st["bold"]))
            story.append(Paragraph(_safe(analysis["module_purpose"], 600), st["body"]))
            story.append(Spacer(1, 0.2 * cm))

        if analysis.get("key_components"):
            story.append(Paragraph("<b>Key Components:</b>", st["bold"]))
            for comp in analysis["key_components"][:10]:
                story.append(Paragraph(f"• {_safe(comp, 120)}", st["body"]))
            story.append(Spacer(1, 0.2 * cm))

        related = module_results.get("related_files", [])
        if related:
            story.append(Paragraph(f"<b>Module Files ({len(related)}):</b>", st["bold"]))
            for f in related[:20]:
                story.append(Paragraph(f"• {_safe(f, 120)}", st["code"]))
            story.append(Spacer(1, 0.2 * cm))

        mod_issues = analysis.get("issues", [])
        if mod_issues:
            story.append(Paragraph(f"<b>Module Issues ({len(mod_issues)}):</b>", st["bold"]))
            story.append(Spacer(1, 0.1 * cm))
            for idx, issue in enumerate(mod_issues[:15], 1):
                story.append(_issue_card(idx, issue, st))

    # ── Recommendations summary ───────────────────────────────────────────────
    critical_list = [i for i in issues if any(
        w in i.get("type", "").lower() for w in
        ["loss", "drift", "violation", "missing", "failed", "security", "error handling", "testing"]
    )]
    if critical_list:
        story.append(PageBreak())
        story.extend(_section("Top Recommendations", st, "🎯"))
        story.append(Paragraph(
            "Fix these issues first — they have the highest impact on quality and security:",
            st["body"]
        ))
        story.append(Spacer(1, 0.3 * cm))

        for rank, issue in enumerate(critical_list[:5], 1):
            remed = _safe(issue.get("remediation", "No remediation provided."), 1000)
            itype = _friendly_type(_safe(issue.get("type", ""), 60))
            desc  = _safe(issue.get("description", ""), 300)

            rec_rows = [
                [Paragraph(f"#{rank}", ParagraphStyle("RN", fontSize=14, fontName="Helvetica-Bold",
                                                       textColor=C_INDIGO, alignment=TA_CENTER)),
                 Paragraph(f"<b>{itype}:</b> {desc}", st["body"])],
                [Paragraph("What to do", st["small"]),
                 Paragraph(remed, st["remediation"])],
            ]
            rec_t = Table(rec_rows, colWidths=[1.2 * cm, PAGE_W - 1.2 * cm])
            rec_t.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), C_INDIGO_LT),
                ("BACKGROUND",   (0, 1), (-1, 1), C_LIGHT),
                ("GRID",         (0, 0), (-1, -1), 0.4, C_BORDER),
                ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
                ("LINEABOVE",    (0, 0), (-1, 0), 2, C_INDIGO),
            ]))
            story.append(KeepTogether([rec_t, Spacer(1, 0.25 * cm)]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 0.15 * cm))

    footer_t = Table([[
        Paragraph("🛡 Drift-X — AI-Powered Compliance Gateway", st["small"]),
        Paragraph(datetime.now().strftime("%Y-%m-%d"), ParagraphStyle(
            "FR", fontSize=8, textColor=C_SLATE, alignment=TA_RIGHT)),
    ]], colWidths=[PAGE_W * 0.7, PAGE_W * 0.3])
    footer_t.setStyle(TableStyle([("TOPPADDING", (0,0), (-1,-1), 0),
                                   ("BOTTOMPADDING", (0,0), (-1,-1), 0)]))
    story.append(footer_t)

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buf.seek(0)
    return buf.getvalue()
