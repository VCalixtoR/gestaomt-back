from pathlib import Path
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, PageBreak, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

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
        self.drawRightString(195*mm, 272*mm, page)

    def save(self):
        # Modify the save() function to add page-number before saving every page
        page_count = len(self.pages)
        i = 0
        for page in self.pages:
            i = i+1
            print(f'Saving page {i}')
            self.__dict__.update(page)
            self.draw_page_number(page_count)
            canvas.Canvas.showPage(self)
        
        # saving
        print(f'Saving')
        canvas.Canvas.save(self)

data = [
    ['Teste', 'Numero', 'String'],
    ['Linha 1', 1, 'Str 1'],
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

# create paragraphs
headText = Paragraph('Teste de um paragrafo aqui com texto personalizado')

# create and style the table
table = Table(data, colWidths=[1.5*inch]*3)
table.setStyle([
    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('BACKGROUND', (0,0), (-1,0), colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
])
for i in range(2, len(data)):
    if i % 2 == 0:
        table.setStyle([('BACKGROUND', (0, i), (-1, i), colors.toColor('rgb(255,245,244)'))])

elems = []
elems.append(Image(Path.cwd() / 'assets' / 'LogoMt.png', hAlign="LEFT"))
elems.append(headText)
elems.append(table)
elems.append(PageBreak())

pdf = SimpleDocTemplate(
    filename='sample.pdf',
    pagesize=A4
)
pdf.build(elems, canvasmaker=MyCanvas)