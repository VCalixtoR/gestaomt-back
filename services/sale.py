from flask import Flask, abort
from flask_restful import Resource, Api, reqparse
import traceback
import os

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

class SaleApi(Resource):

  def put(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('sale_client_id', location='json', type=int, help='sale client id, required', required=True)
    argsParser.add_argument('sale_employee_id', location='json', type=int, help='sale employee id, required', required=True)
    argsParser.add_argument('sale_payment_method_installment_id', location='json', type=int, help='sale payment method installment id, required', required=True)
    argsParser.add_argument('sale_has_products', location='json', type=list, help='product and its variations list, required', required=True)
    argsParser.add_argument('sale_total_discount_percentage', location='json', type=float, help='sale total discount percentage float, required and can be 0.0', required=True)
    argsParser.add_argument('sale_total_value', location='json', type=float, help='sale total value float, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

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

    # test payment method installment
    payMethodQuery = dbGetSingle(
      ' SELECT pm.payment_method_name, pmi.payment_method_Installment_number '
      '   FROM tbl_payment_method pm '
      '   JOIN tbl_payment_method_installment pmi ON pm.payment_method_id = pmi.payment_method_id '
      '   WHERE pmi.payment_method_installment_id = %s; ', [(args['sale_payment_method_installment_id'])])
    if not payMethodQuery:
      return 'A forma de pagamento associado à venda não existe no sistema', 422

    # test sale total discount percentage
    if args['sale_total_discount_percentage'] < 0.0:
      return 'O desconto na venda não pode ser menor que 0', 422
    if args['sale_total_discount_percentage'] >= 100.0:
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
        if customizedProduct['customized_product_sale_quantity'] > customProductQuery['customized_product_quantity']:
          return 'Um dos produtos customizaveis associados está com quantidade maior de vendas que o estoque disponível', 422
        
        # associates product price and quantity in args to use later
        customizedProduct['customized_product_price'] = customProductQuery['customized_product_price']
        customizedProduct['customized_product_quantity'] = customProductQuery['customized_product_quantity']
        
        calculatedSaleValue += customProductQuery['customized_product_price'] * customizedProduct['customized_product_sale_quantity']

    # verifies with only two decimal places to avoid small precision differences between apps
    if ('{:.2f}'.format(calculatedSaleValue-calculatedSaleValue*args['sale_total_discount_percentage'])) != '{:.2f}'.format(args['sale_total_value']):
      return 'Preço esperado diferente do preço calculado no sistema', 422
    
    dbObjectIns = startGetDbObject()
    try:
      # inserts sale and gets sale id
      dbExecute(
        ' INSERT INTO tbl_sale (sale_client_id, sale_employee_id, sale_payment_method_installment_id, sale_total_discount_percentage, sale_total_value) VALUES '
        '   (%s, %s, %s, %s, %s) ',
        [args['sale_client_id'], args['sale_employee_id'], args['sale_payment_method_installment_id'], args['sale_total_discount_percentage'], args['sale_total_value']],
        True, dbObjectIns)
      
      saleIdQuery = dbGetSingle(' SELECT LAST_INSERT_ID() AS sale_id; ', None, True, dbObjectIns)
      
      if not saleIdQuery:
        raise Exception('Exception empty select saleIdQuery after insert from tbl_sale put')
      
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
              (customizedProduct['customized_product_quantity'] - customizedProduct['customized_product_sale_quantity']), 
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
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # sale
    saleQuery = dbGetSingle(
      ' SELECT * '
	    '   FROM tbl_sale s '
      '   JOIN tbl_payment_method_installment pmi ON s.sale_payment_method_installment_id = pmi.payment_method_installment_id '
      '   JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
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
      '   JOIN tbl_product_color pc ON cp.product_color_id = pc.product_color_id '
      '   JOIN tbl_product_other po ON cp.product_other_id = po.product_other_id '
      '   JOIN tbl_product_size ps ON cp.product_size_id = ps.product_size_id '
      '   WHERE s.sale_id = %s AND shp.customized_product_id = cp.customized_product_id '
      '   ORDER BY product_code; ',
      [(args['sale_id'])])
    
    if not saleQuery.get('sale_products') or len(saleQuery['sale_products']) == 0:
      return 'Produtos da venda não encontrados', 404
    
    return saleQuery, 200
  
  def delete(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('sale_id', location='json', type=int, help='sale id, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # sale is never deleted, but it status changes to canceled
    saleQuery = dbGetSingle(
      ' SELECT * '
	    '   FROM tbl_sale s ' 
      '   WHERE s.sale_id = %s; ',
      [(args['sale_id'])])
    
    if saleQuery['sale_status'] == 'Cancelado':
      return 'A venda já está cancelada', 401
    
    dbExecute(' UPDATE tbl_sale SET sale_status = \'Cancelado\' WHERE sale_id = %s; ', [(args['sale_id'])])
    
    return {}, 204

class SalesApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='query limit, required', required=True)
    argsParser.add_argument('offset', location='args', type=int, help='query offset, required', required=True)
    argsParser.add_argument('sale_id', location='args', type=int, help='sale id')
    argsParser.add_argument('sale_client_name', location='args', type=str, help='sale client name')
    argsParser.add_argument('sale_status', location='args', type=str, help='sale status')
    argsParser.add_argument('sale_creation_date_time_start', location='args', type=str, help='start of sale creation interval')
    argsParser.add_argument('sale_creation_date_time_end', location='args', type=str, help='end of sale creation interval')
    argsParser.add_argument('sale_total_value_start', location='args', type=str, help='start value of sale')
    argsParser.add_argument('sale_total_value_end', location='args', type=str, help='end value of sale')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

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
      orderByCollumns='s.sale_id', limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)
    
    sqlScrypt = (
      ' SELECT s.sale_id, s.sale_status, s.sale_total_discount_percentage, s.sale_creation_date_time, s.sale_total_value, '
      ' p_client.person_name AS sale_client_name, '
      ' p_employee.person_name AS sale_employee_name, '
      ' pm.payment_method_name, pmi.payment_method_Installment_number '
      '   FROM tbl_sale s '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person p_client ON c.client_id = p_client.person_id '
      '   JOIN tbl_employee e ON s.sale_employee_id = e.employee_id '
      '   JOIN tbl_person p_employee ON e.employee_id = p_employee.person_id '
      '   JOIN tbl_payment_method_installment pmi ON s.sale_payment_method_installment_id = pmi.payment_method_installment_id '
      '   JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
      + geralFilterScrypt)
    
    sqlScryptNoCount = (
      ' SELECT COUNT(*) AS counts '
      '   FROM tbl_sale s '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person p_client ON c.client_id = p_client.person_id '
      '   JOIN tbl_employee e ON s.sale_employee_id = e.employee_id '
      '   JOIN tbl_user u ON e.employee_id = u.user_id '
      '   JOIN tbl_person p_employee ON u.user_id = p_employee.person_id '
      + geralFilterScryptNoLimit)
    
    countSales = dbGetSingle(sqlScryptNoCount, geralFilterArgsNoLimit)
    salesQuery = dbGetAll(sqlScrypt, geralFilterArgs)

    if not countSales or not salesQuery:
      return { 'count': 0, 'sales': [] }, 200

    for saleRow in salesQuery:
      saleRow['sale_creation_date_time'] = str(saleRow['sale_creation_date_time'])
    
    return { 'count': countSales['counts'], 'sales': salesQuery }, 200
  
class SaleInfoApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    query = dbGetSingle(
      ' SELECT AUTO_INCREMENT AS last_sale_id FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s; ',
      [os.getenv('SQL_SCHEMA'), 'tbl_sale'])
    
    query['payment_methods'] = dbGetAll(
      ' SELECT pmi.payment_method_installment_id, pm.payment_method_name, pmi.payment_method_Installment_number '
      '   FROM tbl_payment_method pm '
      '   JOIN tbl_payment_method_installment pmi ON pm.payment_method_id = pmi.payment_method_id; ')
    
    return query, 200