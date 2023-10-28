import datetime
from flask import Flask, abort, send_file
from flask_restful import Resource, Api, reqparse
import traceback
import os

from utils.dbUtils import *
from utils.utils import toBRCurrency
from utils.generatePDFReport import createSaleReport, createSalesReport, delayedRemoveReport
from services.authentication import isAuthTokenValid

class SaleApi(Resource):

  def put(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('sale_client_id', location='json', type=int, help='sale client id, required', required=True)
    argsParser.add_argument('sale_employee_id', location='json', type=int, help='sale employee id, required', required=True)
    argsParser.add_argument('sale_payment_method_installments', location='json', type=list, help='sale payment method installments with id and value, required', required=True)
    argsParser.add_argument('sale_has_products', location='json', type=list, help='product and its variations list, required', required=True)
    argsParser.add_argument('sale_total_discount_percentage', location='json', type=float, help='sale total discount percentage float, required and can be 0.0', required=True)
    argsParser.add_argument('sale_total_value', location='json', type=float, help='sale total value float, required', required=True)
    argsParser.add_argument('force_product_addition', location='json', type=str, help='if will add missing products in sale creation, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    forceProductAddition = args['force_product_addition'].lower() in ['true', '1']

    # test client
    clientQuery = dbGetSingle(
      ' SELECT * FROM tbl_client c '
      '   JOIN tbl_person p ON c.client_id = p.person_id '
      '   WHERE c.client_id = %s; ', [(args['sale_client_id'])])
    if not clientQuery:
      return 'O cliente associado à venda não existe no sistema', 422
    
    # test employee
    employeeQuery = dbGetSingle(
      ' SELECT p.person_name, p.person_gender, u.user_type, u.user_entry_allowed, e.employee_active, e.employee_id '
      '   FROM tbl_employee e '
      '   JOIN tbl_user u ON e.employee_id = u.user_id '
      '   JOIN tbl_person p ON u.user_id = p.person_id '
      '   WHERE e.employee_id = %s; ', [(args['sale_employee_id'])])
    if not employeeQuery:
      return 'O funcionario associado à venda não existe no sistema', 422
    if not employeeQuery['user_entry_allowed'] or not employeeQuery['employee_active']:
      return 'O funcionario associado à venda não esta habilitado no sistema', 422

    # test payment method installments
    for salePaymentMethodInstallment in args['sale_payment_method_installments']:

      if not salePaymentMethodInstallment.get('id') or not salePaymentMethodInstallment.get('value'):
        return 'A forma de pagamento associado à venda está com formato inválido', 422

      payMethodQuery = dbGetSingle(
        ' SELECT pm.payment_method_name, pmi.payment_method_installment_number '
        '   FROM tbl_payment_method pm '
        '   JOIN tbl_payment_method_installment pmi ON pm.payment_method_id = pmi.payment_method_id '
        '   WHERE pmi.payment_method_installment_id = %s; ', [(salePaymentMethodInstallment['id'])])
      
      if not payMethodQuery:
        return 'A forma de pagamento associado à venda não existe no sistema', 422

    # test sale total discount percentage
    if args['sale_total_discount_percentage'] < 0.0:
      return 'O desconto na venda não pode ser menor que 0', 422
    if args['sale_total_discount_percentage'] >= 1.0:
      return 'O desconto na venda não pode ser maior ou igual a 100', 422
 
    # test sale products
    calculatedSaleValue = 0
    if len(args['sale_has_products']) == 0:
      return 'A venda deve possuir pelo menos um produto associado', 422

    for product in args['sale_has_products']:
      if not product.get('product_id'):
        return 'Um dos produtos associados foi enviado sem o product_id', 422
      
      productQuery = dbGetSingle(
        ' SELECT p.product_id, p.is_product_active '
        '   FROM tbl_product p '
        '   WHERE p.product_id = %s; ', [(product['product_id'])])

      if not productQuery:
        return 'Um dos produtos associados não foi encontrado no sistema', 422
      if not productQuery['is_product_active']:
        return 'Um dos produtos associados está inativo', 422
      
      if not product.get('customized_products') or len(product['customized_products']) == 0:
        return 'Um dos produtos associados foi enviado sem produtos customizados', 422
      
      # test customized products
      for customizedProduct in product['customized_products']:
        if not customizedProduct.get('customized_product_id'):
          return 'Um dos produtos customizaveis associados foi enviado sem o campo customized_product_id', 422
        if not customizedProduct.get('customized_product_sale_quantity'):
          return 'Um dos produtos customizaveis associados foi enviado sem o campo customized_product_sale_quantity', 422
        if customizedProduct['customized_product_sale_quantity'] <= 0:
          return 'Um dos produtos associados possui quantidade de produtos a venda 0 ou menor', 422

        customProductQuery = dbGetSingle(
          ' SELECT cp.is_customized_product_active, cp.customized_product_price, cp.customized_product_quantity '
          '   FROM tbl_product p '
          '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
          '   WHERE p.product_id = %s AND cp.customized_product_id = %s; ',
          [product['product_id'], customizedProduct['customized_product_id']])
        
        if not customProductQuery:
          return 'Um dos produtos customizaveis associados não foi encontrado no sistema', 422
        if not customProductQuery['is_customized_product_active']:
          return 'Um dos produtos customizaveis associados está inativo', 422
        if not forceProductAddition and customizedProduct['customized_product_sale_quantity'] > customProductQuery['customized_product_quantity']:
          return 'Um dos produtos customizaveis associados está com quantidade maior de vendas que o estoque disponível', 422
        
        # associates product price and quantity in args to use later
        customizedProduct['customized_product_price'] = customProductQuery['customized_product_price']
        customizedProduct['customized_product_quantity'] = customProductQuery['customized_product_quantity']
        
        calculatedSaleValue += customProductQuery['customized_product_price'] * customizedProduct['customized_product_sale_quantity']

    # verifies with only two decimal places to avoid small precision differences between apps
    #if ('{:.2f}'.format(calculatedSaleValue-calculatedSaleValue*args['sale_total_discount_percentage'])) != '{:.2f}'.format(args['sale_total_value']):
    #  return 'Preço esperado diferente do preço calculado no sistema', 422
    
    dbObjectIns = startGetDbObject()
    try:
      # inserts sale and gets sale id
      dbExecute(
        ' INSERT INTO tbl_sale (sale_client_id, sale_employee_id, sale_total_discount_percentage, sale_total_value) VALUES '
        '   (%s, %s, %s, %s) ',
        [args['sale_client_id'], args['sale_employee_id'], args['sale_total_discount_percentage'], args['sale_total_value']],
        True, dbObjectIns)
      
      saleIdQuery = dbGetSingle(' SELECT LAST_INSERT_ID() AS sale_id; ', None, True, dbObjectIns)
      
      if not saleIdQuery:
        raise Exception('Exception empty select saleIdQuery after insert from tbl_sale put')
      
      # set installments
      for salePaymentMethodInstallment in args['sale_payment_method_installments']:
        dbExecute(
          ' INSERT INTO tbl_sale_has_payment_method_installment (sale_id, payment_method_installment_id, payment_method_value) VALUES (%s, %s, %s); ', 
          [saleIdQuery['sale_id'], salePaymentMethodInstallment['id'], salePaymentMethodInstallment['value']], True, dbObjectIns)
      
      for product in args['sale_has_products']:
        # set product immutable
        dbExecute(
          ' UPDATE tbl_product '
          '   SET is_product_immutable = TRUE '
          '   WHERE product_id = %s; ', [(product['product_id'])], True, dbObjectIns)
        
        for customizedProduct in product['customized_products']:
          # set customized product immutable and adjusts its quantity
          dbExecute(
            ' UPDATE tbl_customized_product '
            '   SET is_customized_product_immutable = TRUE, '
            '   customized_product_quantity = %s '
            '   WHERE customized_product_id = %s; ',
            [
              max(customizedProduct['customized_product_quantity'] - customizedProduct['customized_product_sale_quantity'], 0), 
              customizedProduct['customized_product_id']
            ], 
            True, dbObjectIns)
          
          # inserts sale has product
          dbExecute(
            ' INSERT INTO tbl_sale_has_product (sale_id, product_id, customized_product_id, sale_has_product_price, sale_has_product_quantity) VALUES '
            '   (%s, %s, %s, %s, %s); ', 
            [saleIdQuery['sale_id'], product['product_id'], customizedProduct['customized_product_id'], customizedProduct['customized_product_price'], customizedProduct['customized_product_sale_quantity']],
            True, dbObjectIns)
      
    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao criar a venda ' + str(e), 500
    dbCommit(dbObjectIns)
    
    return {}, 201
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('sale_id', location='args', type=int, help='sale id, required', required=True)
    argsParser.add_argument('generate_pdf', location='args', type=str, help='if the expected return is a file')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # sale
    saleQuery = dbGetSingle(
      ' SELECT * '
	    '   FROM tbl_sale s '
      '   JOIN ( '
      '     SELECT shpmi.sale_id, '
      '     GROUP_CONCAT(payment_method_name SEPARATOR \',\') AS payment_method_names, '
      '     GROUP_CONCAT(payment_method_installment_number SEPARATOR \',\') AS payment_method_installment_numbers, '
      '     GROUP_CONCAT(payment_method_value SEPARATOR \',\') AS payment_method_values '
      '       FROM tbl_sale_has_payment_method_installment shpmi '
      '       JOIN tbl_payment_method_installment pmi ON shpmi.payment_method_installment_id = pmi.payment_method_installment_id '
      '	      JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
      '     GROUP BY shpmi.sale_id '
      '   ) AS pms ON pms.sale_id = s.sale_id '
      '   WHERE s.sale_id = %s; ',
      [(args['sale_id'])])
    
    if not saleQuery:
      return 'Venda não encontrada', 404
    saleQuery['sale_creation_date_time'] = str(saleQuery['sale_creation_date_time'])
    
    # client
    saleQuery['sale_client'] = dbGetSingle(
      ' SELECT person_name AS client_name, person_cpf AS client_cpf, client_cep, client_adress, '
      ' client_city, client_neighborhood, client_state, client_number, client_complement '
	    '   FROM tbl_sale s '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person p ON c.client_id = p.person_id '
      '   WHERE s.sale_id = %s; ',
      [(args['sale_id'])])

    # product and customized products
    saleQuery['sale_products'] = dbGetAll(
      ' SELECT DISTINCT p.product_id, p.product_code, p.product_name, cp.customized_product_id, '
      ' shp.sale_has_product_price, shp.sale_has_product_quantity, '
      ' pc.product_color_name, po.product_other_name, ps.product_size_name '
      '   FROM tbl_sale s '
      '   JOIN tbl_sale_has_product shp ON s.sale_id = shp.sale_id '
      '   JOIN tbl_product p ON shp.product_id = p.product_id '
      '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
      '   JOIN tbl_product_size ps ON cp.product_size_id = ps.product_size_id '
      '   LEFT JOIN tbl_product_color pc ON cp.product_color_id = pc.product_color_id '
      '   LEFT JOIN tbl_product_other po ON cp.product_other_id = po.product_other_id '
      '   WHERE s.sale_id = %s AND shp.customized_product_id = cp.customized_product_id '
      '   ORDER BY product_code; ',
      [(args['sale_id'])])
    
    if args.get('generate_pdf') == 'true' or args.get('generate_pdf') == True:
      
      # create and remove the pdf file after(1 minute)
      pdfPath, pdfName = createSaleReport(saleQuery)
      delayedRemoveReport(pdfPath)

      # sends
      return send_file(pdfPath, as_attachment=True, download_name=pdfName)

    if not saleQuery.get('sale_products') or len(saleQuery['sale_products']) == 0:
      return 'Produtos da venda não encontrados', 404
    
    return saleQuery, 200
  
  # sale is never deleted, but it status changes to canceled
  def delete(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('sale_id', location='json', type=int, help='sale id, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    saleQuery = dbGetSingle(
      ' SELECT * '
	    '   FROM tbl_sale s ' 
      '   WHERE s.sale_id = %s; ',
      [(args['sale_id'])])
    
    if saleQuery['sale_status'] == 'Cancelado':
      return 'A venda já está cancelada', 401
    
    # products and customized products
    customSaleProducts = dbGetAll(
      ' SELECT DISTINCT shp.product_id, shp.customized_product_id, shp.sale_has_product_quantity '
      '   FROM tbl_sale s '
      '   JOIN tbl_sale_has_product shp ON s.sale_id = shp.sale_id '
      '   WHERE s.sale_id = %s; ',
      [(args['sale_id'])])
    
    dbObjectIns = startGetDbObject()
    try:
      for customProduct in customSaleProducts:
        customDbProduct = dbGetSingle(
          ' SELECT * '
          '   FROM tbl_customized_product cp ' 
          '   WHERE cp.customized_product_id = %s; ',
          (customProduct['customized_product_id'],),True, dbObjectIns
        )
        if not customDbProduct:
          raise Exception('Customized product not found while adding quantity to cancel sale')
        
        dbExecute(
          ' UPDATE tbl_customized_product SET '
          '   customized_product_quantity = %s '
          '   WHERE customized_product_id = %s; ',
          [ customDbProduct['customized_product_quantity'] + customProduct['sale_has_product_quantity'], customProduct['customized_product_id']]
          , True, dbObjectIns)

      dbExecute(' UPDATE tbl_sale SET sale_status = \'Cancelado\' WHERE sale_id = %s; ', [(args['sale_id'])], True, dbObjectIns)

    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao cancelar a venda ' + str(e), 500
    dbCommit(dbObjectIns)
    
    return {}, 204

class SalesApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='query limit')
    argsParser.add_argument('offset', location='args', type=int, help='query offset')
    argsParser.add_argument('order_by', location='args', type=str, help='query orderby', required=True)
    argsParser.add_argument('order_by_asc', location='args', type=str, help='query orderby ascendant', required=True)
    argsParser.add_argument('sale_id', location='args', type=int, help='sale id')
    argsParser.add_argument('sale_client_name', location='args', type=str, help='sale client name')
    argsParser.add_argument('sale_status', location='args', type=str, help='sale status')
    argsParser.add_argument('sale_creation_date_time_start', location='args', type=str, help='start of sale creation interval')
    argsParser.add_argument('sale_creation_date_time_end', location='args', type=str, help='end of sale creation interval')
    argsParser.add_argument('sale_total_value_start', location='args', type=str, help='start value of sale')
    argsParser.add_argument('sale_total_value_end', location='args', type=str, help='end value of sale')
    argsParser.add_argument('generate_pdf', location='args', type=str, help='if the expected return is a file')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    orderByAsc = (args['order_by_asc'] == '1' or args['order_by_asc'].lower() == 'true')
    
    if args.get('sale_creation_date_time_start'):
      try:
        datetime.datetime.strptime(args['sale_creation_date_time_start'], '%Y-%m-%dT%H:%M')
      except ValueError as err:
        return 'Data e hora de início inválida', 422
    
    if args.get('sale_creation_date_time_end'):
      try:
        datetime.datetime.strptime(args['sale_creation_date_time_end'], '%Y-%m-%dT%H:%M')
      except ValueError as err:
        return 'Data e hora de fim inválida', 422

    geralFilterScrypt, geralFilterScryptNoLimit, geralFilterArgs, geralFilterArgsNoLimit =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'s.sale_id', 'filterOperator':'=', 'filterValue':args.get('sale_id')},
        {'filterCollum':'p_client.person_name', 'filterOperator':'LIKE%_%', 'filterValue':args.get('sale_client_name')},
        {'filterCollum':'s.sale_status', 'filterOperator':'=', 'filterValue':args.get('sale_status')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'>=', 'filterValue':args.get('sale_creation_date_time_start')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'<=', 'filterValue':args.get('sale_creation_date_time_end')},
        {'filterCollum':'s.sale_total_value', 'filterOperator':'>=', 'filterValue':args.get('sale_total_value_start')},
        {'filterCollum':'s.sale_total_value', 'filterOperator':'<=', 'filterValue':args.get('sale_total_value_end')}
      ],
      orderByCollumns=args['order_by'], orderByAsc=orderByAsc, limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)
    
    sqlScrypt = (
      ' SELECT s.sale_id, s.sale_status, s.sale_total_discount_percentage, s.sale_creation_date_time, s.sale_total_value, '
      ' p_client.person_name AS sale_client_name, '
      ' p_employee.person_name AS sale_employee_name, '
      ' pms.payment_method_names, pms.payment_method_installment_numbers, pms.payment_method_values '
      '   FROM tbl_sale s '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person p_client ON c.client_id = p_client.person_id '
      '   JOIN tbl_employee e ON s.sale_employee_id = e.employee_id '
      '   JOIN tbl_person p_employee ON e.employee_id = p_employee.person_id '
      '   JOIN ( '
      '     SELECT shpmi.sale_id, '
      '     GROUP_CONCAT(payment_method_name SEPARATOR \',\') AS payment_method_names, '
      '     GROUP_CONCAT(payment_method_installment_number SEPARATOR \',\') AS payment_method_installment_numbers, '
      '     GROUP_CONCAT(payment_method_value SEPARATOR \',\') AS payment_method_values '
      '       FROM tbl_sale_has_payment_method_installment shpmi '
      '       JOIN tbl_payment_method_installment pmi ON shpmi.payment_method_installment_id = pmi.payment_method_installment_id '
      '	      JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
      '     GROUP BY shpmi.sale_id '
      '   ) AS pms ON pms.sale_id = s.sale_id '
      + geralFilterScrypt)
    
    sqlScryptNoLimit = (
      ' SELECT COUNT(DISTINCT s.sale_id) AS total_quantity, '
      ' CAST(SUM(shpmi.payment_method_value) AS UNSIGNED) AS total_value, '
      ' SUM(CASE WHEN pm.payment_method_name="Pix" THEN shpmi.payment_method_value ELSE 0 END) pix_value, '
      ' CAST(SUM(pm.payment_method_name="Pix") AS UNSIGNED) AS pix_quantity, '
      ' SUM(CASE WHEN pm.payment_method_name="Dinheiro" THEN shpmi.payment_method_value ELSE 0 END) dinheiro_value, '
      ' CAST(SUM(pm.payment_method_name="Dinheiro") AS UNSIGNED) AS dinheiro_quantity, '
      ' SUM(CASE WHEN pm.payment_method_name="Cheque" THEN shpmi.payment_method_value ELSE 0 END) cheque_value, '
      ' CAST(SUM(pm.payment_method_name="Cheque") AS UNSIGNED) AS cheque_quantity, '
      ' SUM(CASE WHEN pm.payment_method_name="Cartão de débito" THEN shpmi.payment_method_value ELSE 0 END) debito_value, '
      ' CAST(SUM(pm.payment_method_name="Cartão de débito") AS UNSIGNED) AS debito_quantity, '
      ' SUM(CASE WHEN pm.payment_method_name="Cartão de crédito" THEN shpmi.payment_method_value ELSE 0 END) credito_value, '
      ' CAST(SUM(pm.payment_method_name="Cartão de crédito") AS UNSIGNED) AS credito_quantity '
      '   FROM tbl_sale s '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person p_client ON c.client_id = p_client.person_id '
      '   JOIN tbl_employee e ON s.sale_employee_id = e.employee_id '
      '   JOIN tbl_person p_employee ON e.employee_id = p_employee.person_id '
      '   JOIN tbl_sale_has_payment_method_installment shpmi ON s.sale_id = shpmi.sale_id '
      '   JOIN tbl_payment_method_installment pmi ON shpmi.payment_method_installment_id = pmi.payment_method_installment_id '
      '	  JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
      + geralFilterScryptNoLimit)

    salesSummary = dbGetSingle(sqlScryptNoLimit, geralFilterArgsNoLimit)
    salesQuery = dbGetAll(sqlScrypt, geralFilterArgs)

    # pdf creation
    if args.get('generate_pdf') == 'true' or args.get('generate_pdf') == True:

      # filters
      filters = []

      if args.get('sale_id'):
        filters.append(f"Código: {args.get('sale_id')}")

      if args.get('sale_client_name'):
        filters.append(f"Nome do cliente: {args.get('sale_client_name')}")

      if args.get('sale_status'):
        filters.append(f"Status: {args.get('sale_status')}")

      if args.get('sale_creation_date_time_start'):
        filters.append(f"Criado, de: {datetime.datetime.strptime(args['sale_creation_date_time_start'], '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')}")

      if args.get('sale_creation_date_time_end'):
        filters.append(f"Criado, até: {datetime.datetime.strptime(args['sale_creation_date_time_end'], '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')}")
        
      if args.get('sale_total_value_start'):
        filters.append(f"Valor, de: {toBRCurrency(float(args.get('sale_total_value_start')))}")

      if args.get('sale_total_value_end'):
        filters.append(f"Valor, até: {toBRCurrency(float(args.get('sale_total_value_end')))}")
      
      appliedOrderStr = f"Ordenado em ordem {'ascendente' if orderByAsc else 'decrescente'} por "

      if args['order_by'] == 'sale_id':
        appliedOrderStr += 'código'
      elif args['order_by'] == 'sale_creation_date_time':
        appliedOrderStr += 'data e hora de geração'
      elif args['order_by'] == 'sale_client_name':
        appliedOrderStr += 'nome do cliente'
      elif args['order_by'] == 'sale_status':
        appliedOrderStr += 'status'
      elif args['order_by'] == 'sale_total_value':
        appliedOrderStr += 'valor final'
      
      filters.append(appliedOrderStr)

      # create and remove the pdf file after(1 minute)
      pdfPath, pdfName = createSalesReport(filters, salesSummary, salesQuery)
      delayedRemoveReport(pdfPath)

      # sends
      return send_file(pdfPath, as_attachment=True, download_name=pdfName)

    if not salesSummary or not salesQuery:
      return { 'total_quantity': 0, 'sales': [] }, 200

    for saleRow in salesQuery:
      saleRow['sale_creation_date_time'] = str(saleRow['sale_creation_date_time'])

    return { 'total_quantity': salesSummary['total_quantity'], 'sales': salesQuery, 'summary': salesSummary }, 200
  
class SaleInfoApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    query = dbGetSingle(
      ' SELECT AUTO_INCREMENT AS next_sale_id FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s; ',
      [os.getenv('SQL_SCHEMA'), 'tbl_sale'])
    
    query['payment_methods'] = dbGetAll(
      ' SELECT pmi.payment_method_installment_id, pm.payment_method_name, pm.payment_method_id, pmi.payment_method_installment_number '
      '   FROM tbl_payment_method pm '
      '   JOIN tbl_payment_method_installment pmi ON pm.payment_method_id = pmi.payment_method_id; ')
    
    return query, 200