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
C_ORANGE    = colors.HexColor("#ea580c")
C_ORANGE_LT = colors.HexColor("#fff7ed")
C_PURPLE    = colors.HexColor("#7c3aed")
C_PURPLE_LT = colors.HexColor("#f5f3ff")
PAGE_W      = A4[0] - 4 * cm


def _safe(text, max_len=1200):
    if not text:
        return ""
    t = str(text)
    _REPLACEMENTS = [
        ("—", "--"), ("–", "-"), ("‒", "-"), ("‑", "-"),
        ("‐", "-"), ("―", "--"), ("’", "'"), ("‘", "'"),
        ("“", '"'), ("”", '"'), ("…", "..."), ("·", "-"),
        ("•", "-"), (" ", " "), ("→", "->"), ("←", "<-"),
        ("×", "x"), ("é", "e"), ("à", "a"),
        ("\U0001f512", "[locked]"), ("✅", "[ok]"), ("❌", "[x]"),
        ("\U0001f4cb", "[doc]"), ("\U0001f4cd", "[pin]"),
        ("⚠", "[!]"), ("\U0001f527", "[fix]"),
    ]
    for src, dst in _REPLACEMENTS:
        t = t.replace(src, dst)
    t = t.encode("latin-1", errors="replace").decode("latin-1")
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t[:max_len]


_SEV_PLAIN = {
    "Critical": "Must fix before any deployment",
    "High":     "Fix before next release",
    "Medium":   "Fix within current sprint",
    "Low":      "Fix in future sprint",
}

_CATEGORY_PLAIN = {
    "auth":           "Authentication & Access Control",
    "pipeline":       "Background Jobs & Concurrency",
    "dependencies":   "Package & Dependency Safety",
    "complexity":     "Code Complexity",
    "security":       "Security Vulnerabilities",
    "error_handling": "Error Handling",
    "observability":  "Logging & Monitoring",
    "dead_code":      "Unused / Deferred Code",
}

_TYPE_PLAIN = {
    "security vulnerability":  "Security Risk",
    "security":                "Security Risk",
    "requirement drift":       "Feature Differs from Requirements",
    "drift":                   "Feature Differs from Requirements",
    "feature completeness":    "Incomplete Feature",
    "completeness":            "Incomplete Feature",
    "guideline violation":     "Best Practice Violation",
    "guideline":               "Best Practice Violation",
    "code quality":            "Code Quality Issue",
    "error handling":          "Error Handling Gap",
    "testing gap":             "Missing Tests",
    "testing":                 "Missing Tests",
    "critical feature loss":   "Critical Feature Removed",
    "feature loss":            "Feature Removed",
    "performance issue":       "Performance Problem",
    "deployment readiness":    "Deployment Configuration Gap",
    "observability gap":       "Logging / Monitoring Gap",
    "dependency risk":         "Risky Package Dependency",
}


def _plain_type(raw: str) -> str:
    key = (raw or "").lower().strip()
    for k, v in _TYPE_PLAIN.items():
        if k in key:
            return v
    return raw or "Issue"


def _score_color(score):
    if score >= 85:
        return C_GREEN, C_GREEN_LT, "APPROVED"
    if score >= 65:
        return C_AMBER, C_AMBER_LT, "CONDITIONAL"
    return C_RED, C_RED_LT, "BLOCKED"


def _sev_color(sev):
    return {
        "Critical": (C_RED,    C_RED_LT),
        "High":     (C_ORANGE, C_ORANGE_LT),
        "Medium":   (C_AMBER,  C_AMBER_LT),
        "Low":      (C_SLATE,  C_LIGHT),
    }.get(sev, (C_SLATE, C_LIGHT))


# ── Score bar flowable ────────────────────────────────────────────────────────
class ScoreBar(Flowable):
    def __init__(self, score, width=PAGE_W, height=16):
        super().__init__()
        self.score = min(100, max(0, float(score)))
        self.width = width
        self.height = height

    def draw(self):
        w, h, s = self.width, self.height, self.score
        self.canv.setFillColor(C_BORDER)
        self.canv.roundRect(0, 0, w, h, 5, fill=1, stroke=0)
        fill_w = w * s / 100
        if fill_w > 0:
            clr = C_RED if s < 65 else (C_AMBER if s < 85 else C_GREEN)
            self.canv.setFillColor(clr)
            self.canv.roundRect(0, 0, fill_w, h, 5, fill=1, stroke=0)
        for pct, _ in [(65, ""), (85, "")]:
            x = w * pct / 100
            self.canv.setStrokeColor(colors.white)
            self.canv.setLineWidth(1.5)
            self.canv.line(x, 0, x, h)
        self.canv.setFillColor(colors.white)
        self.canv.setFont("Helvetica-Bold", 9)
        self.canv.drawString(8, 4, f"{s:.0f} / 100")


