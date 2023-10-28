import datetime
import os

from pathlib import Path
from reportlab.platypus import Image, SimpleDocTemplate, Paragraph, PageBreak, Spacer, Table
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from threading import Thread
from time import sleep
from utils.utils import toBRCurrency

# A4 page size: 210 x 297 mm

##### Objects and utilities #####

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
    self.drawRightString(205*mm, 12*mm, page)

  def save(self):
    # Modify the save() function to add page-number before saving every page
    page_count = len(self.pages)
    for page in self.pages:
      self.__dict__.update(page)
      self.draw_page_number(page_count)
      canvas.Canvas.showPage(self)
    
    # saving
    canvas.Canvas.save(self)

# creates a thread to removes a report after 1 minute
def delayedRemoveReport(filePath):
  Thread(target=threadDelayedRemoveReport, args=(filePath,)).start()

# removes a report after 1 minute
def threadDelayedRemoveReport(filePath):
  sleep(60)
  os.remove(filePath)

##### General functions #####

# get used personalized and common styles
def getPersonalizedStyles():

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
  styles.add(ParagraphStyle(
    name='Normal_LEFT',
    parent=styles['Normal'],
    fontName='Helvetica',
    wordWrap='LTR',
    alignment=TA_LEFT,
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
  styles.add(ParagraphStyle(
    name='Title_LEFT',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    wordWrap='LTR',
    alignment=TA_LEFT,
    fontSize=14,
    leading=10,
    textColor=colors.black,
    borderPadding=0,
    leftIndent=0,
    rightIndent=0,
    spaceAfter=0,
    spaceBefore=0,
    splitLongWords=True,
    spaceShrinkage=0.05,
  ))
  styles.add(ParagraphStyle(
    name='Title_CENTER',
    parent=styles['Normal'],
    fontName='Helvetica-Bold',
    wordWrap='LTR',
    alignment=TA_CENTER,
    fontSize=14,
    leading=10,
    textColor=colors.black,
    borderPadding=0,
    leftIndent=0,
    rightIndent=0,
    spaceAfter=0,
    spaceBefore=0,
    splitLongWords=True,
    spaceShrinkage=0.05,
  ))

  return styles

# return a title
def getTitle(title, titleType='Title_LEFT'):
  return Table([[Paragraph(title, getPersonalizedStyles()[titleType])]], colWidths=[200*mm])
  # return Paragraph(title, getPersonalizedStyles()[titleType])

# get head table
def getReportHead(reportName):

  headLogo = Image(Path.cwd() / 'assets' / 'gestao_miss_teen_logo_side.png')
  headData = [[headLogo, reportName]]

  headTable = Table(headData, colWidths=[80*mm, 120*mm])
  headTable.setStyle([
    ('FONT', (0,0), (-1,-1), 'Helvetica-Bold', 14),
    ('ALIGN', (0,0), (0,-1), 'LEFT'),
    ('ALIGN', (1,0), (1,-1), 'CENTER'),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
  ])

  return headTable

# get table box with two collumns, used by filters
def getTwoColumnBoxTable(data, titleWithContent, titleWithoutContent):

  styles = getPersonalizedStyles()

  boxTableData = [[titleWithoutContent, ' ']]
  if(data and len(data) > 0):
    boxTableData = [[titleWithContent, ' ']]
    for fpos in range(0, len(data), 2):
      if fpos+1 < len(data):
        boxTableData.append([Paragraph(data[fpos], styles['Normal_LEFT']), Paragraph(data[fpos+1], styles['Normal_LEFT'])])
      else:
        boxTableData.append([Paragraph(data[fpos], styles['Normal_LEFT'])])
  
  boxTable = Table(boxTableData, colWidths=[100*mm, 100*mm])
  boxTable.setStyle([
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
    ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 14),
    ('BOX', (0,0), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,1), (-1,-1), colors.toColor('rgb(54,52,52)'))
  ])

  return boxTable

# get table with the sizes and numbers of columns specified in colWidths
def getMultiColumnTable(data, colWidths, repeatRows=1, stripColors=True):

  table = Table(data, colWidths=colWidths, repeatRows=repeatRows)
  table.setStyle([
    ('FONT', (0,0), (-1,-1), 'Helvetica', 9),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('GRID', (0,0), (-1,-1), 1, colors.toColor('rgb(241,170,167)')),
    ('BACKGROUND', (0,0), (-1,0), colors.toColor('rgb(241,170,167)')),
    ('TEXTCOLOR', (0,0), (-1,-1), colors.toColor('rgb(54,52,52)'))
  ])
  
  if stripColors:
    for i in range(1, len(data)):
      if i % 2 == 0:
        table.setStyle([('BACKGROUND', (0, i), (-1, i), colors.toColor('rgb(249,229,228)'))])

  return table

