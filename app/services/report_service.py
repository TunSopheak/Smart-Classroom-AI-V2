import csv
from collections import Counter
from datetime import datetime
from io import BytesIO, StringIO
from xml.sax.saxutils import escape

from app.models.ai_event import AIEvent
from app.models.attendance import Attendance


ATTENDANCE_COLUMNS = [
    "Student Code",
    "Student Name",
    "Class",
    "Subject",
    "Teacher",
    "Session Date",
    "Time",
    "Status",
    "Source",
    "Recorded At",
]

AI_EVENT_COLUMNS = [
    "Detected At",
    "Class",
    "Subject",
    "Teacher",
    "Session Date",
    "Session Time",
    "Event Type",
    "Severity",
    "Message",
]


def pdf_text(value) -> str:
    return escape(str(value or ""))


def attendance_row(record: Attendance) -> list[str]:
    student = record.student
    session = record.session
    teacher = session.teacher
    return [
        student.student_code,
        f"{student.first_name} {student.last_name}",
        f"{session.class_group.class_code} - {session.class_group.name}",
        f"{session.subject.code} - {session.subject.name}",
        f"{teacher.teacher_code} - {teacher.first_name} {teacher.last_name}",
        session.session_date.strftime("%Y-%m-%d") if session.session_date else "",
        f"{session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}",
        record.status,
        record.source,
        record.recorded_at.strftime("%Y-%m-%d %H:%M") if record.recorded_at else "",
    ]


def build_attendance_csv(records: list[Attendance]) -> bytes:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(ATTENDANCE_COLUMNS)
    for record in records:
        writer.writerow(attendance_row(record))
    return output.getvalue().encode("utf-8-sig")


def ai_event_row(event: AIEvent) -> list[str]:
    session = event.session
    class_group = session.class_group if session else event.class_group
    subject = session.subject if session else event.subject
    teacher = session.teacher if session else event.teacher
    return [
        event.detected_at.strftime("%Y-%m-%d %H:%M") if event.detected_at else "",
        f"{class_group.class_code} - {class_group.name}" if class_group else "",
        f"{subject.code} - {subject.name}" if subject else "",
        f"{teacher.teacher_code} - {teacher.first_name} {teacher.last_name}" if teacher else "",
        session.session_date.strftime("%Y-%m-%d") if session and session.session_date else "",
        f"{session.start_time.strftime('%H:%M')} - {session.end_time.strftime('%H:%M')}" if session else "",
        event.event_type.replace("_", " "),
        event.severity,
        event.message or event.description or "",
    ]


def build_ai_events_csv(events: list[AIEvent]) -> bytes:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(AI_EVENT_COLUMNS)
    for event in events:
        writer.writerow(ai_event_row(event))
    return output.getvalue().encode("utf-8-sig")


def filter_summary(filters: dict) -> str:
    parts = []
    if filters.get("class_group_label"):
        parts.append(f"Class: {filters['class_group_label']}")
    if filters.get("session_label"):
        parts.append(f"Session: {filters['session_label']}")
    if filters.get("student_search"):
        parts.append(f"Student search: {filters['student_search']}")
    if filters.get("status"):
        parts.append(f"Status: {filters['status']}")
    return "; ".join(parts) if parts else "No filters applied"


def attendance_counts(records: list[Attendance]) -> dict[str, int]:
    counts = Counter(record.status for record in records)
    return {
        "total": len(records),
        "present": counts.get("present", 0),
        "late": counts.get("late", 0),
        "absent": counts.get("absent", 0),
        "permission": counts.get("permission", 0),
    }


def ai_filter_summary(filters: dict) -> str:
    parts = []
    if filters.get("class_group_label"):
        parts.append(f"Class: {filters['class_group_label']}")
    if filters.get("session_label"):
        parts.append(f"Session: {filters['session_label']}")
    if filters.get("subject_label"):
        parts.append(f"Subject: {filters['subject_label']}")
    if filters.get("teacher_label"):
        parts.append(f"Teacher: {filters['teacher_label']}")
    if filters.get("event_type"):
        parts.append(f"Event type: {filters['event_type'].replace('_', ' ')}")
    if filters.get("severity"):
        parts.append(f"Severity: {filters['severity']}")
    if filters.get("date"):
        parts.append(f"Date: {filters['date']}")
    return "; ".join(parts) if parts else "No filters applied"