# ── Styles ────────────────────────────────────────────────────────────────────
def _make_styles():
    base = getSampleStyleSheet()
    def s(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)
    return {
        "cover_title":  s("CT", fontSize=28, fontName="Helvetica-Bold",
                           textColor=colors.white, spaceAfter=4, leading=34),
        "cover_sub":    s("CS", fontSize=13, fontName="Helvetica",
                           textColor=colors.HexColor("#94a3b8"), spaceAfter=2),
        "h2":           s("H2", "Heading2", fontSize=13, spaceBefore=14, spaceAfter=5,
                           textColor=C_NAVY, fontName="Helvetica-Bold"),
        "h3":           s("H3", "Heading3", fontSize=10, spaceBefore=8, spaceAfter=3,
                           textColor=C_INDIGO, fontName="Helvetica-Bold"),
        "body":         s("B",  fontSize=10, textColor=C_NAVY, leading=15),
        "body_plain":   s("BP", fontSize=10, textColor=colors.HexColor("#374151"), leading=15),
        "small":        s("Sm", fontSize=8,  textColor=C_SLATE, leading=12,
                           fontName="Helvetica-Bold"),
        "label":        s("Lb", fontSize=8,  textColor=C_SLATE, leading=11,
                           fontName="Helvetica-Bold"),
        "code":         s("Co", fontSize=8,  fontName="Courier",
                           backColor=colors.HexColor("#1e293b"),
                           textColor=colors.HexColor("#e2e8f0"),
                           leftIndent=8, rightIndent=8, leading=12),
        "bold":         s("Bd", fontSize=10, fontName="Helvetica-Bold", textColor=C_NAVY),
        "center":       s("Ctr", fontSize=9, alignment=TA_CENTER, textColor=C_SLATE, leading=14),
        "center_bold":  s("CtrB", fontSize=10, alignment=TA_CENTER,
                           fontName="Helvetica-Bold", textColor=C_NAVY, leading=15),
        "remediation":  s("Rem", fontSize=10, textColor=colors.HexColor("#1e40af"),
                           backColor=C_BLUE_LT, leftIndent=10, rightIndent=10,
                           spaceBefore=3, leading=14),
        "tag":          s("Tag", fontSize=8, fontName="Helvetica-Bold",
                           alignment=TA_CENTER, textColor=colors.white),
        "verdict_text": s("VT", fontSize=11, fontName="Helvetica-Bold",
                           alignment=TA_CENTER, leading=15),
        "toc_item":     s("TI", fontSize=10, textColor=C_NAVY, leading=16,
                           leftIndent=12),
        "callout":      s("Cal", fontSize=10, textColor=colors.HexColor("#92400e"),
                           backColor=colors.HexColor("#fffbeb"),
                           leftIndent=10, rightIndent=10, leading=15),
        "plain_impact": s("PI", fontSize=10, textColor=colors.HexColor("#1e40af"),
                           backColor=C_BLUE_LT, leftIndent=10, leading=14),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────
def _section(title, styles, icon="", description=""):
    elems = [Spacer(1, 0.3 * cm)]
    display = f"{icon}  {title}" if icon else title
    elems.append(Paragraph(display, styles["h2"]))
    elems.append(HRFlowable(width="100%", thickness=1.5, color=C_INDIGO, spaceAfter=4))
    if description:
        elems.append(Paragraph(description, styles["body_plain"]))
        elems.append(Spacer(1, 0.2 * cm))
    return elems


def _pill(text, fg, bg, styles):
    t = Table([[Paragraph(_safe(text, 40), ParagraphStyle(
        "P", fontSize=8, fontName="Helvetica-Bold",
        textColor=fg, alignment=TA_CENTER
    ))]], colWidths=[2.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("BOX",           (0, 0), (-1, -1), 0.5, fg),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [4, 4, 4, 4]),
    ]))
    return t


def _severity_legend(styles):
    rows = [["Severity Level", "What it means", "When to fix"]]
    defs = [
        ("CRITICAL", C_RED,    "A serious defect that blocks deployment or creates an immediate security/data risk.", "Before this deployment"),
        ("HIGH",     C_ORANGE, "A significant gap that can cause failures, data loss, or security breaches.",          "Before next release"),
        ("MEDIUM",   C_AMBER,  "An issue that degrades quality or reliability but does not block deployment.",         "Within current sprint"),
        ("LOW",      C_SLATE,  "A minor improvement — naming, comments, style — that does not affect functionality.", "In a future sprint"),
    ]
    for sev, clr, meaning, when in defs:
        rows.append([
            Paragraph(f'<font color="{clr.hexval()}"><b>{sev}</b></font>',
                      ParagraphStyle("SL", fontSize=9, fontName="Helvetica-Bold", alignment=TA_CENTER)),
            Paragraph(_safe(meaning), styles["body_plain"]),
            Paragraph(_safe(when), styles["small"]),
        ])
    t = Table(rows, colWidths=[2.2 * cm, PAGE_W - 5.2 * cm, 3.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.4, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
    ]))
    return t


# ── Issue card ────────────────────────────────────────────────────────────────
_LABEL_W = 3.2 * cm

