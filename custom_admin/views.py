from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import json

from competition.models import EssayCompetition, Essay
from core.models import Feedback
from user.models import CustomUser
from .forms import EssayCompetitionForm, EssayForm, FeedbackForm, CustomUserForm

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO
import csv
from datetime import datetime

import os
from django.conf import settings
from competition.ml.linear_regression import EssayScorePredictor
from competition.models import Essay

# ========== HELPER FUNCTIONS ==========
def is_admin(user):
    """Check if user is staff or superuser"""
    return user.is_staff or user.is_superuser


# ========== PDF EXPORT VIEWS ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def export_essays_pdf(request):
    """Export essays to PDF with improved table formatting"""
    # Get filter parameters
    status = request.GET.get('status')
    competition_id = request.GET.get('competition')
    search = request.GET.get('search')
    
    # Base queryset
    essays = Essay.objects.select_related('user', 'competition').all().order_by('-submitted_at')
    
    # Apply filters
    if status:
        essays = essays.filter(status=status)
    if competition_id:
        essays = essays.filter(competition_id=competition_id)
    if search:
        essays = essays.filter(
            Q(title__icontains=search) | 
            Q(user__username__icontains=search)
        )
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), 
                           rightMargin=30, leftMargin=30,
                           topMargin=30, bottomMargin=30)
    
    # Container for elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=22,
        alignment=TA_CENTER,
        spaceAfter=15,
        textColor=colors.HexColor('#007bff'),
        fontName='Helvetica-Bold'
    )
    
    # Title
    title = Paragraph("Essays Report", title_style)
    elements.append(title)
    
    # Date
    date_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    date = Paragraph(date_text, styles['Normal'])
    elements.append(date)
    elements.append(Spacer(1, 15))
    
    # Filter info
    filter_info = "Filters: "
    if status:
        filter_info += f"Status: {status} | "
    if competition_id:
        comp = EssayCompetition.objects.get(id=competition_id)
        filter_info += f"Competition: {comp.title[:30]}... | "
    if search:
        filter_info += f"Search: {search} | "
    if filter_info == "Filters: ":
        filter_info += "All Essays"
    
    filter_para = Paragraph(filter_info, styles['Italic'])
    elements.append(filter_para)
    elements.append(Spacer(1, 15))
    
    # Summary stats - IMPROVED TABLE
    total = essays.count()
    accepted = essays.filter(status='accepted').count()
    rejected = essays.filter(status='rejected').count()
    pending = essays.filter(status='submitted').count()
    
    stats_data = [
        ['Total Essays', 'Accepted', 'Rejected', 'Pending'],
        [str(total), str(accepted), str(rejected), str(pending)]
    ]
    
    stats_table = Table(stats_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#dee2e6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(stats_table)
    elements.append(Spacer(1, 20))
    
    # Essays table
    if essays.exists():
        # Prepare table data
        table_data = [['#', 'Title', 'User', 'Competition', 'Status', 'Score', 'Date']]
        
        for idx, essay in enumerate(essays[:100], 1):
            # Clean text
            title_text = essay.title[:40] + ('...' if len(essay.title) > 40 else '')
            title_text = title_text.replace('\n', ' ').replace('\r', '')
            
            user_text = essay.user.username[:20]
            comp_text = essay.competition.title[:25] + ('...' if len(essay.competition.title) > 25 else '')
            
            status_text = essay.get_status_display()
            score_text = f"{essay.total_score:.1f}%" if essay.total_score else '-'
            date_text = essay.submitted_at.strftime('%Y-%m-%d') if essay.submitted_at else '-'
            
            table_data.append([
                str(idx),
                title_text,
                user_text,
                comp_text,
                status_text,
                score_text,
                date_text
            ])
        
        # Create table with optimized column widths
        col_widths = [0.4*inch, 2.2*inch, 1.2*inch, 1.8*inch, 0.9*inch, 0.9*inch, 1.0*inch]
        essay_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Table style with better formatting
        style = TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # S.No column
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Status column
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),  # Score column
            ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # Date column
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ffffff')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.HexColor('#ffffff')]),
        ])
        
        # Color code status rows
        for i, essay in enumerate(essays[:100], 1):
            if essay.status == 'accepted':
                style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#d4edda'))
                style.add('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#155724'))
            elif essay.status == 'rejected':
                style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8d7da'))
                style.add('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#721c24'))
            elif essay.status == 'submitted':
                style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#d1ecf1'))
                style.add('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#0c5460'))
        
        essay_table.setStyle(style)
        elements.append(essay_table)
        
        # Add note if limited
        if essays.count() > 100:
            note = Paragraph(f"* Showing first 100 essays out of {essays.count()} total", 
                           styles['Italic'])
            elements.append(Spacer(1, 10))
            elements.append(note)
    else:
        elements.append(Paragraph("No essays found matching the criteria.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create response
    response = HttpResponse(content_type='application/pdf')
    filename = f"essays_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def export_essay_detail_pdf(request, pk):
    """Export single essay detail to PDF with proper paragraph formatting"""
    essay = get_object_or_404(Essay, pk=pk)
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=50, leftMargin=50,
                           topMargin=50, bottomMargin=50)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#007bff'),
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#343a40'),
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceBefore=0,
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    content_style = ParagraphStyle(
        'ContentStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,  # Changed to justify for better readability
        spaceBefore=0,
        spaceAfter=12,
        leading=16,
        fontName='Helvetica',
        firstLineIndent=20,
    )
    
    # Title
    title_text = essay.title.replace('\n', ' ').replace('\r', '')
    title = Paragraph(f"Essay: {title_text}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Essay metadata - IMPROVED TABLE FORMATTING
    elements.append(Paragraph("Essay Information", heading_style))
    
    metadata = [
        ['User:', essay.user.username],
        ['Email:', essay.user.email],
        ['Competition:', essay.competition.title],
        ['Status:', essay.get_status_display()],
        ['Submitted:', essay.submitted_at.strftime('%B %d, %Y at %I:%M %p') if essay.submitted_at else '-'],
        ['Evaluated:', essay.evaluated_at.strftime('%B %d, %Y at %I:%M %p') if essay.evaluated_at else '-'],
    ]
    
    if essay.reviewed_by:
        metadata.append(['Reviewed by:', essay.reviewed_by.username])
    
    meta_table = Table(metadata, colWidths=[1.5*inch, 4*inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 20))
    
    # Scores - IMPROVED TABLE FORMATTING
    if essay.total_score:
        elements.append(Paragraph("Evaluation Scores", heading_style))
        
        scores_data = [
            ['Criteria', 'Score'],
            ['Title Relevance', f"{essay.title_relevance_score:.1f}%"],
            ['Cohesion', f"{essay.cohesion_score:.1f}%"],
            ['Grammar', f"{essay.grammar_score:.1f}%"],
            ['Structure', f"{essay.structure_score:.1f}%"],
            ['Total', f"{essay.total_score:.1f}%"],
        ]
        
        scores_table = Table(scores_data, colWidths=[3*inch, 2*inch])
        scores_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007bff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f8f9fa')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(scores_table)
        elements.append(Spacer(1, 20))
    
    # Essay content - COMPLETE CHARACTER CLEANING
    elements.append(Paragraph("Essay Content", heading_style))
    elements.append(Spacer(1, 10))
    
    if essay.content:
        # Get raw content
        content = essay.content
        
        # COMPREHENSIVE CHARACTER REPLACEMENT
        # All possible problematic Unicode characters
        unicode_replacements = {
            # Black squares and bullets
            '■': '', '●': '', '•': '', '▪': '', '▫': '', '◼': '', '◻': '', '◾': '', '◽': '',
            '□': '', '◆': '', '◇': '', '►': '', '◄': '', '▼': '', '▲': '', '◀': '', '▶': '',
            '◊': '', '○': '', '◌': '', '◍': '', '◎': '', '●': '', '◐': '', '◑': '', '◒': '',
            '◓': '', '◔': '', '◕': '', '◖': '', '◗': '', '◘': '', '◙': '', '◚': '', '◛': '',
            '◜': '', '◝': '', '◞': '', '◟': '', '◠': '', '◡': '', '◢': '', '◣': '', '◤': '',
            '◥': '', '◦': '', '◧': '', '◨': '', '◩': '', '◪': '', '◫': '', '◬': '', '◭': '',
            '◮': '', '◯': '', '◰': '', '◱': '', '◲': '', '◳': '', '◴': '', '◵': '', '◶': '',
            '◷': '', '◸': '', '◹': '', '◺': '', '◻': '', '◼': '', '◽': '', '◾': '', '◿': '',
            
            # Lock icons and specials
            '🔒': '', '🔓': '', '🔏': '', '🔐': '', '🔑': '', '🗝️': '',
            
            # Other common problematic characters
            '\u200b': '',  # Zero-width space
            '\u200c': '',  # Zero-width non-joiner
            '\u200d': '',  # Zero-width joiner
            '\ufeff': '',  # Zero-width no-break space
            '\u00a0': ' ', # Non-breaking space to normal space
        }
        
        # Apply Unicode replacements
        for char, replacement in unicode_replacements.items():
            content = content.replace(char, replacement)
        
        # Replace HTML entities
        html_entities = {
            '&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>',
            '&quot;': '"', '&#39;': "'", '&apos;': "'", '&ndash;': '-',
            '&mdash;': '--', '&hellip;': '...', '&bull;': '•',
            '&rsquo;': "'", '&lsquo;': "'", '&rdquo;': '"', '&ldquo;': '"',
        }
        
        for entity, replacement in html_entities.items():
            content = content.replace(entity, replacement)
        
        # Normalize line endings
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove multiple spaces
        content = ' '.join(content.split())
        
        # Split into sentences (for better paragraph formation)
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        # Group sentences into paragraphs (3-4 sentences per paragraph)
        paragraphs = []
        current_paragraph = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                current_paragraph.append(sentence)
                if len(current_paragraph) >= 3:  # 3 sentences per paragraph
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
        
        # Add remaining sentences
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        # If no paragraphs were created, use the whole content
        if not paragraphs and content.strip():
            paragraphs = [content.strip()]
        
        # Add paragraphs to PDF
        for para in paragraphs:
            if para.strip():
                # Clean the paragraph
                clean_para = para.strip()
                # Remove any remaining non-ASCII characters
                clean_para = ''.join(char if ord(char) < 128 else '?' for char in clean_para)
                p = Paragraph(clean_para, content_style)
                elements.append(p)
    else:
        elements.append(Paragraph("No content available.", normal_style))
    
    # Admin notes
    if essay.admin_notes:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Admin Notes", heading_style))
        elements.append(Spacer(1, 10))
        
        notes = essay.admin_notes
        # Clean admin notes too
        for char, replacement in unicode_replacements.items():
            notes = notes.replace(char, replacement)
        notes = notes.replace('\n', '<br/>')
        notes_para = Paragraph(notes, normal_style)
        elements.append(notes_para)
    
    # Build PDF
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    clean_title = ''.join(c for c in essay.title[:30] if c.isalnum() or c in ' -_').strip()
    filename = f"essay_{essay.id}_{clean_title}_{datetime.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)
    
    return response

# ========== CSV EXPORT VIEW ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def export_essays_csv(request):
    """Export essays to CSV"""
    # Get filter parameters
    status = request.GET.get('status')
    competition_id = request.GET.get('competition')
    search = request.GET.get('search')
    
    # Base queryset
    essays = Essay.objects.select_related('user', 'competition').all().order_by('-submitted_at')
    
    # Apply filters
    if status:
        essays = essays.filter(status=status)
    if competition_id:
        essays = essays.filter(competition_id=competition_id)
    if search:
        essays = essays.filter(
            Q(title__icontains=search) | 
            Q(user__username__icontains=search)
        )
    
    response = HttpResponse(content_type='text/csv')
    filename = f"essays_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow([
        'ID', 'Title', 'User', 'User Email', 'Competition', 
        'Status', 'Score', 'Title Relevance', 'Cohesion', 
        'Grammar', 'Structure', 'Submitted Date', 'Evaluated Date',
        'Word Count', 'Language', 'Reviewed By'
    ])
    
    # Write data
    for essay in essays:
        # Clean text data for CSV
        title = essay.title.replace('\n', ' ').replace('\r', ' ').replace(',', ' ')
        username = essay.user.username.replace('\n', ' ').replace('\r', ' ').replace(',', ' ')
        email = essay.user.email.replace('\n', ' ').replace('\r', ' ').replace(',', ' ')
        competition_title = essay.competition.title.replace('\n', ' ').replace('\r', ' ').replace(',', ' ')
        
        writer.writerow([
            essay.id,
            title,
            username,
            email,
            competition_title,
            essay.status,
            f"{essay.total_score:.1f}" if essay.total_score else '',
            f"{essay.title_relevance_score:.1f}" if essay.title_relevance_score else '',
            f"{essay.cohesion_score:.1f}" if essay.cohesion_score else '',
            f"{essay.grammar_score:.1f}" if essay.grammar_score else '',
            f"{essay.structure_score:.1f}" if essay.structure_score else '',
            essay.submitted_at.strftime('%Y-%m-%d %H:%M') if essay.submitted_at else '',
            essay.evaluated_at.strftime('%Y-%m-%d %H:%M') if essay.evaluated_at else '',
            len(essay.content.split()),
            essay.language,
            essay.reviewed_by.username if essay.reviewed_by else ''
        ])
    
    return response