def build_ai_events_pdf(
    events: list[AIEvent],
    filters: dict,
    summary: dict[str, int],
    note: str | None = None,
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.32 * inch,
        leftMargin=0.32 * inch,
        topMargin=0.36 * inch,
        bottomMargin=0.42 * inch,
    )
    doc.allowSplitting = 1
    styles = getSampleStyleSheet()
    table_style = ParagraphStyle(
        "AIEventTableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.1,
        leading=7.2,
        wordWrap="CJK",
        splitLongWords=True,
    )
    header_style = ParagraphStyle(
        "AIEventTableHeader",
        parent=table_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    story = [
        Paragraph("Smart Classroom AI Monitoring V2", styles["Title"]),
        Paragraph("AI Monitoring Event Report", styles["Heading2"]),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Paragraph(f"Applied filters: {ai_filter_summary(filters)}", styles["Normal"]),
        Spacer(1, 0.15 * inch),
        Paragraph(
            "Summary: "
            f"Total {summary['total']} | Info {summary['info']} | Warning {summary['warning']} | "
            f"Critical {summary['critical']} | Face Detected {summary['face_detected']} | "
            f"Empty Occupancy {summary['occupancy_empty']} | Light Auto Off {summary['light_auto_off']} | "
            f"Light Auto On {summary['light_auto_on']}",
            styles["Normal"],
        ),
        Spacer(1, 0.18 * inch),
    ]
    if note:
        story.extend([Paragraph(note, styles["Italic"]), Spacer(1, 0.12 * inch)])

    if not events:
        story.append(Paragraph("No AI monitoring events match the selected filters.", styles["Normal"]))
    else:
        table_data = [
            [
                Paragraph("Detected", header_style),
                Paragraph("Class", header_style),
                Paragraph("Subject", header_style),
                Paragraph("Teacher", header_style),
                Paragraph("Date", header_style),
                Paragraph("Time", header_style),
                Paragraph("Event", header_style),
                Paragraph("Severity", header_style),
                Paragraph("Message", header_style),
            ]
        ]
        for event in events:
            row = ai_event_row(event)
            table_data.append([Paragraph(pdf_text(value), table_style) for value in row])

        table = LongTable(
            table_data,
            repeatRows=1,
            colWidths=[
                0.7 * inch,
                1.12 * inch,
                1.14 * inch,
                1.18 * inch,
                0.62 * inch,
                0.68 * inch,
                0.78 * inch,
                0.52 * inch,
                4.2 * inch,
            ],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f7a6d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 6.1),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dce3ed")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
                ]
            )
        )
        story.append(table)

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(
            document.pagesize[0] - document.rightMargin,
            0.2 * inch,
            f"Page {document.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return buffer.getvalue()


def build_attendance_pdf(records: list[Attendance], filters: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.4 * inch,
        leftMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Smart Classroom AI Monitoring V2", styles["Title"]),
        Paragraph("Attendance Report", styles["Heading2"]),
        Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]),
        Paragraph(f"Applied filters: {filter_summary(filters)}", styles["Normal"]),
        Spacer(1, 0.15 * inch),
    ]

    counts = attendance_counts(records)
    story.append(
        Paragraph(
            "Summary: "
            f"Total {counts['total']} | Present {counts['present']} | Late {counts['late']} | "
            f"Absent {counts['absent']} | Permission {counts['permission']}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    if not records:
        story.append(Paragraph("No attendance records match the selected filters.", styles["Normal"]))
    else:
        table_data = [
            ["Student", "Class", "Subject", "Teacher", "Date", "Time", "Status", "Source", "Recorded"]
        ]
        for record in records:
            row = attendance_row(record)
            table_data.append([row[0], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9]])

        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[0.8 * inch, 1.35 * inch, 1.35 * inch, 1.35 * inch, 0.8 * inch, 0.9 * inch, 0.65 * inch, 0.75 * inch, 0.95 * inch],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f7a6d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#dce3ed")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fb")]),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    return buffer.getvalue()
