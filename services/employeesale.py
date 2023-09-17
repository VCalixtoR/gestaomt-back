from flask import Flask, abort
from flask_restful import Resource, Api, reqparse

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

class EmployeeSalesApi(Resource):
    
  def get(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='number of rows returned, required', required=True)
    argsParser.add_argument('offset', location='args', type=int, help='start row from db, required', required=True)
    argsParser.add_argument('employee_id', location='args', type=str, help='event user id, required', required=True)
    argsParser.add_argument('start_date', location='args', type=str, help='start event date filter')
    argsParser.add_argument('end_date', location='args', type=str, help='end event date filter')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    geralFilterScrypt, geralFilterScryptNoLimit, geralFilterArgs, geralFilterArgsNoLimit =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'e.employee_id', 'filterOperator':'=', 'filterValue':args.get('employee_id')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'>=', 'filterValue':args.get('start_date')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'<=', 'filterValue':args.get('end_date')}
      ],
      orderByCollumns='s.sale_creation_date_time', limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)

    salesQuery = dbGetAll(
      ' SELECT s.sale_id, cp.person_name AS client_name, pms.payment_method_names, pms.payment_method_installment_numbers, '
      ' s.sale_creation_date_time, s.sale_total_value, e.employee_comission '
      '   FROM tbl_employee e '
      '   JOIN tbl_sale s ON e.employee_id = s.sale_employee_id '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person cp ON c.client_id = cp.person_id '
      '   JOIN ( '
      '     SELECT shpmi.sale_id, '
      '     GROUP_CONCAT(payment_method_name SEPARATOR \',\') AS payment_method_names, '
      '     GROUP_CONCAT(payment_method_installment_number SEPARATOR \',\') AS payment_method_installment_numbers '
      '       FROM tbl_sale_has_payment_method_installment shpmi '
      '       JOIN tbl_payment_method_installment pmi ON shpmi.payment_method_installment_id = pmi.payment_method_installment_id '
      '	      JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
      '     GROUP BY shpmi.sale_id '
      '   ) AS pms ON pms.sale_id = s.sale_id '
      + geralFilterScrypt, geralFilterArgs)
    
    countQuery = dbGetSingle(
      ' SELECT COUNT(*) AS countemps '
      '   FROM tbl_employee e '
      '   JOIN tbl_sale s ON e.employee_id = s.sale_employee_id '
      '   JOIN tbl_client c ON s.sale_client_id = c.client_id '
      '   JOIN tbl_person cp ON c.client_id = cp.person_id '
      '   JOIN ( '
      '     SELECT shpmi.sale_id, '
      '     GROUP_CONCAT(payment_method_name SEPARATOR \',\') AS payment_method_names, '
      '     GROUP_CONCAT(payment_method_installment_number SEPARATOR \',\') AS payment_method_installment_numbers '
      '       FROM tbl_sale_has_payment_method_installment shpmi '
      '       JOIN tbl_payment_method_installment pmi ON shpmi.payment_method_installment_id = pmi.payment_method_installment_id '
      '	      JOIN tbl_payment_method pm ON pmi.payment_method_id = pm.payment_method_id '
      '     GROUP BY shpmi.sale_id '
      '   ) AS pms ON pms.sale_id = s.sale_id '
      + geralFilterScryptNoLimit, geralFilterArgsNoLimit)
    
    if not countQuery or not salesQuery:
      return { 'count_sales': 0, 'sales': [] }, 200
    
    for saleRow in salesQuery:
      saleRow['sale_creation_date_time'] = str(saleRow['sale_creation_date_time'])
      saleRow['sale_employee_comission'] = saleRow['sale_total_value'] * saleRow['employee_comission']

    return { 'count_sales': countQuery['countemps'], 'sales': salesQuery }, 200

class EmployeeSalesSummaryApi(Resource):

  def get(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('employee_id', location='args', type=int, help='event user id, required', required=True)
    argsParser.add_argument('start_date', location='args', type=str, help='start event date filter')
    argsParser.add_argument('end_date', location='args', type=str, help='end event date filter')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    employeeQuery = dbGetSingle(
      ' SELECT * FROM tbl_employee e WHERE e.employee_id = %s; ', [(args['employee_id'])])
    
    if not employeeQuery:
      return 'Funcionário não encontrado!', 404
    if not employeeQuery['employee_active']:
      return 'Funcionário não está ativo!', 401
    
    filterPaymentCountScrypt, filterPaymentCountArgs =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'s.sale_employee_id', 'filterOperator':'=', 'filterValue':args.get('employee_id')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'>=', 'filterValue':args.get('start_date')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'<=', 'filterValue':args.get('end_date')}
      ],
      groupByCollumns='pmi.payment_method_id', filterEnding='')

    filterSalesCountScrypt, filterSalesCountArgs =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'s.sale_employee_id', 'filterOperator':'=', 'filterValue':args.get('employee_id')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'>=', 'filterValue':args.get('start_date')},
        {'filterCollum':'s.sale_creation_date_time', 'filterOperator':'<=', 'filterValue':args.get('end_date')}
      ],
      filterEnding='')

    paymentSaleQuery = dbGetAll(
      '  SELECT pm.payment_method_name, payment_methods_count, payment_methods_value '
	    '   FROM tbl_payment_method pm  '
      '   LEFT JOIN ( '
		  '     SELECT pmi.payment_method_id, COUNT(sale_has_payment_method_installment_id) AS payment_methods_count, SUM(payment_method_value) AS payment_methods_value '
      '       FROM tbl_sale s '
			'       JOIN tbl_sale_has_payment_method_installment shpmi ON s.sale_id = shpmi.sale_id '
      '       JOIN tbl_payment_method_installment pmi ON shpmi.payment_method_installment_id = pmi.payment_method_installment_id '
      + filterPaymentCountScrypt +
      '   ) AS payment_calc ON pm.payment_method_id = payment_calc.payment_method_id; ', filterPaymentCountArgs)

    totalSaleQuery = dbGetSingle(
      '  SELECT COUNT(s.sale_id) AS sales_count, SUM(shpmi.payment_method_value) AS sales_value '
      '       FROM tbl_sale s '
      '       JOIN tbl_sale_has_payment_method_installment shpmi ON s.sale_id = shpmi.sale_id '
      + filterSalesCountScrypt, filterSalesCountArgs)
      
    if not paymentSaleQuery:
      return 'Pagamentos não encontrados!', 404
    
    for paymentRow in paymentSaleQuery:

      if not paymentRow['payment_methods_count'] or not paymentRow['payment_methods_value']:
        paymentRow['payment_methods_count'] = 0
        paymentRow['payment_methods_value'] = 0

      paymentRow['payment_methods_comission_value'] = paymentRow['payment_methods_value'] * employeeQuery['employee_comission']

    if not totalSaleQuery or not totalSaleQuery['sales_count'] or not totalSaleQuery['sales_value']:
      totalSaleQuery['sales_count'] = 0
      totalSaleQuery['sales_value'] = 0
    
    totalSaleQuery['sales_comission'] = totalSaleQuery['sales_value'] * employeeQuery['employee_comission']

    return { 'payments' : paymentSaleQuery, 'sales': totalSaleQuery }, 200