# competition/reports.py
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from .models import Essay
import io

def generate_essay_pdf(essay_id):
    """Generate PDF report for a single essay"""
    essay = Essay.objects.get(id=essay_id)
    
    # Create a buffer for the PDF
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6,
        textColor=colors.HexColor('#003893')  # Nepal blue
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph(f"Essay Report: {essay.title}", title_style))
    story.append(Spacer(1, 12))
    
    # Competition Info
    story.append(Paragraph("Competition Information", heading_style))
    info_data = [
        ["Competition:", essay.competition.title],
        ["Deadline:", essay.competition.deadline.strftime("%B %d, %Y")],
        ["Submitted by:", essay.user.get_full_name() or essay.user.username],
        ["Submitted on:", essay.submitted_at.strftime("%B %d, %Y %I:%M %p") if essay.submitted_at else "N/A"],
        ["Status:", essay.get_status_display()],
        ["Word Count:", str(essay.word_count)],
        ["Language:", essay.language.upper()],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Evaluation Scores
    if essay.status == 'accepted':
        story.append(Paragraph("Evaluation Scores", heading_style))
        scores_data = [
            ["Criteria", "Score (Out of 100)", "Weight", "Weighted Score"],
            ["Title-Content Relevance", f"{essay.title_relevance_score:.1f}", "30%", f"{essay.title_relevance_score * 0.3:.1f}"],
            ["Cohesion & Flow", f"{essay.cohesion_score:.1f}", "30%", f"{essay.cohesion_score * 0.3:.1f}"],
            ["Grammar & Language", f"{essay.grammar_score:.1f}", "25%", f"{essay.grammar_score * 0.25:.1f}"],
            ["Structure & Length", f"{essay.structure_score:.1f}", "15%", f"{essay.structure_score * 0.15:.1f}"],
            ["", "", "Total:", f"{essay.total_score:.1f}"]
        ]
        
        scores_table = Table(scores_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch])
        scores_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('LINEBELOW', (0, -1), (-2, -1), 1, colors.black),
            ('LINEABOVE', (-1, -1), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003893')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-2, -1), colors.HexColor('#f8f9fa')),
            ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
        ]))
        story.append(scores_table)
        story.append(Spacer(1, 20))
        
        # Grade interpretation
        grade = "A+" if essay.total_score >= 90 else \
                "A" if essay.total_score >= 80 else \
                "B+" if essay.total_score >= 70 else \
                "B" if essay.total_score >= 60 else \
                "C" if essay.total_score >= 50 else "D"
        
        grade_text = f"Overall Grade: <b>{grade}</b> ({essay.total_score:.1f}/100)"
        story.append(Paragraph(grade_text, normal_style))
        story.append(Spacer(1, 20))
    
    # Essay Content
    story.append(Paragraph("Essay Content", heading_style))
    
    # Clean HTML tags for PDF
    import re
    clean_content = re.sub(r'<[^>]+>', '', essay.content)
    
    # Split into paragraphs for better formatting
    paragraphs = clean_content.split('\n\n')
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para.strip().replace('\n', '<br/>'), normal_style))
            story.append(Spacer(1, 6))
    
    # Admin Notes (if any)
    if essay.admin_notes:
        story.append(Paragraph("Admin Notes", heading_style))
        story.append(Paragraph(essay.admin_notes, normal_style))
    
    # Footer
    story.append(Spacer(1, 20))
    footer_text = f"Report generated on {timezone.now().strftime('%B %d, %Y %I:%M %p')} | Nibandha Nakshatra"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1  # Center
    )))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

def generate_competition_report(competition_id):
    """Generate PDF report for entire competition"""
    from .models import EssayCompetition
    from django.db.models import Count, Avg, Max, Min
    
    competition = EssayCompetition.objects.get(id=competition_id)
    essays = Essay.objects.filter(
        competition=competition,
        status='accepted'
    ).order_by('-total_score')
    
    # Create a buffer for the PDF
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor('#003893')
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph(f"Competition Report: {competition.title}", title_style))
    story.append(Spacer(1, 20))
    
    # Competition Statistics
    story.append(Paragraph("Competition Statistics", styles['Heading2']))
    
    stats = essays.aggregate(
        total=Count('id'),
        avg_score=Avg('total_score'),
        max_score=Max('total_score'),
        min_score=Min('total_score'),
        avg_words=Avg('stored_word_count')
    )
    
    stats_data = [
        ["Total Submissions:", str(stats['total'] or 0)],
        ["Average Score:", f"{stats['avg_score'] or 0:.1f}"],
        ["Highest Score:", f"{stats['max_score'] or 0:.1f}"],
        ["Lowest Score:", f"{stats['min_score'] or 0:.1f}"],
        ["Average Word Count:", f"{stats['avg_words'] or 0:.0f}"],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 30))
    
    # Leaderboard
    story.append(Paragraph("Top Performers", styles['Heading2']))
    
    # Table headers
    leaderboard_data = [["Rank", "Participant", "Essay Title", "Total Score"]]
    
    # Add top 10 essays
    for i, essay in enumerate(essays[:10], 1):
        leaderboard_data.append([
            str(i),
            essay.user.get_full_name() or essay.user.username,
            essay.title[:30] + "..." if len(essay.title) > 30 else essay.title,
            f"{essay.total_score:.1f}"
        ])
    
    leaderboard_table = Table(leaderboard_data, colWidths=[0.5*inch, 1.5*inch, 3*inch, 1*inch])
    leaderboard_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003893')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    story.append(leaderboard_table)
    
    # Footer
    story.append(Spacer(1, 30))
    footer_text = f"Report generated on {timezone.now().strftime('%B %d, %Y %I:%M %p')} | Nibandha Nakshatra"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=1
    )))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