# creates a report given its name and elements, returns its path
def createReportPDF(pdfName, elems):

  # create reports dir if not exists
  reportsDir = Path.cwd() / 'reports'
  if not os.path.isdir(reportsDir):
    print('# Reports directory not found, creating')
    os.mkdir(reportsDir)

  # crates pdf path
  pdfPath = (reportsDir / pdfName).__str__()

  # configure and build pdf
  pdf = SimpleDocTemplate(
    filename=pdfPath,
    pagesize=A4,
    leftMargin=0.5*inch,
    rightMargin=0.5*inch,
    topMargin=0.5*inch,
    bottomMargin=0.5*inch
  )
  pdf.build(elems, canvasmaker=MyCanvas)

  return pdfPath

##### Specific functions #####

# get filter table
def getFilterTable(filters):
  return getTwoColumnBoxTable(filters, 'Filtros', 'Sem Filtros')

# get clients data table
def getClientsDataTable(clientsQuery):

  styles = getPersonalizedStyles()
  data = [[
    'Nome', 
    Paragraph('Data última<br/>compra', styles['Normal_CENTER']), 
    Paragraph('Valor última compra', styles['Normal_CENTER']), 
    'Classificação', 
    'Contatos', 
    'Filhos'
  ]]
  
  for client in clientsQuery:

    # client
    contactValues = client['client_contact_values'].replace(',', '<br/>') if client['client_contact_values'] else ''
    children = ''

    if client['client_children_names']:
      childrenNames = client['client_children_names'].split(',')
      childrenBirthDates = client['client_children_birth_dates'].split(',')
      childrenSizes = client['client_children_product_size_names'].split(',')

      for childPos in range(0, len(childrenNames)):
        
        childBirthDate = ''
        if childrenBirthDates[childPos] and childrenBirthDates[childPos] != 'NULL':
          childBirthDate = datetime.datetime.strptime(childrenBirthDates[childPos], '%Y-%m-%d').strftime('%d/%m')
        
        children = children + ('<br/>' if childPos > 0 else '') + f"{childrenNames[childPos]} {childBirthDate} Tam:{childrenSizes[childPos]}"

    data.append([
      Paragraph(client['client_name'], styles['Normal_CENTER']),
      Paragraph(client['last_sale_date'].strftime("%d/%m/%Y") if client['last_sale_date'] else '', styles['Normal_CENTER']),
      Paragraph(toBRCurrency(client['last_sale_total_value']) if client['last_sale_total_value'] else '', styles['Normal_CENTER']),
      Paragraph(client['client_classification'], styles['Normal_CENTER']),
      Paragraph(contactValues, styles['Normal_CENTER']),
      Paragraph(children, styles['Normal_CENTER'])
    ])

  return getMultiColumnTable(data, [40*mm, 23*mm, 23*mm, 24*mm, 30*mm, 60*mm])

# get conditionals summary table
def getConditionalsSummaryTable(conditionalsSummary):

  quants = [
    int(conditionalsSummary['canceled_quantity']),
    int(conditionalsSummary['returned_quantity']),
    int(conditionalsSummary['pending_quantity']),
    int(conditionalsSummary['total_quantity'])
  ]

  summData = [
    ['','Cancelado', 'Devolvido', 'Pendente', 'Total'],
    ['Quantidade'] + [str(quant) for quant in quants],
    ['Percentual da quantidade'] + [(str(round((quant/quants[3])*100))+'%') for quant in quants]
  ]

  return getMultiColumnTable(summData, [60*mm, 35*mm, 35*mm, 35*mm, 35*mm])

# get conditionals data table
def getConditionalsDataTable(conditionalsQuery):

  styles = getPersonalizedStyles()

  data = [['Código', 'Data', 'Status', 'Cliente', 'Vendedor']]
  for conditional in conditionalsQuery:

    data.append([
      Paragraph(str(conditional['conditional_id']), styles['Normal_CENTER']),
      Paragraph(conditional['conditional_creation_date_time'].strftime("%d/%m/%Y"), styles['Normal_CENTER']),
      Paragraph(conditional['conditional_status'], styles['Normal_CENTER']),
      Paragraph(conditional['conditional_client_name'], styles['Normal_CENTER']),
      Paragraph(conditional['conditional_employee_name'], styles['Normal_CENTER'])
    ])

  return getMultiColumnTable(data, [40*mm, 40*mm, 40*mm, 40*mm, 40*mm])

