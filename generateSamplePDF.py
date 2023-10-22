from pathlib import Path
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, PageBreak, Spacer, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# A4 page size: 210 x 297 mm
# Custom Canvas class for automatically adding page-numbers
class MyCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def draw_page_number(self, page_count):
        # Modify the content and styles according to the requirement
        page = "{curr_page}/{total_pages}".format(curr_page=self._pageNumber, total_pages=page_count)
        self.setFont("Helvetica", 10)
        self.drawRightString(195*mm, 12*mm, page)

    def save(self):
        # Modify the save() function to add page-number before saving every page
        page_count = len(self.pages)
        i = 0
        for page in self.pages:
            i = i+1
            self.__dict__.update(page)
            self.draw_page_number(page_count)
            canvas.Canvas.showPage(self)
        
        # saving
        canvas.Canvas.save(self)

# head table
headLogo = Image(Path.cwd() / 'assets' / 'gestao_miss_teen_logo_side.png')
headData = [[headLogo, 'Relatório de vendas']]

headTable = Table(headData, colWidths=[70*mm, 110*mm])
headTable.setStyle([
    ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 14),
    ('ALIGN', (0,0), (0,-1), 'LEFT'),
    ('ALIGN', (1,0), (1,-1), 'CENTER'),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
])

# filter table

filterData = [
    ['Filtros'],
    ['Data: 21/07/2022 até 21/08/2022', 'Cor: Azul'],
    ['Numeração: 40 até 50', 'Outro: Com Babado']
]

filterTable = Table(filterData, colWidths=[95*mm, 85*mm])
filterTable.setStyle([
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 14),
    ('BOX', (0,0), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
])

# data table
data = [
    ['Teste', 'Numero', 'String'],
    ['Linha 1', 1, 'Str 1\nStr 2\nStr 3'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3'],
    ['Linha 1', 1, 'Str 1'],
    ['Linha 2', 2, 'Str 2'],
    ['Linha 3', 3, 'Str 3']
]

dataTable = Table(data, colWidths=[60*mm]*3)
dataTable.setStyle([
    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('BACKGROUND', (0,0), (-1,0), colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
])
for i in range(2, len(data)):
    if i % 2 == 0:
        dataTable.setStyle([('BACKGROUND', (0, i), (-1, i), colors.toColor('rgb(255,245,244)'))])

elems = []
elems.append(headTable)
elems.append(Spacer(1, 1*mm))
elems.append(filterTable)
elems.append(Spacer(1, 5*mm))
elems.append(dataTable)

pdf = SimpleDocTemplate(
    filename='reports/Report.pdf',
    pagesize=A4,
    leftMargin=0.5*inch,
    rightMargin=0.5*inch,
    topMargin=0.5*inch,
    bottomMargin=0.5*inch
)
pdf.build(elems, canvasmaker=MyCanvas)