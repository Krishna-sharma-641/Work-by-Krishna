# pdf_export.py
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_pdf(schedule, subjects=None, user_name="", filename="study_schedule.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(f"Smart Study Schedule – {user_name or ''}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3*inch))

    data = [["Day", "Time", "Subject", "Duration"]]
    for day, sessions in schedule.items():
        if sessions:
            for s in sessions:
                data.append([day, f"{s['start'].strftime('%H:%M')} - {s['end'].strftime('%H:%M')}", s['subject'], f"{int(s['duration'])} min"])
        else:
            data.append([day, "No sessions", "-", "-"])

    table = Table(data, colWidths=[1.5*inch, 2*inch, 2*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('ALIGN',(0,0),(-1,-1),'CENTER'),
        ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,0),14),
        ('BOTTOMPADDING',(0,0),(-1,0),12),
        ('BACKGROUND',(0,1),(-1,-1),colors.beige),
        ('GRID',(0,0),(-1,-1),0.5,colors.black),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.4*inch))

    if subjects:
        story.append(Paragraph("Summary (Goal vs Difficulty/Priority)", styles['Heading2']))
        data2 = [["Subject","Difficulty","Priority","Goal (hrs)"]]
        for s in subjects:
            data2.append([s["name"], s["difficulty"], s["priority"], s["goal_hours"]])
        table2 = Table(data2, colWidths=[2*inch,1*inch,1*inch,1.5*inch])
        table2.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.black)]))
        story.append(table2)

    doc.build(story)
    return filename