# get products data table
def getProductsDataTable(productsQuery):

  styles = getPersonalizedStyles()

  #data = [['Produtos'],['Cod', 'Nome', 'Tipos', 'Coleções', 'Variações', '30', '32', '34', '36', '38', '40', '42', '44', 'PP', 'P', 'M', 'G']]
  data = [['Código', 'Nome', 'Variações', '30', '32', '34', '36', '38', '40', '42', '44', 'PP', 'P', 'M', 'G']]
  
  for product in productsQuery:

    # product
    types = product['product_type_names'].replace(',', '<br/>') if product['product_type_names'] else ''
    collections = product['product_collection_names'].replace(',', '<br/>') if product['product_collection_names'] else ''

    # product variation
    colorNames = product['product_color_names'].split(',')
    otherNames = product['product_other_names'].split(',')
    sizeNames = product['product_size_names'].split(',')
    customizedQuantities = product['customized_product_quantityes'].split(',')
    customizedPrices = product['customized_product_prices'].split(',')
    
    # Order = other, color, sizes
    variations = {}
    for customPPos in range(0, len(customizedQuantities)):
      
      # Name = otherName<br/>colorName
      variationName = f'{otherNames[customPPos]}<br/>{colorNames[customPPos]}'
      
      # Initializate its structure and sizes
      if otherNames and colorNames and not variations.get(variationName):
        variations[variationName] = {}
        for size in ['30','32','34','36','38','40','42','44','PP','P','M','G']:
          variations[variationName][size] = 0

      variations[variationName][sizeNames[customPPos]] = customizedQuantities[customPPos]

    for variation in variations:
      data.append([
        Paragraph(str(product['product_code']), styles['Normal_CENTER']),
        Paragraph(product['product_name'], styles['Normal_CENTER']),
        #Paragraph(types, styles['Normal_CENTER']),
        #Paragraph(collections, styles['Normal_CENTER']),
        Paragraph(variation, styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['30']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['32']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['34']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['36']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['38']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['40']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['42']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['44']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['PP']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['P']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['M']), styles['Normal_CENTER']),
        Paragraph(str(variations[variation]['G']), styles['Normal_CENTER']),
      ])

  return getMultiColumnTable(data, [25*mm, 25*mm, 30*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm, 10*mm])

# get sales summary table
def getSalesSummaryTable(salesSummary):
  
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
    ['','Crédito', 'Cheque', 'Débito', 'Dinheiro', 'Pix', 'Total'],
    ['Quantidade'] + [str(quant) for quant in quants],
    ['Valor'] + [toBRCurrency(value) for value in values],
    ['Percentual da quantidade'] + [(str(round((quant/quants[5])*100))+'%') for quant in quants],
    ['Percentual do valor'] + [(str(round((value/values[5])*100))+'%') for value in values]
  ]

  return getMultiColumnTable(summData, [50*mm, 25*mm, 25*mm, 25*mm, 25*mm, 25*mm, 25*mm])

# get sales data table
def getSalesDataTable(salesQuery):

  styles = getPersonalizedStyles()

  data = [['Cod', 'Data', 'Confirmado', 'Cliente', 'Vendedor', 'Formas de Pagamento', 'Valor']]
  for sale in salesQuery:

    payments = ''
    paymentMethodNames = sale['payment_method_names'].split(',')
    paymentMethodInstallmentNumbers = sale['payment_method_installment_numbers'].split(',')
    paymentMethodValues = sale['payment_method_values'].split(',')
    
    for payPos in range(0, len(paymentMethodNames)):
      payments = payments + ('<br/>' if len(payments) > 0 else '') + f"{paymentMethodNames[payPos]} ({paymentMethodInstallmentNumbers[payPos]} X {toBRCurrency(float(paymentMethodValues[payPos]))})"

    data.append([
      Paragraph(str(sale['sale_id']), styles['Normal_CENTER']),
      Paragraph(sale['sale_creation_date_time'].strftime("%d/%m/%Y"), styles['Normal_CENTER']),
      Paragraph('S' if sale['sale_status'] == 'Confirmado' else 'N', styles['Normal_CENTER']),
      Paragraph(sale['sale_client_name'], styles['Normal_CENTER']),
      Paragraph(sale['sale_employee_name'], styles['Normal_CENTER']),
      Paragraph(payments, styles['Normal_CENTER']),
      Paragraph(toBRCurrency(float(sale['sale_total_value'])), styles['Normal_CENTER'])
    ])

  return getMultiColumnTable(data, [16*mm, 21*mm, 17*mm, 29*mm, 29*mm, 62*mm, 26*mm])

