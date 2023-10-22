import datetime
import locale
import os

from pathlib import Path
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, PageBreak, Spacer, Table
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from threading import Thread
from time import sleep

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
    for page in self.pages:
      self.__dict__.update(page)
      self.draw_page_number(page_count)
      canvas.Canvas.showPage(self)
    
    # saving
    canvas.Canvas.save(self)

def createSalesReport(filters, salesSummary, salesQuery):

  # creates a centered font style used in paragraphs
  styles = getSampleStyleSheet()
  styles.add(ParagraphStyle(
    name='Normal_CENTER',
    parent=styles['Normal'],
    fontName='Helvetica',
    wordWrap='LTR',
    alignment=TA_CENTER,
    fontSize=9,
    leading=10,
    textColor=colors.toColor('rgb(54,52,52)'),
    borderPadding=0,
    leftIndent=0,
    rightIndent=0,
    spaceAfter=0,
    spaceBefore=0,
    splitLongWords=True,
    spaceShrinkage=0.05,
  ))

  # used to adjust currency strings
  locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

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
  filterData = [['Sem Filtros', ' ']]
  if(filters and len(filters) > 0):
    filterData = [['Filtros', ' ']]
    for fpos in range(0, len(filters), 2):
      if fpos+1 < len(filters):
        filterData.append([Paragraph(filters[fpos], styles['Normal_CENTER']), Paragraph(filters[fpos+1], styles['Normal_CENTER'])])
      else:
        filterData.append([Paragraph(filters[fpos], styles['Normal_CENTER'])])

  filterTable = Table(filterData, colWidths=[95*mm, 85*mm])
  filterTable.setStyle([
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 14),
    ('BOX', (0,0), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
  ])

  # summary table
  quants = [
    int(salesSummary['credito_quantity']),
    int(salesSummary['cheque_quantity']),
    int(salesSummary['debito_quantity']),
    int(salesSummary['dinheiro_quantity']),
    int(salesSummary['pix_quantity']),
    int(salesSummary['total_quantity'])
  ]
  values = [
    float(salesSummary['credito_value']),
    float(salesSummary['cheque_value']),
    float(salesSummary['debito_value']),
    float(salesSummary['dinheiro_value']),
    float(salesSummary['pix_value']),
    float(salesSummary['total_value'])
  ]
  summData = [
    ['Resumo'],
    ['','Crédito', 'Cheque', 'Débito', 'Dinheiro', 'Pix', 'Total'],
    ['Quantidade'] + [str(quant) for quant in quants],
    ['Valor'] + [locale.currency(value, grouping=True) for value in values],
    ['Percentual da quantidade'] + [(str(round((quant/quants[5])*100))+'%') for quant in quants],
    ['Percentual do valor'] + [(str(round((value/values[5])*100))+'%') for value in values]
  ]
  summTable = Table(summData, colWidths=[48*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm])
  summTable.setStyle([
    ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 14),
    ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,0), 'LEFT'),
    ('ALIGN', (0,1), (-1,-1), 'CENTER'),
    ('GRID', (0,1), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('BACKGROUND', (0,1), (-1,1), colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
  ])

  # data table
  data = [['Vendas'],['Cod', 'Data', 'Confirmado', 'Cliente', 'Vendedor', 'Formas de Pagamento', 'Valor']]
  for sale in salesQuery:

    payments = ''
    paymentMethodNames = sale['payment_method_names'].split(',')
    paymentMethodInstallmentNumbers = sale['payment_method_installment_numbers'].split(',')
    paymentMethodValues = sale['payment_method_values'].split(',')
    
    for payPos in range(0, len(paymentMethodNames)):
      payments = payments + ('<br/>' if len(payments) > 0 else '') + f"{paymentMethodNames[payPos]} ({paymentMethodInstallmentNumbers[payPos]} X {locale.currency(float(paymentMethodValues[payPos]), grouping=True)})"

    data.append([
      Paragraph(str(sale['sale_id']), styles['Normal_CENTER']),
      Paragraph(sale['sale_creation_date_time'].strftime("%d/%m/%Y"), styles['Normal_CENTER']),
      Paragraph('S' if sale['sale_status'] == 'Confirmado' else 'N', styles['Normal_CENTER']),
      Paragraph(sale['sale_client_name'], styles['Normal_CENTER']),
      Paragraph(sale['sale_employee_name'], styles['Normal_CENTER']),
      Paragraph(payments, styles['Normal_CENTER']),
      Paragraph(locale.currency(float(sale['sale_total_value']), grouping=True), styles['Normal_CENTER'])
    ])

  dataTable = Table(data, colWidths=[10*mm, 22*mm, 17*mm, 27*mm, 27*mm, 57*mm, 20*mm])
  dataTable.setStyle([
    ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 14),
    ('FONT', (0,1), (-1,-1), 'Helvetica', 9),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,0), 'LEFT'),
    ('ALIGN', (0,1), (-1,-1), 'CENTER'),
    ('GRID', (0,1), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('BACKGROUND', (0,1), (-1,1), colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
  ])
  for i in range(2, len(data)):
    if i % 2 == 0:
      dataTable.setStyle([('BACKGROUND', (0, i), (-1, i), colors.toColor('rgb(255,245,244)'))])

  elems = []
  elems.append(headTable)
  elems.append(Spacer(1, 1*mm))
  elems.append(filterTable)
  elems.append(Spacer(1, 2*mm))
  elems.append(summTable)
  elems.append(Spacer(1, 2*mm))
  elems.append(dataTable)

  pdfName = f'SalesReport{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pdf'
  pdfPath = f'reports/{pdfName}'

  pdf = SimpleDocTemplate(
    filename=pdfPath,
    pagesize=A4,
    leftMargin=0.5*inch,
    rightMargin=0.5*inch,
    topMargin=0.5*inch,
    bottomMargin=0.5*inch
  )
  pdf.build(elems, canvasmaker=MyCanvas)

  return pdfPath, pdfName

# creates a thread to removes a report after 10 minutes
def delayedRemoveReport(filePath):
  Thread(target=threadDelayedRemoveReport, args=(filePath,)).start()

# removes a report after 10 minutes
def threadDelayedRemoveReport(filePath):
  sleep(600)
  os.remove(filePath)