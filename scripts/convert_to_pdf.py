import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Flowable
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
import os

# Color Palette (Professional, Sophisticated)
COLOR_PRIMARY = colors.HexColor("#1A1B3D")      # Deep Navy
COLOR_ACCENT = colors.HexColor("#6B4CE6")       # Royal Purple
COLOR_ACCENT_DARK = colors.HexColor("#4A35A8")  # Dark Purple
COLOR_TEXT = colors.HexColor("#2D2D44")         # Charcoal
COLOR_MUTED = colors.HexColor("#71717A")        # Cool Gray
COLOR_LIGHT_BG = colors.HexColor("#F7F7FB")     # Subtle Lavender
COLOR_BUY = colors.HexColor("#059669")          # Forest Green
COLOR_SELL = colors.HexColor("#DC2626")         # Deep Red
COLOR_HOLD = colors.HexColor("#D97706")         # Amber
COLOR_NEUTRAL = colors.HexColor("#52525B")      # Zinc

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 0.75 * inch


class BookmarkAction(Flowable):
    """Custom flowable to add bookmarks to PDF outline."""
    def __init__(self, title, key, level=0):
        Flowable.__init__(self)
        self.title = title
        self.key = key
        self.level = level

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        self.canv.bookmarkPage(self.key)
        self.canv.addOutlineEntry(self.title, self.key, level=self.level)


def get_signal_color(signal_text):
    """Determine color based on signal/rating text."""
    s = str(signal_text).upper()
    if any(x in s for x in ["BUY", "PRIORITY", "STRONG", "EXCELLENT", "HIGH"]):
        return COLOR_BUY
    if any(x in s for x in ["SELL", "AVOID", "WEAK", "POOR", "LOW"]):
        return COLOR_SELL
    if any(x in s for x in ["HOLD", "NEUTRAL", "MODERATE", "MEDIUM", "INVESTIGATE"]):
        return COLOR_HOLD
    return COLOR_NEUTRAL


def format_field_name(field_name):
    """Convert snake_case to Title Case."""
    return field_name.replace("_", " ").title()


class PDFTemplate:
    """Custom template for adding headers, footers, and watermarks."""
    
    def __init__(self, company_name, logo_path=None, watermark_path=None):
        self.company_name = company_name
        self.logo_path = logo_path
        self.watermark_path = watermark_path or logo_path
        self.watermark_opacity = 0.06
        
    def __call__(self, canvas, doc):
        """Called for each page."""
        canvas.saveState()
        
        # Watermark (on content pages only, not title page)
        if self.watermark_path and os.path.exists(self.watermark_path):
            try:
                img = Image.open(self.watermark_path)
                img_width, img_height = img.size
                aspect = img_width / img_height
                
                # Center watermark
                wm_height = 2 * inch
                wm_width = wm_height * aspect
                x = (PAGE_WIDTH - wm_width) / 2
                y = (PAGE_HEIGHT - wm_height) / 2
                
                canvas.setFillAlpha(self.watermark_opacity)
                canvas.drawImage(
                    self.watermark_path, x, y, 
                    width=wm_width, height=wm_height,
                    preserveAspectRatio=True, mask='auto'
                )
                canvas.setFillAlpha(1)
            except Exception as e:
                print(f"Warning: Could not load watermark: {e}")
        
        # Footer
        canvas.setStrokeColor(colors.HexColor("#E5E5EA"))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 0.6 * inch, PAGE_WIDTH - MARGIN, 0.6 * inch)
        
        canvas.setFont("Times-Roman", 8)
        canvas.setFillColor(COLOR_MUTED)
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        canvas.drawString(MARGIN, 0.4 * inch, date_str)
        
        # Page number
        page_num = f"Page {doc.page}"
        canvas.drawRightString(PAGE_WIDTH - MARGIN, 0.4 * inch, page_num)
        
        # Company name in footer center
        canvas.drawCentredString(PAGE_WIDTH / 2, 0.4 * inch, self.company_name)
        
        canvas.restoreState()