##### Specific report creation functions #####

# clients
def createClientsReport(filters, clientsQuery):

  # appends pdf initial elements
  elems = []
  elems.append(getReportHead('Relatório de clientes'))
  elems.append(Spacer(1, 2*mm))
  elems.append(getFilterTable(filters))

  # if not find clients, append not find message
  if not clientsQuery or len(clientsQuery) == 0:
    elems.append(Spacer(1, 4*mm))
    elems.append(getTitle('Não foram encontrados clientes com estes filtros', 'Title_CENTER')),
  
  # if find, append data
  else:
    elems.append(Spacer(1, 2*mm))
    elems.append(getTitle('Clientes'))
    elems.append(Spacer(1, 2*mm))
    elems.append(getClientsDataTable(clientsQuery))

  # creates pdf name and the pdf itself
  pdfName = f'RelatorioClientes{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pdf'
  pdfPath = createReportPDF(pdfName, elems)

  return pdfPath, pdfName

# conditionals
def createConditionalsReport(filters, conditionalsSummary, conditionalsQuery):

  # appends pdf initial elements
  elems = []
  elems.append(getReportHead('Relatório de condicionais'))
  elems.append(Spacer(1, 2*mm))
  elems.append(getFilterTable(filters))

  # if not find conditionals, append not find message
  if not conditionalsSummary or not conditionalsQuery or len(conditionalsQuery) == 0:
    elems.append(Spacer(1, 4*mm))
    elems.append(getTitle('Não foram encontradas condicionais com estes filtros', 'Title_CENTER'))
  
  # if find, append summary and data
  else:
    elems.append(Spacer(1, 2*mm))
    elems.append(getTitle('Resumo'))
    elems.append(Spacer(1, 2*mm))
    elems.append(getConditionalsSummaryTable(conditionalsSummary))
    elems.append(Spacer(1, 2*mm))
    elems.append(getTitle('Condicionais'))
    elems.append(Spacer(1, 2*mm))
    elems.append(getConditionalsDataTable(conditionalsQuery))

  # creates pdf name and the pdf itself
  pdfName = f'RelatorioCondicionais{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pdf'
  pdfPath = createReportPDF(pdfName, elems)

  return pdfPath, pdfName

# products
def createProductsReport(filters, productsQuery):

  # appends pdf initial elements
  elems = []
  elems.append(getReportHead('Relatório de produtos'))
  elems.append(Spacer(1, 2*mm))
  elems.append(getFilterTable(filters))

  # if not find products, append not find message
  if not productsQuery or len(productsQuery) == 0:
    elems.append(Spacer(1, 4*mm))
    elems.append(getTitle('Não foram encontrados produtos com estes filtros', 'Title_CENTER')),
  
  # if find, append data
  else:
    elems.append(Spacer(1, 2*mm))
    elems.append(getTitle('Produtos'))
    elems.append(Spacer(1, 2*mm))
    elems.append(getProductsDataTable(productsQuery))

  # creates pdf name and the pdf itself
  pdfName = f'RelatorioProdutos{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pdf'
  pdfPath = createReportPDF(pdfName, elems)

  return pdfPath, pdfName

# sales
def createSalesReport(filters, salesSummary, salesQuery):

  # appends pdf initial elements
  elems = []
  elems.append(getReportHead('Relatório de vendas'))
  elems.append(Spacer(1, 1*mm))
  elems.append(getFilterTable(filters))

  # if not find sales, append not find message
  if not salesSummary or not salesQuery or len(salesQuery) == 0:
    elems.append(Spacer(1, 4*mm))
    elems.append(getTitle('Não foram encontradas vendas com estes filtros', 'Title_CENTER'))
  
  # if find, append summary and data
  else:
    elems.append(Spacer(1, 2*mm))
    elems.append(getTitle('Resumo'))
    elems.append(Spacer(1, 2*mm))
    elems.append(getSalesSummaryTable(salesSummary))
    elems.append(Spacer(1, 2*mm))
    elems.append(getTitle('Vendas'))
    elems.append(Spacer(1, 2*mm))
    elems.append(getSalesDataTable(salesQuery))

  # creates pdf name and the pdf itself
  pdfName = f'RelatorioVendas{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.pdf'
  pdfPath = createReportPDF(pdfName, elems)

  return pdfPath, pdfName