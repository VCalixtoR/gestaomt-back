from flask import Flask, abort, send_file
from flask_restful import Resource, Api, reqparse
import datetime
import traceback

from utils.dbUtils import *
from utils.generatePDFReport import createConditionalReport, createConditionalsReport, delayedRemoveReport
from services.authentication import isAuthTokenValid

class ConditionalApi(Resource):

  def put(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('conditional_client_id', location='json', type=int, help='conditional client id, required', required=True)
    argsParser.add_argument('conditional_employee_id', location='json', type=int, help='conditional employee id, required', required=True)
    argsParser.add_argument('conditional_has_products', location='json', type=list, help='products and its variations list, required', required=True)
    argsParser.add_argument('force_product_addition', location='json', type=str, help='if will add missing products in conditional creation, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    forceProductAddition = args['force_product_addition'].lower() in ['true', '1']

    # test client
    clientQuery = dbGetSingle(
      ' SELECT * FROM tbl_client c '
      '   JOIN tbl_person p ON c.client_id = p.person_id '
      '   WHERE c.client_id = %s; ', [(args['conditional_client_id'])])
    if not clientQuery:
      return 'O cliente associado à condicional não existe no sistema', 422
    
    # test employee
    employeeQuery = dbGetSingle(
      ' SELECT p.person_name, p.person_gender, u.user_type, u.user_entry_allowed, e.employee_active, e.employee_id '
      '   FROM tbl_employee e '
      '   JOIN tbl_user u ON e.employee_id = u.user_id '
      '   JOIN tbl_person p ON u.user_id = p.person_id '
      '   WHERE e.employee_id = %s; ', [(args['conditional_employee_id'])])
    if not employeeQuery:
      return 'O funcionario associado à condicional não existe no sistema', 422
    if not employeeQuery['user_entry_allowed'] or not employeeQuery['employee_active']:
      return 'O funcionario associado à condicional não esta habilitado no sistema', 422

    # test conditional products
    if len(args['conditional_has_products']) == 0:
      return 'A condicional deve possuir pelo menos um produto associado', 422

    for product in args['conditional_has_products']:
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
        if not customizedProduct.get('customized_product_conditional_quantity'):
          return 'Um dos produtos customizaveis associados foi enviado sem o campo customized_product_conditional_quantity', 422
        if customizedProduct['customized_product_conditional_quantity'] <= 0:
          return 'Um dos produtos associados possui quantidade de produtos 0 ou menor', 422

        customProductQuery = dbGetSingle(
          ' SELECT cp.is_customized_product_active, cp.customized_product_quantity '
          '   FROM tbl_product p '
          '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
          '   WHERE p.product_id = %s AND cp.customized_product_id = %s; ',
          [product['product_id'], customizedProduct['customized_product_id']])
        
        if not customProductQuery:
          return 'Um dos produtos customizaveis associados não foi encontrado no sistema', 422
        if not customProductQuery['is_customized_product_active']:
          return 'Um dos produtos customizaveis associados está inativo', 422
        if not forceProductAddition and customizedProduct['customized_product_conditional_quantity'] > customProductQuery['customized_product_quantity']:
          return 'Um dos produtos customizaveis associados está com quantidade maior que o estoque disponível', 422
        
        # associates product quantity in args to use later
        customizedProduct['customized_product_quantity'] = customProductQuery['customized_product_quantity']

    dbObjectIns = startGetDbObject()
    try:
      # inserts conditional and gets its id
      dbExecute(
        ' INSERT INTO tbl_conditional (conditional_client_id, conditional_employee_id) VALUES '
        '   (%s, %s) ',
        [args['conditional_client_id'], args['conditional_employee_id']], True, dbObjectIns)
      
      conditionalIdQuery = dbGetSingle(' SELECT LAST_INSERT_ID() AS conditional_id; ', None, True, dbObjectIns)
      
      if not conditionalIdQuery:
        raise Exception('Exception empty select conditionalIdQuery after insert from tbl_conditional put')
      
      for product in args['conditional_has_products']:
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
              max(customizedProduct['customized_product_quantity'] - customizedProduct['customized_product_conditional_quantity'], 0),
              customizedProduct['customized_product_id']
            ], 
            True, dbObjectIns)
          
          # inserts conditional has product
          dbExecute(
            ' INSERT INTO tbl_conditional_has_product (conditional_id, product_id, customized_product_id, conditional_has_product_quantity) VALUES '
            '   (%s, %s, %s, %s); ', 
            [conditionalIdQuery['conditional_id'], product['product_id'], customizedProduct['customized_product_id'], customizedProduct['customized_product_conditional_quantity']],
            True, dbObjectIns)
      
    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao criar a condicional ' + str(e), 500
    dbCommit(dbObjectIns)
    
    return {}, 201
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('conditional_id', location='args', type=int, help='conditional id, required', required=True)
    argsParser.add_argument('generate_pdf', location='args', type=str, help='if the expected return is a file')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # conditional
    conditionalQuery = dbGetSingle(
      ' SELECT * '
	    '   FROM tbl_conditional c ' 
      '   WHERE c.conditional_id = %s; ',
      [(args['conditional_id'])])
    
    if not conditionalQuery:
      return 'Condicional não encontrada', 404
    conditionalQuery['conditional_creation_date_time'] = str(conditionalQuery['conditional_creation_date_time'])
    
    # client
    conditionalQuery['conditional_client'] = dbGetSingle(
      ' SELECT person_name AS client_name, person_cpf AS client_cpf, client_cep, client_adress, '
      ' client_city, client_neighborhood, client_state, client_number, client_complement '
	    '   FROM tbl_conditional cond '
      '   JOIN tbl_client cli ON cond.conditional_client_id = cli.client_id '
      '   JOIN tbl_person p ON cli.client_id = p.person_id '
      '   WHERE cond.conditional_id = %s; ',
      [(args['conditional_id'])])

    # product and customized products
    conditionalQuery['conditional_products'] = dbGetAll(
      ' SELECT DISTINCT p.product_id, p.product_code, p.product_name, cp.customized_product_id, '
      ' chp.conditional_has_product_quantity, '
      ' pc.product_color_name, po.product_other_name, ps.product_size_name '
      '   FROM tbl_conditional c '
      '   JOIN tbl_conditional_has_product chp ON c.conditional_id = chp.conditional_id '
      '   JOIN tbl_product p ON chp.product_id = p.product_id '
      '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
      '   JOIN tbl_product_size ps ON cp.product_size_id = ps.product_size_id '
      '   LEFT JOIN tbl_product_color pc ON cp.product_color_id = pc.product_color_id '
      '   LEFT JOIN tbl_product_other po ON cp.product_other_id = po.product_other_id '
      '   WHERE c.conditional_id = %s AND chp.customized_product_id = cp.customized_product_id '
      '   ORDER BY p.product_code; ',
      [(args['conditional_id'])])
    
    if args.get('generate_pdf') == 'true' or args.get('generate_pdf') == True:
      
      # create and remove the pdf file after(1 minute)
      pdfPath, pdfName = createConditionalReport(conditionalQuery)
      delayedRemoveReport(pdfPath)

      # sends
      return send_file(pdfPath, as_attachment=True, download_name=pdfName)
    
    if not conditionalQuery.get('conditional_products') or len(conditionalQuery['conditional_products']) == 0:
      return 'Produtos da Condicional não encontrados', 404
    
    return conditionalQuery, 200
  
  # patch to change conditional status
  def patch(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('conditional_id', location='json', type=int, help='conditional id, required', required=True)
    argsParser.add_argument('conditional_status', location='json', type=str, help='conditional status, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    if args['conditional_status'] not in ['Pendente', 'Devolvido', 'Cancelado']:
      return 'Status inválido', 422

    # conditional is never deleted, but it status changes to canceled
    conditionalQuery = dbGetSingle(
      ' SELECT * '
	    '   FROM tbl_conditional c ' 
      '   WHERE c.conditional_id = %s; ',
      [(args['conditional_id'])])
    
    if conditionalQuery['conditional_status'] == 'Cancelado':
      return 'A condicional está cancelada e não pode ser alterada', 401
    if conditionalQuery['conditional_status'] == 'Devolvido':
      return 'A condicional está Devolvida e não pode ser alterada', 401
    if conditionalQuery['conditional_status'] == args['conditional_status']:
      return {}, 204
    
    # products and customized products
    customConditionalProducts = dbGetAll(
      ' SELECT DISTINCT chp.product_id, chp.customized_product_id, chp.conditional_has_product_quantity '
      '   FROM tbl_conditional c '
      '   JOIN tbl_conditional_has_product chp ON c.conditional_id = chp.conditional_id '
      '   WHERE c.conditional_id = %s; ',
      [(args['conditional_id'])])
    
    dbObjectIns = startGetDbObject()
    try:
      for customProduct in customConditionalProducts:
        customDbProduct = dbGetSingle(
          ' SELECT * '
          '   FROM tbl_customized_product cp ' 
          '   WHERE cp.customized_product_id = %s; ',
          (customProduct['customized_product_id'],),True, dbObjectIns
        )
        if not customDbProduct:
          raise Exception('Customized product not found while adding quantity to change conditional status')
        print(customProduct)
        print(customDbProduct)
        print(customDbProduct['customized_product_quantity'] + customProduct['conditional_has_product_quantity'])
        
        dbExecute(
          ' UPDATE tbl_customized_product SET '
          '   customized_product_quantity = %s '
          '   WHERE customized_product_id = %s; ',
          [ customDbProduct['customized_product_quantity'] + customProduct['conditional_has_product_quantity'], customProduct['customized_product_id']]
          , True, dbObjectIns)

      dbExecute(' UPDATE tbl_conditional SET conditional_status = %s WHERE conditional_id = %s; ', 
        [args['conditional_status'], args['conditional_id']], True, dbObjectIns)

    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao cancelar a condicional ' + str(e), 500
    dbCommit(dbObjectIns)
    
    return {}, 204

class ConditionalsApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='query limit')
    argsParser.add_argument('offset', location='args', type=int, help='query offset')
    argsParser.add_argument('order_by', location='args', type=str, help='query orderby', required=True)
    argsParser.add_argument('order_by_asc', location='args', type=str, help='query orderby ascendant', required=True)
    argsParser.add_argument('conditional_id', location='args', type=int, help='conditional id')
    argsParser.add_argument('conditional_client_name', location='args', type=str, help='conditional client name')
    argsParser.add_argument('conditional_status', location='args', type=str, help='conditional status')
    argsParser.add_argument('conditional_creation_date_time_start', location='args', type=str, help='start of conditional creation interval')
    argsParser.add_argument('conditional_creation_date_time_end', location='args', type=str, help='end of conditional creation interval')
    argsParser.add_argument('generate_pdf', location='args', type=str, help='if the expected return is a file')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    orderByAsc = (args['order_by_asc'] == '1' or args['order_by_asc'].lower() == 'true')
    
    if args.get('conditional_creation_date_time_start'):
      try:
        datetime.datetime.strptime(args['conditional_creation_date_time_start'], '%Y-%m-%dT%H:%M')
      except ValueError as err:
        return 'Data e hora de início inválida', 422
    
    if args.get('conditional_creation_date_time_end'):
      try:
        datetime.datetime.strptime(args['conditional_creation_date_time_end'], '%Y-%m-%dT%H:%M')
      except ValueError as err:
        return 'Data e hora de fim inválida', 422

    geralFilterScrypt, geralFilterScryptNoLimit, geralFilterArgs, geralFilterArgsNoLimit =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'cond.conditional_id', 'filterOperator':'=', 'filterValue':args.get('conditional_id')},
        {'filterCollum':'p_client.person_name', 'filterOperator':'LIKE%_%', 'filterValue':args.get('conditional_client_name')},
        {'filterCollum':'cond.conditional_status', 'filterOperator':'=', 'filterValue':args.get('conditional_status')},
        {'filterCollum':'cond.conditional_creation_date_time', 'filterOperator':'>=', 'filterValue':args.get('conditional_creation_date_time_start')},
        {'filterCollum':'cond.conditional_creation_date_time', 'filterOperator':'<=', 'filterValue':args.get('conditional_creation_date_time_end')}
      ],
      orderByCollumns=args['order_by'], orderByAsc=orderByAsc, limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)
    
    sqlScrypt = (
      ' SELECT cond.conditional_id, cond.conditional_status, cond.conditional_creation_date_time, '
      ' p_client.person_name AS conditional_client_name, '
      ' p_employee.person_name AS conditional_employee_name '
      '   FROM tbl_conditional cond '
      '   JOIN tbl_client cli ON cond.conditional_client_id = cli.client_id '
      '   JOIN tbl_person p_client ON cli.client_id = p_client.person_id '
      '   JOIN tbl_employee e ON cond.conditional_employee_id = e.employee_id '
      '   JOIN tbl_person p_employee ON e.employee_id = p_employee.person_id '
      + geralFilterScrypt)
    
    sqlScryptNoCount = (
      ' SELECT COUNT(*) AS total_quantity, '
      ' CAST(SUM(cond.conditional_status="Cancelado") AS UNSIGNED) AS canceled_quantity, '
      ' CAST(SUM(cond.conditional_status="Pendente") AS UNSIGNED) AS pending_quantity, '
      ' CAST(SUM(cond.conditional_status="Devolvido") AS UNSIGNED) AS returned_quantity '
      '   FROM tbl_conditional cond '
      '   JOIN tbl_client cli ON cond.conditional_client_id = cli.client_id '
      '   JOIN tbl_person p_client ON cli.client_id = p_client.person_id '
      '   JOIN tbl_employee e ON cond.conditional_employee_id = e.employee_id '
      '   JOIN tbl_person p_employee ON e.employee_id = p_employee.person_id '
      + geralFilterScryptNoLimit)
    
    conditionalsSummary = dbGetSingle(sqlScryptNoCount, geralFilterArgsNoLimit)
    conditionalsQuery = dbGetAll(sqlScrypt, geralFilterArgs)
    
    # pdf creation
    if args.get('generate_pdf') == 'true' or args.get('generate_pdf') == True:

      # filters
      filters = []

      if args.get('conditional_id'):
        filters.append(f"Código: {args.get('conditional_id')}")

      if args.get('conditional_client_name'):
        filters.append(f"Nome do cliente: {args.get('conditional_client_name')}")

      if args.get('conditional_status'):
        filters.append(f"Status: {args.get('conditional_status')}")

      if args.get('conditional_creation_date_time_start'):
        filters.append(f"Criado, de: {datetime.datetime.strptime(args['conditional_creation_date_time_start'], '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')}")

      if args.get('conditional_creation_date_time_end'):
        filters.append(f"Criado, até: {datetime.datetime.strptime(args['conditional_creation_date_time_end'], '%Y-%m-%dT%H:%M').strftime('%d/%m/%Y %H:%M')}")
      
      appliedOrderStr = f"Ordenado em ordem {'ascendente' if orderByAsc else 'decrescente'} por "

      if args['order_by'] == 'conditional_id':
        appliedOrderStr += 'código'
      elif args['order_by'] == 'conditional_creation_date_time':
        appliedOrderStr += 'data e hora de geração'
      elif args['order_by'] == 'conditional_client_name':
        appliedOrderStr += 'nome do cliente'
      elif args['order_by'] == 'conditional_status':
        appliedOrderStr += 'status'
      
      filters.append(appliedOrderStr)

      # create and remove the pdf file after(1 minute)
      pdfPath, pdfName = createConditionalsReport(filters, conditionalsSummary, conditionalsQuery)
      delayedRemoveReport(pdfPath)

      # sends
      return send_file(pdfPath, as_attachment=True, download_name=pdfName)

    if not conditionalsSummary or not conditionalsQuery:
      return { 'total_quantity': 0, 'conditionals': [] }, 200

    for conditionalRow in conditionalsQuery:
      conditionalRow['conditional_creation_date_time'] = str(conditionalRow['conditional_creation_date_time'])
    
    return { 'total_quantity': conditionalsSummary['total_quantity'], 'conditionals': conditionalsQuery, 'summary': conditionalsSummary }, 200

class ConditionalInfoApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    query = dbGetSingle(
      ' SELECT AUTO_INCREMENT AS next_conditional_id FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s; ',
      [os.getenv('SQL_SCHEMA'), 'tbl_conditional'])
    
    return query, 200