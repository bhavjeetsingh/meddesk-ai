"""
CareFirst Medical Center - Prescription PDF Generator
Generate professional prescription PDFs with Indian medical format
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os


BRAND_BLUE = HexColor("#1a5276")
BRAND_LIGHT = HexColor("#2980b9")
GREY = HexColor("#7f8c8d")
LIGHT_GREY = HexColor("#ecf0f1")


def generate_prescription(
    patient_name: str,
    patient_age: str,
    patient_gender: str,
    doctor_name: str,
    doctor_qualification: str,
    registration_number: str,
    diagnosis: str,
    medications: list,
    instructions: str,
    follow_up: str,
    output_path: str = None,
) -> str:
    """Generate a professional prescription PDF"""

    if not output_path:
        os.makedirs("prescriptions", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = patient_name.replace(" ", "_").lower()
        output_path = f"prescriptions/prescription_{safe_name}_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=1.5*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'PrescriptionTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=BRAND_BLUE,
        alignment=TA_CENTER,
        spaceAfter=2*mm,
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=GREY,
        alignment=TA_CENTER,
        spaceAfter=4*mm,
    )

    section_style = ParagraphStyle(
        'Section',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=BRAND_BLUE,
        spaceBefore=4*mm,
        spaceAfter=2*mm,
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=2*mm,
    )

    med_style = ParagraphStyle(
        'Medicine',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        leftIndent=10,
        spaceAfter=1*mm,
    )

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=GREY,
        alignment=TA_CENTER,
    )

    elements = []

    # Header
    elements.append(Paragraph("CareFirst Medical Center", title_style))
    elements.append(Paragraph(
        "Sunshine Plaza, MG Road, Andheri West, Mumbai - 400058<br/>"
        "Phone: +91 98765 43210 | www.carefirstmedical.in",
        subtitle_style
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=BRAND_LIGHT))
    elements.append(Spacer(1, 3*mm))

    # Prescription title
    rx_style = ParagraphStyle('RX', parent=styles['Normal'], fontSize=14, textColor=BRAND_BLUE, alignment=TA_LEFT)
    elements.append(Paragraph("<b>R x</b>", rx_style))
    elements.append(Spacer(1, 3*mm))

    # Patient & Doctor info table
    date_str = datetime.now().strftime("%d %B %Y")
    info_data = [
        [Paragraph(f"<b>Patient:</b> {patient_name}", body_style),
         Paragraph(f"<b>Date:</b> {date_str}", body_style)],
        [Paragraph(f"<b>Age/Gender:</b> {patient_age} / {patient_gender}", body_style),
         Paragraph(f"<b>Dr. {doctor_name}</b>", body_style)],
        [Paragraph("", body_style),
         Paragraph(f"{doctor_qualification}", body_style)],
        [Paragraph("", body_style),
         Paragraph(f"Reg: {registration_number}", body_style)],
    ]

    info_table = Table(info_data, colWidths=[9*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY))

    # Diagnosis
    elements.append(Paragraph("<b>Diagnosis:</b>", section_style))
    elements.append(Paragraph(diagnosis, body_style))
    elements.append(Spacer(1, 2*mm))

    # Medications
    elements.append(Paragraph("<b>Prescription:</b>", section_style))
    for i, med in enumerate(medications, 1):
        if isinstance(med, dict):
            name = med.get("name", "")
            dosage = med.get("dosage", "")
            frequency = med.get("frequency", "")
            duration = med.get("duration", "")
            med_text = f"{i}. <b>{name}</b> — {dosage}, {frequency}, for {duration}"
        else:
            med_text = f"{i}. {med}"
        elements.append(Paragraph(med_text, med_style))
    elements.append(Spacer(1, 3*mm))

    # Instructions
    if instructions:
        elements.append(Paragraph("<b>Instructions:</b>", section_style))
        elements.append(Paragraph(instructions, body_style))

    # Follow-up
    if follow_up:
        elements.append(Spacer(1, 3*mm))
        elements.append(Paragraph(f"<b>Follow-up:</b> {follow_up}", body_style))

    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GREY))
    elements.append(Spacer(1, 3*mm))

    # Doctor signature
    sig_style = ParagraphStyle('Sig', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT)
    elements.append(Paragraph(f"<b>Dr. {doctor_name}</b>", sig_style))
    elements.append(Paragraph(f"{doctor_qualification}", sig_style))
    elements.append(Paragraph("CareFirst Medical Center", sig_style))

    elements.append(Spacer(1, 5*mm))
    elements.append(Paragraph(
        "This prescription is valid for 30 days from the date of issue.<br/>"
        "For emergencies, call 108 or visit the nearest hospital.<br/>"
        "GST 18% applicable on consultation fees.",
        footer_style
    ))

    # Build PDF
    doc.build(elements)
    return output_path