def create_title_page(canvas, company_name, logo_path=None):
    """Create professional title page."""
    canvas.saveState()
    
    # Background accent bar
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.rect(0, PAGE_HEIGHT - 2.2 * inch, PAGE_WIDTH, 2.2 * inch, fill=1, stroke=0)
    
    # Logo (large, centered - takes up ~40% of page)
    if logo_path and os.path.exists(logo_path):
        try:
            img = Image.open(logo_path)
            img_width, img_height = img.size
            aspect = img_width / img_height
            
            # Logo should be large and prominent
            logo_height = 4.5 * inch
            logo_width = logo_height * aspect
            
            x = (PAGE_WIDTH - logo_width) / 2
            y = PAGE_HEIGHT / 2 - 1.3 * inch
            
            canvas.drawImage(
                logo_path, x, y,
                width=logo_width, height=logo_height,
                preserveAspectRatio=True, mask='auto'
            )
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")
    
    # Company name
    canvas.setFont("Helvetica-Bold", 34)
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 1.8 * inch, company_name)
    
    # Divider line
    canvas.setStrokeColor(COLOR_ACCENT)
    canvas.setLineWidth(2.5)
    canvas.line(
        PAGE_WIDTH / 2 - 2.2 * inch, PAGE_HEIGHT / 2 - 2.15 * inch,
        PAGE_WIDTH / 2 + 2.2 * inch, PAGE_HEIGHT / 2 - 2.15 * inch
    )
    
    # Subtitle
    canvas.setFont("Times-Italic", 20)
    canvas.setFillColor(COLOR_ACCENT)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 2.65 * inch, "Multi-Perspective Analysis")
    
    # Date
    canvas.setFont("Times-Roman", 11)
    canvas.setFillColor(COLOR_MUTED)
    date_str = datetime.now().strftime("%B %d, %Y")
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT / 2 - 3.15 * inch, date_str)
    
    # Confidential footer
    canvas.setFillColor(COLOR_PRIMARY)
    canvas.rect(0, 0, PAGE_WIDTH, 0.8 * inch, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(PAGE_WIDTH / 2, 0.4 * inch, "CONFIDENTIAL")
    
    canvas.restoreState()
    canvas.showPage()


def create_styles():
    """Create custom paragraph styles."""
    styles = getSampleStyleSheet()
    
    # Section header
    styles.add(ParagraphStyle(
        name='CustomSectionHeader',
        parent=styles['Heading1'],
        fontSize=15,
        textColor=COLOR_PRIMARY,
        spaceAfter=12,
        spaceBefore=24,
        fontName='Times-Bold',
        leftIndent=0,
        borderPadding=(10, 10, 10, 10),
        backColor=COLOR_LIGHT_BG,
        borderWidth=0,
        borderColor=COLOR_LIGHT_BG,
    ))
    
    # Subsection header
    styles.add(ParagraphStyle(
        name='CustomSubHeader',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=COLOR_ACCENT_DARK,
        spaceAfter=8,
        spaceBefore=12,
        fontName='Times-Bold',
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_TEXT,
        spaceAfter=10,
        leading=14,
        fontName='Times-Roman',
        alignment=TA_LEFT,
    ))
    
    # Bullet points
    styles.add(ParagraphStyle(
        name='CustomBullet',
        parent=styles['Normal'],
        fontSize=10,
        textColor=COLOR_TEXT,
        spaceAfter=6,
        leading=14,
        leftIndent=20,
        bulletIndent=10,
        fontName='Times-Roman',
    ))
    
    # Year divider
    styles.add(ParagraphStyle(
        name='CustomYearHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.white,
        spaceAfter=20,
        spaceBefore=30,
        fontName='Times-Bold',
        alignment=TA_CENTER,
        backColor=COLOR_PRIMARY,
        borderPadding=(14, 14, 14, 14),
    ))
    
    return styles


def create_badge(label, value):
    """Create a colored badge for ratings/signals."""
    color = get_signal_color(value)
    
    badge_style = ParagraphStyle(
        name='Badge',
        fontSize=10,
        textColor=color,
        fontName='Times-Bold',
    )
    
    label_style = ParagraphStyle(
        name='BadgeLabel',
        fontSize=10,
        textColor=COLOR_TEXT,
        fontName='Times-Bold',
    )
    
    # Create table for badge layout
    data = [[Paragraph(f"{label}:", label_style), Paragraph(str(value), badge_style)]]
    
    table = Table(data, colWidths=[2 * inch, 3 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (1, 0), colors.Color(color.red, color.green, color.blue, alpha=0.12)),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    return table


def process_value(key, value, styles):
    """Process a value from JSON and return appropriate flowable elements."""
    elements = []
    
    # Badge fields (ratings, signals, verdicts)
    badge_keywords = ['rating', 'signal', 'verdict', 'level', 'action']
    if any(kw in key.lower() for kw in badge_keywords) and isinstance(value, str):
        elements.append(create_badge(format_field_name(key), value))
        elements.append(Spacer(1, 0.15 * inch))
        return elements
    
    # Add subheader
    elements.append(Paragraph(format_field_name(key), styles['CustomSubHeader']))
    
    # Lists
    if isinstance(value, list):
        for item in value:
            bullet_text = f"• {str(item)}"
            elements.append(Paragraph(bullet_text, styles['CustomBullet']))
        elements.append(Spacer(1, 0.1 * inch))
    
    # Text
    elif isinstance(value, str):
        elements.append(Paragraph(value, styles['CustomBody']))
        elements.append(Spacer(1, 0.1 * inch))
    
    # Other types
    else:
        elements.append(Paragraph(str(value), styles['CustomBody']))
        elements.append(Spacer(1, 0.1 * inch))
    
    return elements


def process_section(section_name, section_data, styles, canvas=None):
    """Process a section (like 'buffett', 'taleb', etc.) and return elements."""
    elements = []
    
    # Section header
    header_text = format_field_name(section_name)
    if section_name.lower() in ['buffett', 'taleb', 'contrarian']:
        header_text = f"{format_field_name(section_name)} Analysis"
    
    # Add bookmark for PDF outline/navigation
    bookmark_key = f"section_{section_name}"
    elements.append(BookmarkAction(header_text, bookmark_key, level=1))
    elements.append(Paragraph(header_text, styles['CustomSectionHeader']))
    elements.append(Spacer(1, 0.15 * inch))
    
    # Process each field in section
    if isinstance(section_data, dict):
        for key, value in section_data.items():
            section_elements = process_value(key, value, styles)
            elements.extend(section_elements)
    elif isinstance(section_data, str):
        elements.append(Paragraph(section_data, styles['CustomBody']))
    elif isinstance(section_data, list):
        for item in section_data:
            bullet_text = f"• {str(item)}"
            elements.append(Paragraph(bullet_text, styles['CustomBullet']))
    
    elements.append(Spacer(1, 0.2 * inch))
    return elements


def json_to_pdf(json_input, pdf_filename, company_name, logo_path=None, watermark_path=None):
    """
    Convert structured JSON to professional PDF report.
    
    Args:
        json_input: Path to JSON file or dict
        pdf_filename: Output PDF path
        company_name: Company name for report
        logo_path: Optional path to logo image for title page
        watermark_path: Optional path to watermark image for content pages (defaults to logo_path)
    """
    # Load JSON
    if isinstance(json_input, str):
        with open(json_input, 'r') as f:
            data = json.load(f)
    elif isinstance(json_input, dict):
        data = json_input
    else:
        raise ValueError("json_input must be a file path or dict")
    
    # Create PDF
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    
    # Create custom canvas for title page
    def add_title_page(canvas, doc):
        create_title_page(canvas, company_name, logo_path)
    
    # Story (content)
    story = []
    styles = create_styles()
    
    # Detect if data has year structure
    has_years = all(str(k).isdigit() for k in data.keys() if k)
    
    if has_years:
        # Multi-year report
        years = sorted(data.keys(), reverse=True)
        
        for year in years:
            # Year divider with bookmark (Level 0 - top level)
            bookmark_key = f"year_{year}"
            story.append(BookmarkAction(f"Fiscal Year {year}", bookmark_key, level=0))
            story.append(Paragraph(f"Fiscal Year {year}", styles['CustomYearHeader']))
            story.append(Spacer(1, 0.3 * inch))
            
            year_data = data[year]
            
            # Process each section in year
            for section_name, section_data in year_data.items():
                section_elements = process_section(section_name, section_data, styles)
                story.extend(section_elements)
            
            # Page break after each year (except last)
            if year != years[-1]:
                story.append(PageBreak())
    
    else:
        # Single structure (no years)
        for section_name, section_data in data.items():
            section_elements = process_section(section_name, section_data, styles)
            story.extend(section_elements)
    
    # Build PDF
    template = PDFTemplate(company_name, logo_path, watermark_path)
    doc.build(story, onFirstPage=add_title_page, onLaterPages=template)
    
    print(f"PDF successfully generated: {pdf_filename}")


if __name__ == "__main__":
    # Example usage
    json_to_pdf(
        "./scripts/test.json",
        "./scripts/output.pdf",
        "Erebus Observatory Network",
        logo_path="./logo.png",
        watermark_path="./watermark.png",
    )