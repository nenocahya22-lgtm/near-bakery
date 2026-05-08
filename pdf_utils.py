from fpdf import FPDF
from datetime import datetime

class PO_PDF(FPDF):
    def header(self):
        # Background color
        self.set_fill_color(249, 247, 242) # Warm Bone
        self.rect(0, 0, 210, 297, 'F')
        
        # Logo placeholder or Title
        self.set_font('Times', 'B', 24)
        self.set_text_color(74, 68, 63) # Deep Taupe
        self.cell(0, 15, 'NEAR BAKERY & CO.', 0, 1, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 5, 'The Royal Heritage - Purchase Order', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-25)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(180, 180, 180)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_po_pdf(po_id, supplier_name, date, items):
    pdf = PO_PDF()
    pdf.add_page()
    
    # PO Info Box
    pdf.set_fill_color(212, 175, 55) # Champagne Gold
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f'  PURCHASE ORDER: #{po_id}', 0, 1, 'L', True)
    
    pdf.set_text_color(74, 68, 63) # Deep Taupe
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Supplier:', 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, f'{supplier_name}', 0, 1)
    
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(40, 7, 'Order Date:', 0, 0)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, f'{date}', 0, 1)
    
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(74, 68, 63)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(10, 10, 'No', 1, 0, 'C', True)
    pdf.cell(80, 10, 'Material Name', 1, 0, 'C', True)
    pdf.cell(30, 10, 'Qty', 1, 0, 'C', True)
    pdf.cell(30, 10, 'Unit', 1, 0, 'C', True)
    pdf.cell(40, 10, 'Estimated Total', 1, 1, 'C', True)
    
    # Table Content
    pdf.set_text_color(74, 68, 63)
    pdf.set_font('Helvetica', '', 10)
    total_po = 0
    for i, item in enumerate(items, 1):
        pdf.cell(10, 8, str(i), 1, 0, 'C')
        pdf.cell(80, 8, item['name'], 1, 0, 'L')
        pdf.cell(30, 8, str(item['qty']), 1, 0, 'C')
        pdf.cell(30, 8, item['unit'], 1, 0, 'C')
        pdf.cell(40, 8, f"Rp {item['subtotal']:,.0f}", 1, 1, 'R')
        total_po += item['subtotal']
    
    # Total
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(150, 10, 'TOTAL ESTIMATED AMOUNT', 1, 0, 'R')
    pdf.cell(40, 10, f"Rp {total_po:,.0f}", 1, 1, 'R')
    
    pdf.ln(20)
    pdf.cell(0, 10, 'Authorized by,', 0, 1, 'R')
    pdf.ln(15)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 10, 'Management - Near Bakery & Co.', 0, 1, 'R')
    
    return pdf.output()
