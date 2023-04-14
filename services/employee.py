from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import Flask, abort
from flask_restful import Resource, Api, reqparse

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

def getEmployeeFromDB(employeeId):
    
  employeeQuery = dbGetSingle(
    ' SELECT employee_id, employee_active, employee_comission, person_name AS employee_name, user_mail AS employee_mail, '
    ' person_birth_date AS employee_birth_date, user_entry_date_time AS employee_entry_date_time '
    '   FROM tbl_person p '
    '   JOIN tbl_user u ON p.person_id = u.user_id '
    '   JOIN tbl_employee e ON u.user_id = e.employee_id '
    '     WHERE employee_id = %s AND user_type = \'E\'; ',
    [(employeeId)])
  
  if employeeQuery == None:
    return None
    
  return {
    'id': employeeQuery['employee_id'],
    'active': employeeQuery['employee_active'],
    'comission': employeeQuery['employee_comission'],
    'name': employeeQuery['employee_name'],
    'mail': employeeQuery['employee_mail'],
    'birth_date': str(employeeQuery['employee_birth_date']),
    'entry_date_time': str(employeeQuery['employee_entry_date_time'])
  }

class EmployeeApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('employee_id', location='args', type=int, help='id from employee, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    employee = getEmployeeFromDB(args['employee_id'])
    if employee == None:
      abort(404, 'Funcionário ' + str(args['employee_id']) + ' não econtrado!')
        
    return employee, 200
  
  def patch(self):
    
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('employee_id', location='json', type=int, help='id from emplyee, required', required=True)
    argsParser.add_argument('active', location='json', type=bool, help='Employee active in the system')
    argsParser.add_argument('comission', location='json', type=float, help='Employee comission per sale')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    employee = getEmployeeFromDB(args['employee_id'])
    if employee == None:
      abort(404, 'Funcionário não econtrado!')

    dbExecute(
    ' UPDATE tbl_employee SET '
    '   employee_active = %s, '
    '   employee_comission = %s '
    '   WHERE employee_id = %s; ',
    [
      args['active'] if args.get('active') != None else employee['active'],
      args['comission'] if args.get('comission') != None else employee['comission'],
      args['employee_id']
    ])
  
    return {}, 204
  
class EmployeesApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # get start and end datetime to get sales
    dateMonthStart = datetime.today().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    dateMonthEnd = dateMonthStart + relativedelta(months=1)
    
    employeesQuery = dbGetAll(
      ' SELECT e.employee_id, employee_active, employee_comission, '
      ' person_name AS employee_name, person_birth_date AS employee_birth_date, '
      ' user_mail AS employee_mail, user_entry_date_time AS employee_entry_date_time, '
      ' sale_emp.employee_total_sales, '
      ' month_sale_emp.employee_month_total_sales, month_sale_emp.employee_month_total_sales_value, '
      ' conditional_emp.employee_total_conditionals, '
      ' active_conditional_emp.employee_active_total_conditionals '
      '   FROM tbl_person p '
      '   JOIN tbl_user u ON p.person_id = u.user_id '
      '   JOIN tbl_employee e ON u.user_id = e.employee_id '
      '   LEFT JOIN ( '
		  '     SELECT se.employee_id, COUNT(s.sale_id) AS employee_total_sales '
			'       FROM tbl_sale s '
      '       JOIN tbl_employee se ON s.sale_employee_id = se.employee_id '
      '       GROUP BY se.employee_id '
      '   ) AS sale_emp ON e.employee_id = sale_emp.employee_id '
      '   LEFT JOIN ( '
		  '     SELECT mse.employee_id, COUNT(ms.sale_id) AS employee_month_total_sales, SUM(ms.sale_total_value) AS employee_month_total_sales_value '
			'       FROM tbl_sale ms '
      '       JOIN tbl_employee mse ON ms.sale_employee_id = mse.employee_id '
      '       WHERE ms.sale_creation_date_time >= %s AND ms.sale_creation_date_time <= %s '
      '       GROUP BY mse.employee_id '
      '   ) AS month_sale_emp ON e.employee_id = month_sale_emp.employee_id '
      '   LEFT JOIN ( '
		  '     SELECT ce.employee_id, COUNT(conditional_id) AS employee_total_conditionals '
			'       FROM tbl_conditional c '
      '       JOIN tbl_employee ce ON c.conditional_employee_id = ce.employee_id '
      '       GROUP BY ce.employee_id '
      '   ) AS conditional_emp ON e.employee_id = conditional_emp.employee_id '
      '   LEFT JOIN ( '
		  '     SELECT ace.employee_id, COUNT(ac.conditional_id) AS employee_active_total_conditionals '
			'       FROM tbl_conditional ac '
      '       JOIN tbl_employee ace ON ac.conditional_employee_id = ace.employee_id '
      '       WHERE ac.conditional_status = \'Pendente\' '
      '       GROUP BY ace.employee_id '
      '   ) AS active_conditional_emp ON e.employee_id = active_conditional_emp.employee_id '
      '   WHERE user_type = \'E\'; ', [dateMonthStart, dateMonthEnd])
  
    if employeesQuery == None:
      return []
    
    employees = []
    for employeeRow in employeesQuery:
      employees.append({
        'id': employeeRow['employee_id'],
        'active': employeeRow['employee_active'],
        'sales': employeeRow['employee_total_sales'] if employeeRow['employee_total_sales'] else 0,
        'conditionals': employeeRow['employee_total_conditionals'] if employeeRow['employee_total_conditionals'] else 0,
        'active_conditionals': employeeRow['employee_active_total_conditionals'] if employeeRow['employee_active_total_conditionals'] else 0,
        'comission': employeeRow['employee_comission'],
        'name': employeeRow['employee_name'],
        'mail': employeeRow['employee_mail'],
        'birth_date': str(employeeRow['employee_birth_date']),
        'entry_date_time': str(employeeRow['employee_entry_date_time']),
        'last_month_sales': employeeRow['employee_month_total_sales'] if employeeRow['employee_month_total_sales'] else 0,
        'last_month_value': employeeRow['employee_month_total_sales_value'] if employeeRow['employee_month_total_sales_value'] else 0
      })
        
    return { 'employees': employees }, 200