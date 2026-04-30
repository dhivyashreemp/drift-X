from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from io import BytesIO
from datetime import datetime


def _safe_text(text, max_len=500):
    if not text:
        return ""
    text = str(text)
    text = text.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
    return text[:max_len]


def generate_pdf_report(results, history_results=None, module_results=None,
                        repo_url="", branch="", module_name=""):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="DriftX 2.0 Analysis Report",
        author="DriftX"
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=22, spaceAfter=6, textColor=colors.HexColor("#1a3a5c")
    )
    h2_style = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=14, spaceAfter=6, spaceBefore=12,
        textColor=colors.HexColor("#2c5f8a")
    )
    h3_style = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontSize=11, spaceAfter=4, spaceBefore=8,
        textColor=colors.HexColor("#3d7ab5")
    )
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, textColor=colors.grey)
    code_style = ParagraphStyle(
        "Code", parent=normal, fontSize=8,
        fontName="Courier",
        backColor=colors.HexColor("#f4f4f4"),
        leftIndent=12, rightIndent=12,
        spaceAfter=2
    )
    label_style = ParagraphStyle(
        "Label", parent=normal, fontName="Helvetica-Bold", fontSize=9
    )

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("DriftX 2.0 — Analysis Report", title_style))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        small
    ))
    story.append(Spacer(1, 0.2 * cm))

    meta_rows = [["Repository", _safe_text(repo_url, 200)]]
    if branch:
        meta_rows.append(["Branch", _safe_text(branch)])
    if module_name:
        meta_rows.append(["Module Focus", _safe_text(module_name)])

    meta_table = Table(meta_rows, colWidths=[4 * cm, 13 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f0f6ff"), colors.white]),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2c5f8a")))
    story.append(Spacer(1, 0.4 * cm))

    # ── Score Card ───────────────────────────────────────────────────────────
    score = results.get("score", 0)
    try:
        score = float(score)
    except Exception:
        score = 0.0

    if score >= 80:
        status, status_color = "PASSED ✓", colors.HexColor("#1a7a3c")
    elif score >= 60:
        status, status_color = "WARNING ⚠", colors.HexColor("#b36200")
    else:
        status, status_color = "FAILED ✗", colors.HexColor("#a01010")

    score_data = [
        ["Overall Quality Score", f"{score:.1f} / 100"],
        ["Gate Status", status],
        ["Pass Threshold", "80 / 100"],
    ]
    score_table = Table(score_data, colWidths=[6 * cm, 11 * cm])
    score_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d0e8ff")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8f8f8")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.white),
        ("TEXTCOLOR", (1, 1), (1, 1), status_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.5 * cm))

    # ── Summary ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Summary", h2_style))
    story.append(Paragraph(_safe_text(results.get("summary", "No summary available."), 800), normal))
    story.append(Spacer(1, 0.4 * cm))

    # ── Issues ───────────────────────────────────────────────────────────────
    issues = results.get("issues", [])
    if issues:
        story.append(Paragraph(f"Identified Issues ({len(issues)})", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

        for i, issue in enumerate(issues, 1):
            issue_type = issue.get("type", "Unknown")
            desc = _safe_text(issue.get("description", ""), 300)
            is_critical = any(w in issue_type.lower() for w in ["loss", "drift", "violation", "missing", "failed"])
            header_color = colors.HexColor("#ffe5e5") if is_critical else colors.HexColor("#f0f8e8")

            rows = [
                [Paragraph(f"{i}. [{issue_type}]", label_style),
                 Paragraph(desc, normal)],
            ]
            if issue.get("evidence"):
                rows.append([Paragraph("Evidence", label_style),
                              Paragraph(_safe_text(issue.get("evidence"), 300), code_style)])
            if issue.get("reasoning"):
                rows.append([Paragraph("Reasoning", label_style),
                              Paragraph(_safe_text(issue.get("reasoning"), 300), normal)])
            if issue.get("remediation"):
                rows.append([Paragraph("Remediation", label_style),
                              Paragraph(_safe_text(issue.get("remediation"), 400), normal)])

            issue_table = Table(rows, colWidths=[3 * cm, 14 * cm])
            issue_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), header_color),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ]))
            story.append(KeepTogether([issue_table, Spacer(1, 0.25 * cm)]))

    # ── Feature Evolution ─────────────────────────────────────────────────────
    if history_results and "error" not in history_results:
        story.append(Paragraph("Feature Evolution", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

        metadata = history_results.get("analysis_metadata", {})
        base_h = str(metadata.get("base_commit", "Initial"))[:8]
        head_h = str(metadata.get("head_commit", "Now"))[:8]
        story.append(Paragraph(f"Commit Range: <b>{base_h}</b> → <b>{head_h}</b>", normal))

        evo_summary = history_results.get("summary", "")
        if evo_summary:
            story.append(Paragraph(_safe_text(evo_summary, 600), normal))
        story.append(Spacer(1, 0.3 * cm))

        for change in history_results.get("feature_changes", []):
            feature_name = _safe_text(change.get("feature_name", ""), 100)
            status_val = change.get("status", "")
            is_loss = "loss" in status_val.lower() or "missing" in status_val.lower()
            icon = "✗" if is_loss else "↺"
            clr = colors.HexColor("#ffe5e5") if is_loss else colors.HexColor("#e8f5e9")

            rows = [
                [Paragraph(f"{icon} {feature_name}", label_style),
                 Paragraph(f"Status: {status_val} | Severity: {change.get('severity', 'Medium')}", normal)],
            ]
            if change.get("impact"):
                rows.append([Paragraph("Impact", label_style),
                              Paragraph(_safe_text(change.get("impact"), 300), normal)])
            if change.get("replacement_logic"):
                rows.append([Paragraph("Replacement", label_style),
                              Paragraph(_safe_text(change.get("replacement_logic"), 300), normal)])

            chg_table = Table(rows, colWidths=[3 * cm, 14 * cm])
            chg_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), clr),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(KeepTogether([chg_table, Spacer(1, 0.2 * cm)]))

    # ── Module Analysis ───────────────────────────────────────────────────────
    if module_results:
        story.append(Paragraph(
            f"Module Analysis: {_safe_text(module_results.get('module_name', ''), 80)}", h2_style
        ))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))

        mod_meta = [
            ["Module Files Identified", str(module_results.get("file_count", 0))],
            ["Referenced in Other Files", str(module_results.get("usage_count", 0))],
        ]
        mod_table = Table(mod_meta, colWidths=[8 * cm, 9 * cm])
        mod_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f0f6ff"), colors.white]),
        ]))
        story.append(mod_table)
        story.append(Spacer(1, 0.3 * cm))

        related_files = module_results.get("related_files", [])
        if related_files:
            story.append(Paragraph("Module Files:", h3_style))
            for f in related_files[:20]:
                story.append(Paragraph(f"• {_safe_text(f, 120)}", code_style))
            story.append(Spacer(1, 0.3 * cm))

        usages = module_results.get("usage_in_files", {})
        if usages:
            story.append(Paragraph("Referenced In:", h3_style))
            for file_path, usage_lines in list(usages.items())[:15]:
                story.append(Paragraph(f"<b>{_safe_text(file_path, 120)}</b>", normal))
                for usage in usage_lines[:3]:
                    story.append(Paragraph(
                        f"  Line {usage['line']}: {_safe_text(usage['content'], 120)}",
                        code_style
                    ))
            story.append(Spacer(1, 0.3 * cm))

        analysis = module_results.get("analysis", {})
        if analysis:
            if analysis.get("module_purpose"):
                story.append(Paragraph("Module Purpose:", h3_style))
                story.append(Paragraph(_safe_text(analysis["module_purpose"], 600), normal))

            if analysis.get("key_components"):
                story.append(Paragraph("Key Components:", h3_style))
                for comp in analysis["key_components"][:10]:
                    story.append(Paragraph(f"• {_safe_text(comp, 200)}", normal))

            if analysis.get("summary"):
                story.append(Paragraph("Module Analysis Summary:", h3_style))
                story.append(Paragraph(_safe_text(analysis["summary"], 600), normal))

            mod_issues = analysis.get("issues", [])
            if mod_issues:
                story.append(Paragraph("Module-Specific Issues:", h3_style))
                for issue in mod_issues[:10]:
                    story.append(Paragraph(
                        f"• [{_safe_text(issue.get('type', ''), 40)}] {_safe_text(issue.get('description', ''), 200)}",
                        normal
                    ))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph(
        "Generated by DriftX 2.0 — AI-Powered Compliance Gateway",
        ParagraphStyle("Footer", parent=normal, fontSize=8, textColor=colors.grey, alignment=1)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