def _issue_card(idx, issue, styles):
    raw_type = issue.get("type", "Issue")
    itype    = _plain_type(raw_type)
    sev      = issue.get("severity", "Medium")
    sev_clr, sev_bg = _sev_color(sev)
    desc     = _safe(issue.get("description", ""), 800)
    ev       = _safe(issue.get("evidence", ""), 500)
    reason   = _safe(issue.get("reasoning", ""), 600)
    remed    = _safe(issue.get("remediation", ""), 900)

    header_row = [
        Paragraph(
            f'<font color="{sev_clr.hexval()}"><b>{sev.upper()}</b></font>  '
            f'<font color="{C_SLATE.hexval()}">#{idx}</font>',
            ParagraphStyle("IH", fontSize=9, fontName="Helvetica-Bold", leading=13)
        ),
        Paragraph(f"<b>{_safe(itype, 80)}</b>", styles["bold"]),
        Paragraph(
            f'<font color="{C_SLATE.hexval()}" size="8">{_SEV_PLAIN.get(sev, "")}</font>',
            ParagraphStyle("IHR", fontSize=8, alignment=TA_RIGHT, textColor=C_SLATE, leading=12)
        ),
    ]

    rows = [header_row]
    rows.append([
        Paragraph("What's wrong", styles["label"]),
        Paragraph(desc, styles["body_plain"]),
        Paragraph("", styles["body"]),
    ])
    if ev:
        rows.append([
            Paragraph("Where in code", styles["label"]),
            Paragraph(ev, styles["code"]),
            Paragraph("", styles["body"]),
        ])
    if reason:
        rows.append([
            Paragraph("Business impact", styles["label"]),
            Paragraph(reason, styles["plain_impact"]),
            Paragraph("", styles["body"]),
        ])
    if remed:
        rows.append([
            Paragraph("Recommended Fix", styles["label"]),
            Paragraph(remed, styles["remediation"]),
            Paragraph("", styles["body"]),
        ])

    col_w = [_LABEL_W, PAGE_W - _LABEL_W - 0.1 * cm, 0.1 * cm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(TableStyle([
        ("SPAN",         (1, 0), (2, 0)),
        ("SPAN",         (1, 1), (2, 1)),
        ("SPAN",         (1, 2), (2, 2)),
        ("SPAN",         (1, 3), (2, 3)),
        ("SPAN",         (1, 4), (2, 4)),
        ("BACKGROUND",   (0, 0), (-1, 0), sev_bg),
        ("BACKGROUND",   (0, 1), (-1, -1), colors.white),
        ("BACKGROUND",   (0, 1), (0, -1), C_LIGHT),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("GRID",         (0, 0), (-1, -1), 0.3, C_BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("LINEABOVE",    (0, 0), (-1, 0), 3, sev_clr),
    ]))
    return KeepTogether([t, Spacer(1, 0.3 * cm)])


def _code_issue_card(idx, issue, styles):
    cat      = issue.get("category", "")
    sub      = issue.get("subcategory", _CATEGORY_PLAIN.get(cat, cat))
    sev      = issue.get("severity", "Medium")
    sev_clr, sev_bg = _sev_color(sev)
    file_ref = _safe(issue.get("file", ""), 100)
    line_no  = issue.get("line", "")
    loc      = f"{file_ref}:{line_no}" if line_no else file_ref
    desc     = _safe(issue.get("description", ""), 600)
    ev       = _safe(issue.get("evidence", ""), 400)
    remed    = _safe(issue.get("remediation", ""), 700)
    cat_label = _CATEGORY_PLAIN.get(cat, cat.replace("_", " ").title())

    rows = [
        [
            Paragraph(f'<font color="{sev_clr.hexval()}"><b>{sev}</b></font>  '
                      f'<font size="8" color="{C_SLATE.hexval()}">#{idx}</font>',
                      ParagraphStyle("CH", fontSize=9, fontName="Helvetica-Bold", leading=12)),
            Paragraph(f"<b>{_safe(sub, 80)}</b>  "
                      f'<font color="{C_SLATE.hexval()}" size="8">({cat_label})</font>',
                      styles["bold"]),
        ],
        [
            Paragraph("File / Line", styles["label"]),
            Paragraph(f"<font face='Courier' size='8'>{loc}</font>", styles["body_plain"]),
        ],
        [
            Paragraph("Problem", styles["label"]),
            Paragraph(desc, styles["body_plain"]),
        ],
    ]
    if ev:
        rows.append([Paragraph("Evidence", styles["label"]), Paragraph(ev, styles["code"])])
    if remed:
        rows.append([Paragraph("Fix", styles["label"]), Paragraph(remed, styles["remediation"])])

    t = Table(rows, colWidths=[_LABEL_W, PAGE_W - _LABEL_W])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), sev_bg),
        ("BACKGROUND",   (0, 1), (-1, -1), colors.white),
        ("BACKGROUND",   (0, 1), (0, -1), C_LIGHT),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("GRID",         (0, 0), (-1, -1), 0.3, C_BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LINEABOVE",    (0, 0), (-1, 0), 3, sev_clr),
    ]))
    return KeepTogether([t, Spacer(1, 0.25 * cm)])


def _stat_box(label, value, color, styles, bg=None):
    bg = bg or C_LIGHT
    t = Table(
        [[Paragraph(
            f'<font size="20" color="{color.hexval()}"><b>{_safe(str(value), 20)}</b></font>'
            f'<br/><font size="8" color="{C_SLATE.hexval()}">{_safe(label, 40)}</font>',
            ParagraphStyle("SB", alignment=TA_CENTER, leading=26)
        )]],
        colWidths=[PAGE_W / 4 - 0.1 * cm]
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [4, 4, 4, 4]),
    ]))
    return t


def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_SLATE)
    canvas.drawRightString(A4[0] - 2 * cm, 0.7 * cm, f"Page {canvas.getPageNumber()}")
    canvas.drawString(2 * cm, 0.7 * cm, "Drift-X -- Confidential Code Quality Report")
    canvas.restoreState()