# ========== AUTHENTICATION VIEWS ==========
def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('custom_admin:dashboard')
        else:
            messages.error(request, 'Invalid credentials or not an admin user')
    
    return render(request, 'custom_admin/login.html')

def admin_logout(request):
    logout(request)
    return redirect('custom_admin:login')

def admin_root(request):
    """Redirect root to login if not authenticated, otherwise to dashboard"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('custom_admin:dashboard')
    else:
        return redirect('custom_admin:login')


# ========== DASHBOARD ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def dashboard(request):
    # Basic stats
    total_users = CustomUser.objects.count()
    total_competitions = EssayCompetition.objects.filter(is_active=True).count()
    total_essays = Essay.objects.count()
    accepted_essays = Essay.objects.filter(status='accepted').count()
    
    # New users today
    today = timezone.now().date()
    new_users_today = CustomUser.objects.filter(created_at__date=today).count()
    
    # Pending essays
    pending_essays = Essay.objects.filter(status='submitted').count()
    
    # Upcoming competitions
    upcoming_competitions = EssayCompetition.objects.filter(
        deadline__gt=timezone.now(),
        is_active=True
    ).count()
    
    # Acceptance rate
    acceptance_rate = (accepted_essays / total_essays * 100) if total_essays > 0 else 0
    
    # Weekly submissions
    daily_submissions = []
    daily_labels = []
    
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        count = Essay.objects.filter(
            submitted_at__date=day.date()
        ).count()
        daily_submissions.append(count)
        daily_labels.append(day.strftime('%a'))
    
    # Competition stats
    active_comps = EssayCompetition.objects.filter(
        is_active=True, 
        deadline__gt=timezone.now()
    ).count()
    expired_comps = EssayCompetition.objects.filter(
        deadline__lt=timezone.now()
    ).count()
    upcoming_comps = EssayCompetition.objects.filter(
        is_active=True,
        deadline__gt=timezone.now() + timedelta(days=7)
    ).count()
    
    # Recent essays
    recent_essays = Essay.objects.select_related('user', 'competition').order_by('-submitted_at')[:5]
    
    # Recent feedback
    recent_feedback = Feedback.objects.order_by('-created_at')[:5]
    
    # Top users
    top_users = CustomUser.objects.annotate(
        essay_count=Count('essays'),
        accepted_count=Count('essays', filter=Q(essays__status='accepted')),
        avg_score=Avg('essays__total_score', filter=Q(essays__status='accepted'))
    ).filter(essay_count__gt=0).order_by('-accepted_count')[:5]
    
    for user in top_users:
        if user.essay_count > 0:
            user.success_rate = (user.accepted_count / user.essay_count) * 100
        else:
            user.success_rate = 0
    
    context = {
        'total_users': total_users,
        'total_competitions': total_competitions,
        'total_essays': total_essays,
        'accepted_essays': accepted_essays,
        'new_users_today': new_users_today,
        'pending_essays': pending_essays,
        'upcoming_competitions': upcoming_competitions,
        'acceptance_rate': round(acceptance_rate, 1),
        'weekly_labels': json.dumps(daily_labels),
        'weekly_data': json.dumps(daily_submissions),
        'competition_stats': json.dumps([active_comps, expired_comps, upcoming_comps]),
        'recent_essays': recent_essays,
        'recent_feedback': recent_feedback,
        'top_users': top_users,
        'now': timezone.now(),
    }
    
    return render(request, 'custom_admin/dashboard.html', context)


# ========== COMPETITION CRUD ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def competitions(request):
    competitions_list = EssayCompetition.objects.annotate(
        essay_count=Count('essays'),
        accepted_count=Count('essays', filter=Q(essays__status='accepted')),
        avg_score=Avg('essays__total_score', filter=Q(essays__status='accepted'))
    ).order_by('-deadline')
    
    context = {
        'competitions': competitions_list,
        'now': timezone.now(),
    }
    
    return render(request, 'custom_admin/competitions.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def competition_add(request):
    if request.method == 'POST':
        form = EssayCompetitionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Competition added successfully!')
            return redirect('custom_admin:competitions')
    else:
        form = EssayCompetitionForm()
    
    return render(request, 'custom_admin/competition_form.html', {
        'form': form,
        'title': 'Add Competition'
    })

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def competition_edit(request, pk):
    competition = get_object_or_404(EssayCompetition, pk=pk)
    if request.method == 'POST':
        form = EssayCompetitionForm(request.POST, instance=competition)
        if form.is_valid():
            form.save()
            messages.success(request, 'Competition updated successfully!')
            return redirect('custom_admin:competitions')
    else:
        form = EssayCompetitionForm(instance=competition)
    
    return render(request, 'custom_admin/competition_form.html', {
        'form': form,
        'title': 'Edit Competition'
    })

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def competition_delete(request, pk):
    competition = get_object_or_404(EssayCompetition, pk=pk)
    if request.method == 'POST':
        competition.delete()
        messages.success(request, 'Competition deleted successfully!')
        return redirect('custom_admin:competitions')
    
    return render(request, 'custom_admin/confirm_delete.html', {
        'object': competition,
        'type': 'competition'
    })


# ========== ESSAY CRUD ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def essays(request):
    essays_list = Essay.objects.select_related('user', 'competition').all().order_by('-submitted_at')
    
    status = request.GET.get('status')
    competition_id = request.GET.get('competition')
    search = request.GET.get('search')
    
    if status:
        essays_list = essays_list.filter(status=status)
    if competition_id:
        essays_list = essays_list.filter(competition_id=competition_id)
    if search:
        essays_list = essays_list.filter(
            Q(title__icontains=search) | 
            Q(user__username__icontains=search) |
            Q(content__icontains=search)
        )
    
    paginator = Paginator(essays_list, 20)
    page_number = request.GET.get('page')
    essays_page = paginator.get_page(page_number)
    
    competitions = EssayCompetition.objects.all()
    
    context = {
        'essays': essays_page,
        'competitions': competitions,
    }
    
    return render(request, 'custom_admin/essays.html', context)

import re

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def essay_detail(request, pk):
    essay = get_object_or_404(Essay, pk=pk)
    
    # ===== FIX THE CONTENT HERE =====
    if essay.content:
        # Get the raw content
        content = essay.content
        
        # Define all problematic characters to replace
        # Black squares, bullets, circles, etc.
        problematic_chars = {
            '■': '\n',    # Replace black square with newline
            '●': '\n',    # Replace black circle with newline
            '•': '\n',    # Replace bullet with newline
            '▪': '\n',    # Replace small square with newline
            '▫': '\n',    # Replace white square with newline
            '◼': '\n',    # Replace medium square with newline
            '□': '\n',    # Replace white square with newline
            '◆': '\n',    # Replace diamond with newline
            '◇': '\n',    # Replace white diamond with newline
            '►': '\n',    # Replace arrow with newline
            '◄': '\n',    # Replace arrow with newline
            '▼': '\n',    # Replace triangle with newline
            '▲': '\n',    # Replace triangle with newline
        }
        
        # Replace each problematic character
        for char, replacement in problematic_chars.items():
            content = content.replace(char, replacement)
        
        # Replace multiple newlines with double newline
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Split into paragraphs
        raw_paragraphs = content.split('\n')
        
        # Clean each paragraph
        cleaned_paragraphs = []
        current_para = []
        
        for line in raw_paragraphs:
            line = line.strip()
            if line:
                current_para.append(line)
            else:
                if current_para:
                    cleaned_paragraphs.append(' '.join(current_para))
                    current_para = []
        
        # Add the last paragraph
        if current_para:
            cleaned_paragraphs.append(' '.join(current_para))
        
        # If no paragraphs found (maybe content has no newlines), create one
        if not cleaned_paragraphs and content.strip():
            cleaned_paragraphs = [content.strip()]
        
        # Add to essay object
        essay.paragraphs = cleaned_paragraphs
    else:
        essay.paragraphs = []
    
    return render(request, 'custom_admin/essay_detail.html', {'essay': essay})

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def essay_edit(request, pk):
    essay = get_object_or_404(Essay, pk=pk)
    if request.method == 'POST':
        form = EssayForm(request.POST, instance=essay)
        if form.is_valid():
            form.save()
            messages.success(request, 'Essay updated successfully!')
            return redirect('custom_admin:essays')
    else:
        form = EssayForm(instance=essay)
    
    return render(request, 'custom_admin/essay_form.html', {
        'form': form,
        'title': 'Edit Essay'
    })

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def essay_delete(request, pk):
    essay = get_object_or_404(Essay, pk=pk)
    if request.method == 'POST':
        essay.delete()
        messages.success(request, 'Essay deleted successfully!')
        return redirect('custom_admin:essays')
    
    return render(request, 'custom_admin/confirm_delete.html', {
        'object': essay,
        'type': 'essay'
    })

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def essay_review(request, pk):
    essay = get_object_or_404(Essay, pk=pk)
    from competition.evaluator import EssayEvaluator
    
    if request.method == 'POST':
        status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes')
        
        if status == 'accepted':
            try:
                evaluator = EssayEvaluator(
                    min_words=essay.competition.min_words,
                    max_words=essay.competition.max_words
                )
                scores = evaluator.evaluate(essay.title, essay.content)
                
                essay.title_relevance_score = scores['title_relevance_score']
                essay.cohesion_score = scores['cohesion_score']
                essay.grammar_score = scores['grammar_score']
                essay.structure_score = scores['structure_score']
                essay.total_score = scores['total_score']
            except Exception as e:
                messages.error(request, f'Error evaluating essay: {str(e)}')
        
        essay.status = status
        essay.admin_notes = admin_notes
        essay.reviewed_by = request.user
        essay.evaluated_at = timezone.now()
        essay.save()
        
        messages.success(request, f'Essay {status} successfully!')
        return redirect('custom_admin:essays')
    
    return render(request, 'custom_admin/essay_review.html', {'essay': essay})


# ========== USER CRUD ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def users(request):
    users_list = CustomUser.objects.annotate(
        essay_count=Count('essays'),
        accepted_count=Count('essays', filter=Q(essays__status='accepted')),
        avg_score=Avg('essays__total_score', filter=Q(essays__status='accepted'))
    ).order_by('-created_at')
    
    total_users = users_list.count()
    active_users = users_list.filter(last_login__date=timezone.now().date()).count()
    users_with_essays = users_list.filter(essay_count__gt=0).count()
    new_users = users_list.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
    
    paginator = Paginator(users_list, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'total_users': total_users,
        'active_users': active_users,
        'users_with_essays': users_with_essays,
        'new_users': new_users,
    }
    
    return render(request, 'custom_admin/users.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def user_detail(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    user_essays = Essay.objects.filter(user=user).select_related('competition')
    
    context = {
        'user': user,
        'essays': user_essays,
    }
    return render(request, 'custom_admin/user_detail.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    old_doc_path = None
    
    # Store the old document path before any changes
    if user.identity_doc:
        old_doc_path = user.identity_doc.path
    
    if request.method == 'POST':
        # Create form with both POST and FILES data
        form = CustomUserForm(request.POST, request.FILES, instance=user)
        
        if form.is_valid():
            # Save the form first - this handles the new file upload
            updated_user = form.save()
            
            # After successful save, delete the old file if it was replaced
            if 'identity_doc' in request.FILES and old_doc_path:
                try:
                    # Check if the old file exists and is different from the new one
                    import os
                    if os.path.exists(old_doc_path):
                        os.remove(old_doc_path)
                except Exception as e:
                    # Log the error but don't stop the process
                    print(f"Error deleting old file: {e}")
            
            messages.success(request, 'User updated successfully!')
            return redirect('custom_admin:users')
        else:
            # Print form errors for debugging
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserForm(instance=user)
    
    return render(request, 'custom_admin/user_form.html', {
        'form': form,
        'title': 'Edit User'
    })

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def user_delete(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        # Delete the document file if exists
        if user.identity_doc:
            user.identity_doc.delete(save=False)
        user.delete()
        messages.success(request, 'User deleted successfully!')
        return redirect('custom_admin:users')
    
    return render(request, 'custom_admin/confirm_delete.html', {
        'object': user,
        'type': 'user'
    })

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def user_add(request):
    if request.method == 'POST':
        # Create form with both POST and FILES data
        form = CustomUserForm(request.POST, request.FILES)
        
        if form.is_valid():
            # Save the form - this handles the file upload automatically
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            messages.success(request, 'User added successfully!')
            return redirect('custom_admin:users')
        else:
            print("Form errors:", form.errors)
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserForm()
    
    return render(request, 'custom_admin/user_form.html', {
        'form': form,
        'title': 'Add User'
    })

# ========== FEEDBACK CRUD ==========
@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def feedback(request):
    feedback_list = Feedback.objects.all().order_by('-created_at')
    
    # Add statistics
    pending_count = Feedback.objects.filter(status='pending').count()
    approved_count = Feedback.objects.filter(status='approved').count()
    featured_count = Feedback.objects.filter(show_on_homepage=True).count()
    
    if request.method == 'POST':
        feedback_id = request.POST.get('feedback_id')
        action = request.POST.get('action')
        
        if feedback_id and action:
            feedback_item = get_object_or_404(Feedback, id=feedback_id)
            if action == 'approve':
                feedback_item.status = 'approved'
                messages.success(request, f'Feedback from {feedback_item.name} approved')
            elif action == 'reject':
                feedback_item.status = 'rejected'
                feedback_item.show_on_homepage = False
                messages.success(request, f'Feedback from {feedback_item.name} rejected')
            elif action == 'feature':
                feedback_item.show_on_homepage = True
                messages.success(request, f'Feedback from {feedback_item.name} featured')
            feedback_item.save()
            return redirect('custom_admin:feedback')
    
    status_filter = request.GET.get('status')
    if status_filter:
        feedback_list = feedback_list.filter(status=status_filter)
    
    paginator = Paginator(feedback_list, 10)
    page_number = request.GET.get('page')
    feedback_page = paginator.get_page(page_number)
    
    context = {
        'feedback_list': feedback_page,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'featured_count': featured_count,
    }
    
    return render(request, 'custom_admin/feedback.html', context)

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def feedback_detail(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    return render(request, 'custom_admin/feedback_detail.html', {'feedback': feedback})

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def feedback_reply(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    
    if request.method == 'POST':
        reply = request.POST.get('admin_reply')
        if reply:
            feedback.admin_reply = reply
            feedback.replied_at = timezone.now()
            feedback.save()
            messages.success(request, f'Reply sent to {feedback.name} successfully!')
        else:
            messages.error(request, 'Reply cannot be empty')
        
        return redirect('custom_admin:feedback')
    
    return render(request, 'custom_admin/feedback_reply.html', {'feedback': feedback})


# ========== MACHINE LEARNING VIEWS ==========

@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def ml_dashboard(request):
    """Admin dashboard for machine learning"""
    
    predictor = EssayScorePredictor()
    
    # Check if model exists
    model_files = []
    models_dir = os.path.join(settings.BASE_DIR, 'competition', 'ml', 'models')
    if os.path.exists(models_dir):
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib')]
    
    # Get essay statistics
    total_essays = Essay.objects.filter(status='accepted').count()
    
    # Try to load latest model to check if trained
    model_trained = False
    if model_files:
        try:
            latest_model = sorted(model_files)[-1].replace('.joblib', '')
            predictor.load_model(latest_model)
            model_trained = predictor.model is not None
        except:
            pass
    
    context = {
        'page_title': 'ML Dashboard',
        'model_trained': model_trained,
        'model_files': model_files,
        'total_essays': total_essays,
        'feature_names': predictor.feature_names,
    }
    
    return render(request, 'custom_admin/ml_dashboard.html', context)


@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def train_model(request):
    """Train the ML model"""
    if request.method == 'POST':
        
        predictor = EssayScorePredictor()
        
        # Get all accepted essays
        essays = Essay.objects.filter(status='accepted', total_score__gt=0)
        
        if essays.count() < 5:
            messages.error(request, f'Need at least 5 essays to train. Found {essays.count()}')
            return redirect('custom_admin:ml_dashboard')
        
        # Train the model
        results = predictor.train(essays)
        
        if results['success']:
            # Save the model
            model_path = predictor.save_model()
            
            # Show results
            messages.success(
                request, 
                f'✅ Model trained successfully!\n'
                f'• Total essays: {results["total_samples"]}\n'
                f'• Train R²: {results["metrics"]["train"]["r2"]:.3f}\n'
                f'• Test R²: {results["metrics"]["test"]["r2"]:.3f}'
            )
            
            # Store results in session to display
            request.session['train_results'] = {
                'metrics': results['metrics'],
                'feature_importance': results['feature_importance'],
                'total_samples': results['total_samples']
            }
        else:
            messages.error(request, results['message'])
        
        return redirect('custom_admin:ml_dashboard')
    
    return redirect('custom_admin:ml_dashboard')


@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def view_model_results(request):
    """View results of the last training"""
    results = request.session.get('train_results')
    
    if not results:
        messages.info(request, 'No training results found. Train a model first.')
        return redirect('custom_admin:ml_dashboard')
    
    context = {
        'page_title': 'Model Training Results',
        'metrics': results['metrics'],
        'feature_importance': results['feature_importance'],
        'total_samples': results['total_samples'],
    }
    
    return render(request, 'custom_admin/model_results.html', context)


@login_required(login_url='custom_admin:login')
@user_passes_test(is_admin, login_url='custom_admin:login')
def predict_essay(request, pk):
    """Predict score for a specific essay"""
    
    essay = get_object_or_404(Essay, pk=pk)
    predictor = EssayScorePredictor()
    
    # Try to load the latest model
    models_dir = os.path.join(settings.BASE_DIR, 'competition', 'ml', 'models')
    if os.path.exists(models_dir):
        model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib')]
        if model_files:
            latest_model = sorted(model_files)[-1].replace('.joblib', '')
            try:
                predictor.load_model(latest_model)
            except:
                pass
    
    if predictor.model is None:
        messages.error(request, 'No trained model found. Train a model first.')
        return redirect('custom_admin:ml_dashboard')
    
    try:
        prediction = predictor.predict(essay)
        
        context = {
            'essay': essay,
            'prediction': prediction,
            'actual_score': essay.total_score if essay.status == 'accepted' else None,
        }
        return render(request, 'custom_admin/prediction_result.html', context)
    except Exception as e:
        messages.error(request, f'Error making prediction: {str(e)}')
        return redirect('custom_admin:ml_dashboard')