# ── Cover page ────────────────────────────────────────────────────────────────
def _build_cover(story, score, verdict, score_clr, score_bg, issues,
                 feature_changes, repo_url, branch, module_name, styles):

    losses = [c for c in feature_changes if "loss" in c.get("status", "").lower()]
    critical_cnt = sum(1 for i in issues if i.get("severity") == "Critical")

    # Dark header band
    header = Table([[
        Paragraph("Drift-X", styles["cover_title"]),
        Paragraph("Unified Code Quality &amp; Compliance Report",
                  ParagraphStyle("CSR", fontSize=13, fontName="Helvetica",
                                 textColor=colors.HexColor("#94a3b8"),
                                 alignment=TA_RIGHT, leading=18)),
    ]], colWidths=[PAGE_W * 0.4, PAGE_W * 0.6])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), C_NAVY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
    ]))
    story.append(header)

    # Meta strip
    repo_display = _safe(repo_url, 80).replace("https://github.com/", "")
    meta_items = [f"Repository: {repo_display}"]
    if branch and branch not in ("Unified", "default"):
        meta_items.append(f"Branch: {_safe(branch, 40)}")
    if module_name:
        meta_items.append(f"Module: {_safe(module_name, 40)}")
    meta_items.append(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')}")
    meta_row = [[Paragraph(_safe(m, 80), ParagraphStyle(
        "MI", fontSize=9, textColor=colors.white, fontName="Helvetica"
    )) for m in meta_items]]
    meta_t = Table(meta_row, colWidths=[PAGE_W / len(meta_items)] * len(meta_items))
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#334155")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("LINEBELOW",     (0, 0), (-1, -1), 3, C_INDIGO),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 0.5 * cm))

    # Score hero
    score_big = Paragraph(
        f'<font size="52" color="{score_clr.hexval()}"><b>{score:.0f}</b></font>'
        f'<font size="20" color="{C_SLATE.hexval()}"> / 100</font>',
        ParagraphStyle("SH", alignment=TA_CENTER, leading=64, spaceBefore=4)
    )
    verdict_pill = Paragraph(
        f'<font size="18" color="{score_clr.hexval()}"><b>{verdict}</b></font>',
        ParagraphStyle("VP", alignment=TA_CENTER, leading=28)
    )
    verdict_meaning = {
        "APPROVED":    "Code meets quality standards and is ready for production deployment.",
        "CONDITIONAL": "Code has issues that should be resolved before the next release.",
        "BLOCKED":     "Critical issues found -- deployment must be paused until fixes are applied.",
    }
    verdict_desc = Paragraph(
        _safe(verdict_meaning.get(verdict, ""), 200),
        ParagraphStyle("VD", alignment=TA_CENTER, fontSize=10,
                       textColor=C_SLATE, leading=15, spaceBefore=4)
    )
    score_card = Table(
        [[score_big], [verdict_pill], [Spacer(1, 0.3 * cm)],
         [ScoreBar(score, PAGE_W - 1.6 * cm)], [Spacer(1, 0.1 * cm)],
         [verdict_desc], [Spacer(1, 0.15 * cm)],
         [Paragraph("Pass threshold: 85 -- Conditional: 65-84 -- Blocked: below 65",
                    ParagraphStyle("TN", fontSize=8, textColor=C_SLATE,
                                   alignment=TA_CENTER))]],
        colWidths=[PAGE_W]
    )
    score_card.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), score_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("BOX",           (0, 0), (-1, -1), 1.5, score_clr),
    ]))
    story.append(score_card)
    story.append(Spacer(1, 0.4 * cm))

    # At-a-glance stats
    stats_row = [
        _stat_box("Issues Found",    len(issues),      C_INDIGO, styles),
        _stat_box("Critical Issues", critical_cnt,     C_RED if critical_cnt else C_GREEN, styles,
                  bg=C_RED_LT if critical_cnt else C_GREEN_LT),
        _stat_box("Feature Losses",  len(losses),      C_RED if losses else C_GREEN, styles,
                  bg=C_RED_LT if losses else C_GREEN_LT),
        _stat_box("Analysis Date",   datetime.now().strftime("%d %b %Y"), C_SLATE, styles),
    ]
    story.append(Table([stats_row], colWidths=[PAGE_W / 4] * 4))
    story.append(Spacer(1, 0.5 * cm))

    # Table of contents
    story.append(Paragraph("What's in this report", styles["h2"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=4))
    toc_items = [
        ("1", "Executive Summary",       "Overall verdict, what was analysed, key findings in plain English"),
        ("2", "How to Read This Report", "A guide to severity levels and what each category means"),
        ("3", "Quality Issues",          "All issues found -- grouped by severity, with exact fixes"),
        ("4", "Code Level Issues",       "Auth, pipeline, dependency, complexity and observability gaps"),
        ("5", "Feature Evolution",       "What changed across commits -- features added, removed, or broken"),
        ("6", "Module Analysis",         "Deep-dive into a specific module (if requested)"),
        ("7", "Top Priority Action Plan","Your ranked fix list -- most impactful changes first"),
    ]
    for num, title, desc in toc_items:
        story.append(Paragraph(
            f'<b>{num}.</b>  <b>{title}</b>  --  <font color="{C_SLATE.hexval()}">{desc}</font>',
            styles["toc_item"]
        ))
    story.append(Spacer(1, 0.3 * cm))


# ── Main generator ────────────────────────────────────────────────────────────
def generate_pdf_report(results, history_results=None, module_results=None,
                        code_level_results=None, repo_url="", branch="", module_name=""):

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=1.5 * cm, bottomMargin=2 * cm,
        title="Drift-X Code Quality Report",
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
    feature_changes = (history_results or {}).get("feature_changes", [])
    losses = [c for c in feature_changes if "loss" in c.get("status", "").lower()]

    # Sort issues: Critical → High → Medium → Low
    _sev_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    sorted_issues = sorted(issues, key=lambda i: _sev_rank.get(i.get("severity", "Low"), 9))

    # ── PAGE 1: Cover ─────────────────────────────────────────────────────────
    _build_cover(story, score, verdict, score_clr, score_bg, issues,
                 feature_changes, repo_url, branch, module_name, st)

    # ── PAGE 2: Executive Summary ─────────────────────────────────────────────
    story.append(PageBreak())
    story.extend(_section(
        "Executive Summary", st, icon="",
        description=(
            "This section summarises what was analysed, what was found, and what the "
            "deployment decision is. Written for both technical and non-technical readers."
        )
    ))

    # Deployment decision banner
    gate_cfg = {
        "APPROVED":    ("APPROVED FOR DEPLOYMENT",
                        "The codebase meets all quality thresholds. "
                        "Issues found are low-severity and can be resolved in normal sprint work. "
                        "Production deployment is cleared.",
                        C_GREEN, C_GREEN_LT),
        "CONDITIONAL": ("CONDITIONAL -- FIX BEFORE NEXT RELEASE",
                        "The codebase passes minimum quality checks but contains issues "
                        "that must be resolved before the next scheduled release. "
                        "Deployment can proceed for hotfixes only.",
                        C_AMBER, C_AMBER_LT),
        "BLOCKED":     ("DEPLOYMENT BLOCKED -- CRITICAL FIXES REQUIRED",
                        "The codebase has critical defects that create unacceptable risk. "
                        "Deployment must be paused. Resolve all Critical and High severity "
                        "issues listed in Section 3 before re-running this analysis.",
                        C_RED, C_RED_LT),
    }
    gate_title, gate_desc, g_clr, g_bg = gate_cfg.get(verdict, gate_cfg["CONDITIONAL"])
    gate_t = Table(
        [[Paragraph(gate_title, ParagraphStyle(
            "GT", fontSize=11, fontName="Helvetica-Bold",
            textColor=g_clr, alignment=TA_CENTER
        ))],
         [Paragraph(_safe(gate_desc, 400), ParagraphStyle(
             "GD", fontSize=10, textColor=colors.HexColor("#374151"),
             alignment=TA_CENTER, leading=15
         ))]],
        colWidths=[PAGE_W]
    )
    gate_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), g_bg),
        ("BOX",           (0, 0), (-1, -1), 2, g_clr),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
    ]))
    story.append(gate_t)
    story.append(Spacer(1, 0.4 * cm))

    # Key findings table
    security_cnt = sum(1 for i in issues if "security" in i.get("type", "").lower())
    testing_cnt  = sum(1 for i in issues if "testing"  in i.get("type", "").lower())
    eh_cnt       = sum(1 for i in issues if "error"    in i.get("type", "").lower())
    critical_cnt = sum(1 for i in issues if i.get("severity") == "Critical")
    high_cnt     = sum(1 for i in issues if i.get("severity") == "High")

    exec_data = [
        ["What we measured",  "Result"],
        ["Overall Score",     f"{score:.0f} out of 100"],
        ["Deployment Decision", verdict],
        ["Total Issues Found", f"{len(issues)} issue(s) across all categories"],
        ["Critical Issues",   f"{critical_cnt} -- must fix before deployment"
                              if critical_cnt else "None -- no blocking issues"],
        ["High Issues",       f"{high_cnt} -- fix before next release"
                              if high_cnt else "None"],
        ["Security Risks",    f"{security_cnt} security issue(s) identified"
                              if security_cnt else "None identified"],
        ["Error Handling Gaps", f"{eh_cnt} gap(s) in error handling"
                                if eh_cnt else "None identified"],
        ["Missing Tests",     f"{testing_cnt} test gap(s) found"
                              if testing_cnt else "Test coverage gaps not found"],
        ["Feature Losses",    f"{len(losses)} feature(s) removed without replacement"
                              if losses else "No feature losses detected"],
        ["Repository",        _safe(repo_url, 90).replace("https://github.com/", "github.com/")],
        ["Analysed On",       datetime.now().strftime("%d %B %Y at %H:%M")],
    ]
    exec_t = Table(
        [[Paragraph(_safe(r[0], 60), st["label"]),
          Paragraph(_safe(r[1], 200), st["body"])] for r in exec_data],
        colWidths=[4.5 * cm, PAGE_W - 4.5 * cm]
    )
    exec_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.3, C_BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR",     (0, 1), (0, -1), C_SLATE),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
    ]))
    story.append(exec_t)
    story.append(Spacer(1, 0.4 * cm))

    summary_text = _safe(results.get("summary", "No analysis summary available."), 2000)
    story.append(Paragraph("<b>Analysis Overview</b>", st["bold"]))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph(summary_text, st["body_plain"]))

    # ── PAGE 3: How to Read This Report ──────────────────────────────────────
    story.append(PageBreak())
    story.extend(_section(
        "How to Read This Report", st, icon="",
        description="Use this guide to understand what each severity level means and what action to take."
    ))

    story.append(Paragraph("<b>Severity Levels Explained</b>", st["bold"]))
    story.append(Spacer(1, 0.15 * cm))
    story.append(_severity_legend(st))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("<b>Issue Categories Explained</b>", st["bold"]))
    story.append(Spacer(1, 0.15 * cm))
    cat_defs = [
        ["Category",              "What it covers",                              "Who should act"],
        ["Security Risk",         "Vulnerabilities that could allow unauthorised access or data breaches", "Security / Lead Dev"],
        ["Auth & Access Control", "Login, tokens, session expiry, role-based access",                     "Backend developer"],
        ["Error Handling Gap",    "Errors that are silently swallowed, causing invisible failures",        "Backend developer"],
        ["Incomplete Feature",    "A requirement was promised but not fully built",                        "Product + Dev team"],
        ["Feature Differs from Requirements", "Feature was built differently from the specification",     "Product + Dev team"],
        ["Missing Tests",         "Code paths with no automated test coverage",                            "QA / Dev team"],
        ["Performance Problem",   "Code that may be slow or fail under real-world load",                  "Backend developer"],
        ["Background Jobs & Concurrency", "Issues with async tasks, threads, or background workers",      "Backend developer"],
        ["Package & Dependency Safety", "Outdated, unpinned, or risky third-party libraries",             "DevOps / Lead Dev"],
        ["Code Complexity",       "Functions that are too large or complex to safely maintain or test",   "Developer assigned"],
        ["Logging / Monitoring Gap", "Missing logs that make it impossible to debug failures in prod",    "Backend developer"],
        ["Deployment Configuration Gap", "Missing health checks, env vars, or startup validation",        "DevOps"],
    ]
    cat_t = Table(
        [[Paragraph(_safe(r[0], 60), ParagraphStyle("CH", fontSize=8, fontName="Helvetica-Bold",
                                                      textColor=colors.white if i == 0 else C_NAVY)),
          Paragraph(_safe(r[1], 200), st["body_plain"] if i > 0 else ParagraphStyle(
              "CB", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white)),
          Paragraph(_safe(r[2], 60), st["small"] if i > 0 else ParagraphStyle(
              "CB2", fontSize=8, fontName="Helvetica-Bold", textColor=colors.white))]
         for i, r in enumerate(cat_defs)],
        colWidths=[4.5 * cm, PAGE_W - 7.5 * cm, 3.0 * cm]
    )
    cat_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_LIGHT, colors.white]),
        ("GRID",          (0, 0), (-1, -1), 0.3, C_BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
    ]))
    story.append(cat_t)

    # ── PAGE 4+: Quality Issues ───────────────────────────────────────────────
    story.append(PageBreak())
    if sorted_issues:
        story.extend(_section(
            f"Quality Issues  --  {len(sorted_issues)} found", st, icon="",
            description=(
                "Issues are listed most severe first. Each card shows what is wrong, "
                "where it is in the code, why it matters for the business, and exact steps to fix it."
            )
        ))

        # Issue summary by category
        type_counts = {}
        for iss in sorted_issues:
            label = _plain_type(iss.get("type", "Other"))
            type_counts[label] = type_counts.get(label, 0) + 1

        sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for iss in sorted_issues:
            sev_counts[iss.get("severity", "Low")] = sev_counts.get(iss.get("severity", "Low"), 0) + 1

        sev_row = []
        for sev, cnt in sev_counts.items():
            sev_clr2, _ = _sev_color(sev)
            sev_row.append(Paragraph(
                f'<font size="18" color="{sev_clr2.hexval()}"><b>{cnt}</b></font>'
                f'<br/><font size="8" color="{C_SLATE.hexval()}">{sev}</font>',
                ParagraphStyle("SR", alignment=TA_CENTER, leading=22)
            ))
        sev_t = Table([sev_row], colWidths=[PAGE_W / 4] * 4)
        sev_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(sev_t)
        story.append(Spacer(1, 0.3 * cm))

        for idx, issue in enumerate(sorted_issues, 1):
            story.append(_issue_card(idx, issue, st))
    else:
        story.extend(_section("Quality Issues", st))
        story.append(Paragraph(
            "No quality issues were detected. The codebase meets all quality criteria.", st["body_plain"]
        ))

    # ── Code Level Issues ─────────────────────────────────────────────────────
    if code_level_results:
        story.append(PageBreak())
        static_total = code_level_results.get("total_static_issues", 0)
        story.extend(_section(
            f"Code Level Issues  --  {static_total} static findings", st, icon="",
            description=(
                "These issues were found by automated code analysis tools scanning the source files directly. "
                "They cover authentication gaps, unsafe concurrency patterns, "
                "dependency risks, code complexity, security vulnerabilities (Bandit), "
                "and missing observability."
            )
        ))

        # LLM summary if present
        llm_summary = _safe(code_level_results.get("summary", ""), 600)
        if llm_summary:
            story.append(Paragraph("<b>AI Analysis Summary</b>", st["bold"]))
            story.append(Paragraph(llm_summary, st["callout"]))
            story.append(Spacer(1, 0.3 * cm))

        by_category = code_level_results.get("by_category", {})
        llm_keys = {
            "llm_auth_issues":           "auth",
            "llm_pipeline_issues":       "pipeline",
            "llm_dependency_issues":     "dependencies",
            "llm_error_handling_issues": "error_handling",
            "llm_observability_issues":  "observability",
        }
        # Merge LLM issues into by_category
        for llm_key, cat in llm_keys.items():
            for iss in code_level_results.get(llm_key, []):
                by_category.setdefault(cat, []).append({**iss, "category": cat, "source": "llm"})

        cat_order = ["auth", "security", "pipeline", "error_handling",
                     "dependencies", "complexity", "observability", "dead_code"]

        total_code_issues = 0
        for cat in cat_order:
            cat_issues = by_category.get(cat, [])
            if not cat_issues:
                continue
            total_code_issues += len(cat_issues)
            cat_label = _CATEGORY_PLAIN.get(cat, cat.replace("_", " ").title())

            story.append(Paragraph(
                f"<b>{cat_label}</b>  "
                f'<font color="{C_SLATE.hexval()}" size="9">({len(cat_issues)} finding(s))</font>',
                st["h3"]
            ))
            sev_sorted = sorted(cat_issues, key=lambda i: _sev_rank.get(i.get("severity", "Low"), 9))
            for idx, issue in enumerate(sev_sorted[:20], 1):
                story.append(_code_issue_card(idx, issue, st))
            if len(cat_issues) > 20:
                story.append(Paragraph(
                    f"... and {len(cat_issues) - 20} more {cat_label} findings not shown.",
                    st["small"]
                ))
            story.append(Spacer(1, 0.2 * cm))

    # ── Feature Evolution ─────────────────────────────────────────────────────
    if history_results and "error" not in history_results:
        story.append(PageBreak())
        story.extend(_section(
            "Feature Evolution", st, icon="",
            description=(
                "This section analyses commit history to check whether features were added, "
                "removed, or broken between versions. A 'Loss' means a feature that was "
                "working is now gone with no replacement -- this requires immediate attention."
            )
        ))

        meta   = history_results.get("analysis_metadata", {})
        evo_sum = _safe(history_results.get("summary", ""), 800)
        n_changes = len(feature_changes)
        n_losses  = len(losses)
        n_replace = sum(1 for c in feature_changes if "replacement" in c.get("status", "").lower())
        n_refactor = sum(1 for c in feature_changes if "refactor" in c.get("status", "").lower())

        evo_row = [
            Paragraph(f'<font size="18" color="{C_RED.hexval() if n_losses else C_GREEN.hexval()}"><b>{n_losses}</b></font><br/><font size="8">Feature Losses</font>',
                      ParagraphStyle("ES", alignment=TA_CENTER, leading=22)),
            Paragraph(f'<font size="18" color="{C_AMBER.hexval()}"><b>{n_changes}</b></font><br/><font size="8">Total Changes</font>',
                      ParagraphStyle("ES", alignment=TA_CENTER, leading=22)),
            Paragraph(f'<font size="18" color="{C_GREEN.hexval()}"><b>{n_replace}</b></font><br/><font size="8">Safe Replacements</font>',
                      ParagraphStyle("ES", alignment=TA_CENTER, leading=22)),
            Paragraph(f'<font size="18" color="{C_SLATE.hexval()}"><b>{n_refactor}</b></font><br/><font size="8">Refactors</font>',
                      ParagraphStyle("ES", alignment=TA_CENTER, leading=22)),
        ]
        evo_t = Table([evo_row], colWidths=[PAGE_W / 4] * 4)
        evo_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(evo_t)
        story.append(Spacer(1, 0.3 * cm))

        if evo_sum:
            story.append(Paragraph(evo_sum, st["body_plain"]))
            story.append(Spacer(1, 0.3 * cm))

        for change in feature_changes:
            fname   = _safe(change.get("feature_name", "Unknown Feature"), 120)
            status  = change.get("status", "")
            sev     = change.get("severity", "Medium")
            impact  = _safe(change.get("impact", ""), 500)
            rep     = _safe(change.get("replacement_logic", ""), 500)
            remed   = _safe(change.get("remediation", ""), 700)
            req_ref = _safe(change.get("requirement_reference", ""), 200)
            commit  = _safe(change.get("commit_info", ""), 80)
            is_problem = any(w in status.lower() for w in
                             ["loss", "missing", "regression", "breaking", "drift", "violation"])
            sev_clr2, sev_bg2 = _sev_color(sev)

            status_symbol = "[LOSS]" if is_problem else "[OK]"
            rows = [[
                Paragraph(f"{status_symbol} <b>{_safe(fname, 80)}</b>", st["bold"]),
                Paragraph(
                    f'Status: <b>{_safe(status, 50)}</b>  |  '
                    f'Severity: <font color="{sev_clr2.hexval()}"><b>{sev}</b></font>  |  '
                    f'<font size="8" color="{C_SLATE.hexval()}">{_SEV_PLAIN.get(sev, "")}</font>',
                    st["body"]
                ),
            ]]
            if req_ref:
                rows.append([Paragraph("Requirement", st["label"]),
                              Paragraph(req_ref, st["body_plain"])])
            if commit:
                rows.append([Paragraph("Commit", st["label"]),
                              Paragraph(f"<font face='Courier' size='8'>{commit}</font>", st["body_plain"])])
            if impact:
                rows.append([Paragraph("Business Impact", st["label"]),
                              Paragraph(impact, st["plain_impact"])])
            if rep:
                rows.append([Paragraph("What replaced it", st["label"]),
                              Paragraph(rep, st["body_plain"])])
            if remed:
                rows.append([Paragraph("How to fix", st["label"]),
                              Paragraph(remed, st["remediation"])])

            ct = Table(rows, colWidths=[_LABEL_W, PAGE_W - _LABEL_W])
            ct.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), sev_bg2 if is_problem else C_GREEN_LT),
                ("BACKGROUND",   (0, 1), (-1, -1), colors.white),
                ("BACKGROUND",   (0, 1), (0, -1), C_LIGHT),
                ("GRID",         (0, 0), (-1, -1), 0.3, C_BORDER),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
                ("LINEABOVE",    (0, 0), (-1, 0), 2.5,
                 sev_clr2 if is_problem else C_GREEN),
                ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ]))
            story.append(KeepTogether([ct, Spacer(1, 0.25 * cm)]))

    # ── Module Analysis ───────────────────────────────────────────────────────
    if module_results:
        story.append(PageBreak())
        mod_name = _safe(module_results.get("module_name", ""), 60)
        story.extend(_section(
            f"Module Analysis: {mod_name}", st, icon="",
            description=f"Deep-dive into the '{mod_name}' module -- its purpose, structure, and issues."
        ))

        analysis  = module_results.get("analysis", {})
        mod_score = analysis.get("compliance_score")
        ms_clr, ms_bg, ms_v = _score_color(float(mod_score or 0))

        mod_row = [
            Paragraph(f'<font size="18" color="{C_INDIGO.hexval()}"><b>{module_results.get("file_count", 0)}</b></font><br/><font size="8">Module Files</font>',
                      ParagraphStyle("MS", alignment=TA_CENTER, leading=22)),
            Paragraph(f'<font size="18" color="{C_SLATE.hexval()}"><b>{module_results.get("usage_count", 0)}</b></font><br/><font size="8">Referenced In</font>',
                      ParagraphStyle("MS", alignment=TA_CENTER, leading=22)),
            Paragraph(f'<font size="18" color="{ms_clr.hexval()}"><b>{mod_score if mod_score is not None else "N/A"}</b></font><br/><font size="8">Module Score</font>',
                      ParagraphStyle("MS", alignment=TA_CENTER, leading=22)),
        ]
        mod_t = Table([mod_row], colWidths=[PAGE_W / 3] * 3)
        mod_t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), C_LIGHT),
            ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, C_BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(mod_t)
        story.append(Spacer(1, 0.3 * cm))

        if analysis.get("module_purpose"):
            story.append(Paragraph("<b>What this module does:</b>", st["bold"]))
            story.append(Paragraph(_safe(analysis["module_purpose"], 500), st["body_plain"]))
            story.append(Spacer(1, 0.2 * cm))

        if analysis.get("key_components"):
            story.append(Paragraph("<b>Key components:</b>", st["bold"]))
            for comp in analysis["key_components"][:12]:
                story.append(Paragraph(f"- {_safe(comp, 120)}", st["body_plain"]))
            story.append(Spacer(1, 0.2 * cm))

        related = module_results.get("related_files", [])
        if related:
            story.append(Paragraph(f"<b>Files in this module ({len(related)}):</b>", st["bold"]))
            for f in related[:20]:
                story.append(Paragraph(f"<font face='Courier' size='8'>  {_safe(f, 120)}</font>",
                                        st["body_plain"]))
            story.append(Spacer(1, 0.2 * cm))

        mod_issues = analysis.get("issues", [])
        if mod_issues:
            story.append(Paragraph(f"<b>Issues in this module ({len(mod_issues)}):</b>", st["bold"]))
            story.append(Spacer(1, 0.1 * cm))
            for idx, issue in enumerate(mod_issues[:15], 1):
                story.append(_issue_card(idx, issue, st))

    # ── Top Priority Action Plan ──────────────────────────────────────────────
    story.append(PageBreak())
    story.extend(_section(
        "Top Priority Action Plan", st, icon="",
        description=(
            "These are the most impactful issues to fix first. Resolving them in this order "
            "will have the greatest effect on quality, security, and deployment readiness."
        )
    ))

    # Combine quality issues + critical code level issues
    all_priority = list(sorted_issues)
    if code_level_results:
        by_cat = code_level_results.get("by_category", {})
        for cat_issues in by_cat.values():
            for iss in cat_issues:
                if iss.get("severity") in ("Critical", "High"):
                    all_priority.append({
                        "type": _CATEGORY_PLAIN.get(iss.get("category", ""), "Code Issue"),
                        "severity": iss.get("severity", "High"),
                        "description": iss.get("description", ""),
                        "evidence": iss.get("evidence", ""),
                        "reasoning": "",
                        "remediation": iss.get("remediation", ""),
                    })

    top5 = sorted(all_priority, key=lambda i: _sev_rank.get(i.get("severity", "Low"), 9))[:7]

    if top5:
        for rank, issue in enumerate(top5, 1):
            sev    = issue.get("severity", "Medium")
            sev_clr2, sev_bg2 = _sev_color(sev)
            itype  = _plain_type(issue.get("type", ""))
            desc   = _safe(issue.get("description", ""), 300)
            remed  = _safe(issue.get("remediation", "No specific steps provided."), 800)
            reason = _safe(issue.get("reasoning", ""), 400)

            rank_rows = [
                [
                    Paragraph(f"<b>#{rank}</b>", ParagraphStyle(
                        "RN", fontSize=16, fontName="Helvetica-Bold",
                        textColor=sev_clr2, alignment=TA_CENTER
                    )),
                    Paragraph(
                        f"<b>{_safe(itype, 80)}</b>  "
                        f'<font color="{sev_clr2.hexval()}" size="9">[{sev}]</font>  '
                        f'<font color="{C_SLATE.hexval()}" size="9">-- {_SEV_PLAIN.get(sev, "")}</font>',
                        st["bold"]
                    ),
                ],
                [
                    Paragraph("Problem", st["label"]),
                    Paragraph(desc, st["body_plain"]),
                ],
            ]
            if reason:
                rank_rows.append([Paragraph("Why it matters", st["label"]),
                                   Paragraph(reason, st["plain_impact"])])
            rank_rows.append([Paragraph("Steps to fix", st["label"]),
                               Paragraph(remed, st["remediation"])])

            rec_t = Table(rank_rows, colWidths=[_LABEL_W, PAGE_W - _LABEL_W])
            rec_t.setStyle(TableStyle([
                ("BACKGROUND",   (0, 0), (-1, 0), sev_bg2),
                ("BACKGROUND",   (0, 1), (-1, -1), colors.white),
                ("BACKGROUND",   (0, 1), (0, -1), C_LIGHT),
                ("GRID",         (0, 0), (-1, -1), 0.3, C_BORDER),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
                ("LINEABOVE",    (0, 0), (-1, 0), 3, sev_clr2),
                ("FONTSIZE",     (0, 0), (-1, -1), 9),
            ]))
            story.append(KeepTogether([rec_t, Spacer(1, 0.3 * cm)]))
    else:
        story.append(Paragraph(
            "No critical or high-priority issues found. The codebase is in good health.", st["body_plain"]
        ))

    # What to do next
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("<b>Next Steps</b>", st["bold"]))
    story.append(Spacer(1, 0.1 * cm))
    next_steps = {
        "APPROVED":    [
            "Share this report with the release manager to confirm deployment approval.",
            "Schedule fixes for Medium and Low issues in the next sprint.",
            "Re-run this analysis after the next major code change.",
        ],
        "CONDITIONAL": [
            "Assign all High severity issues to developers immediately.",
            "Set a deadline to resolve High issues before the next planned release.",
            "Re-run this analysis to confirm all issues are resolved before releasing.",
        ],
        "BLOCKED":     [
            "Pause the deployment pipeline until all Critical issues are resolved.",
            "Hold an emergency review meeting to assign Critical issues to developers.",
            "Re-run this analysis after fixes -- do not deploy until APPROVED status is achieved.",
        ],
    }
    for step in next_steps.get(verdict, []):
        story.append(Paragraph(f"- {step}", st["body_plain"]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.8 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 0.15 * cm))
    footer_t = Table([[
        Paragraph("Drift-X -- AI-Powered Code Quality Gateway  |  Confidential", st["small"]),
        Paragraph(datetime.now().strftime("%Y-%m-%d"),
                  ParagraphStyle("FR", fontSize=8, textColor=C_SLATE, alignment=TA_RIGHT)),
    ]], colWidths=[PAGE_W * 0.7, PAGE_W * 0.3])
    footer_t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(footer_t)

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buf.seek(0)
    return buf.getvalue()
