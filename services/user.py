from flask import Flask, abort
from flask_restful import Resource, Api, reqparse
import traceback

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

def getAllUsersFromDB(pendingUsers=False):

  usersQuery = None
  
  if not pendingUsers:
    usersQuery = dbGetAll(
      ' SELECT user_id, person_name AS user_name, user_type, person_birth_date AS user_birth_date, '
      ' person_cpf AS user_cpf, person_gender AS user_gender, user_mail, user_phone_num, user_entry_date_time, user_entry_allowed '
      '   FROM tbl_person p JOIN tbl_user u ON p.person_id = u.user_id; ')
  else:
    usersQuery = dbGetAll(
      ' SELECT user_id, person_name AS user_name, user_type, person_birth_date AS user_birth_date, '
      ' person_cpf AS user_cpf, person_gender AS user_gender, user_mail, user_phone_num, user_entry_date_time, user_entry_allowed '
      '   FROM tbl_person p JOIN tbl_user u ON p.person_id = u.user_id '
      '   WHERE user_entry_allowed = 0 AND user_type = \'E\'; ')
  
  if usersQuery == None:
    return []
  
  users = []
  for userRow in usersQuery:
    users.append({
      'id': userRow['user_id'],
      'name': userRow['user_name'],
      'type': userRow['user_type'],
      'birth_date': str(userRow['user_birth_date']),
      'cpf': userRow['user_cpf'],
      'gender': userRow['user_gender'],
      'mail': userRow['user_mail'],
      'phone_num': userRow['user_phone_num'],
      'entry_date_time': str(userRow['user_entry_date_time']),
      'entry_allowed': userRow['user_entry_allowed']
    })

  return users

def getUserFromDB(userId):
      
  userQuery = dbGetSingle(
    ' SELECT user_id, person_name AS user_name, user_type, person_birth_date AS user_birth_date, '
    ' person_cpf AS user_cpf, person_gender AS user_gender, user_mail, user_phone_num, user_entry_date_time, user_entry_allowed '
	  '   FROM tbl_person p JOIN tbl_user u ON p.person_id = u.user_id '
    '   WHERE user_id = %s; ',
    [(userId)])

  if userQuery == None or len(userQuery) != 10:
    return None
        
  user = {
    'id': userQuery['user_id'],
    'name': userQuery['user_name'],
    'type': userQuery['user_type'],
    'birth_date': str(userQuery['user_birth_date']),
    'cpf': userQuery['user_cpf'],
    'gender': userQuery['user_gender'],
    'mail': userQuery['user_mail'],
    'phone_num': userQuery['user_phone_num'],
    'entry_date_time': str(userQuery['user_entry_date_time']),
    'entry_allowed': userQuery['user_entry_allowed']
  }

  return user

def createUserInDB(user):
    
  if user == None:
    return 'Objeto usuário não formatado!'
    
  userQuery = dbGetSingle("SELECT * FROM tbl_user WHERE user_mail = %s;",[(user['mail'])])
  if userQuery != None:
    return 'Email já utilizado!'
    
  userQuery = dbGetSingle("SELECT * FROM tbl_person WHERE person_cpf = %s;",[(user['cpf'])])
  if userQuery != None:
    return 'Cpf já utilizado!'

  try:
    dbExecute(
      ' INSERT INTO tbl_person (person_name, person_cpf, person_birth_date, person_gender) VALUES (%s, %s, %s, %s) ',
      [user['name'], user['cpf'], user['birth_date'], user['gender']], False)
    
    dbExecute(
      ' INSERT INTO tbl_user (user_id, user_type, user_mail, user_phone_num, user_hash_password) VALUES '
      ' (LAST_INSERT_ID(), %s, %s, %s, %s); ',
      [user['type'], user['mail'], user['phone_num'], user['hash_password']], False)
  except Exception as e:
    dbRollback()
    traceback.print_exc()
    return 'Erro ao criar o usuario ' + str(e)
  dbCommit()

  return 'Usuário criado!'

def updateUserInDB(user):

  if user == None:
    return 'Objeto usuário não formatado!'
  
  dbExecute(
    ' UPDATE tbl_person SET '
    '   person_name = %s, '
    '   person_birth_date = %s, '
    '   person_cpf = %s, '
    '   person_gender = %s '
    '   WHERE person_id = %s; ',
    [user['name'], user['birth_date'], user['cpf'], user['gender'], user['id']], False)

  dbExecute(
    ' UPDATE tbl_user SET '
    '   user_type = %s, '
    '   user_mail = %s, '
    '   user_phone_num = %s, '
    '   user_entry_allowed = %s '
    '   WHERE user_id = %s; ',
    [user['type'], user['mail'], user['phone_num'], user['entry_allowed'], user['id']], False)
  
  return 'Usuário atualizado!'

def deleteUserFromDb(userId):

  try:
    sqlScrypt = "DELETE FROM tbl_user WHERE user_id = %s;"
    dbExecute(sqlScrypt, [(userId)])
    
    sqlScrypt = "DELETE FROM tbl_person WHERE person_id = %s;"
    dbExecute(sqlScrypt, [(userId)])
  except Exception as e:
    dbRollback()
    traceback.print_exc()
    return 'Erro ao atualizar o usuario ' + str(e)
  dbCommit()

  return 'Usuário apagado!'

class UserApi(Resource):

  def get(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('user_id', location='args', type=int, help='id from user, required', required=True)
    args = argsParser.parse_args()
        
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    user = getUserFromDB(args['user_id'])
    if user == None:
      abort(404, 'Usuário ' + str(args['user_id']) + ' não econtrado!')
            
    return user, 200
    
  def put(self):
        
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication!')
    argsParser.add_argument('user_name', type=str, help='Name of the user, required', required=True)
    argsParser.add_argument('user_type', type=str, help='E for employee, A for administrator, required', required=True)
    argsParser.add_argument('user_birth_date', type=str, help='Birth date format: yyyy-mm-dd, required', required=True)
    argsParser.add_argument('user_cpf', type=str, help='Cpf digits 00000000000 without symbols, required', required=True)
    argsParser.add_argument('user_gender', type=str, help='F for female, M for male, required', required=True)
    argsParser.add_argument('user_mail', type=str, help='Email of the user, used to authentication, required', required=True)
    argsParser.add_argument('user_phone_num', type=str, help='User phone number', required=False)
    argsParser.add_argument('user_hash_password', type=str, help='Hash password, defined by the web application, required', required=True)
    args = argsParser.parse_args()
        
    if(args['Authorization']):
      isValid, returnMessage = isAuthTokenValid(args)
      if not isValid:
        abort(401, 'Autenticação com o token falhou: ' + returnMessage)
      
    user = {
      'name': args['user_name'],
      'type': args['user_type'],
      'birth_date': args['user_birth_date'],
      'cpf': args['user_cpf'],
      'gender': args['user_gender'],
      'mail': args['user_mail'],
      'phone_num': args['user_phone_num'],
      'hash_password': args['user_hash_password']
    }

    createMsg = createUserInDB(user)
    if createMsg != 'Usuário criado!':
      abort(409, createMsg)
        
    return {}, 201
  
class UsersApi(Resource):

  def get(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    users = getAllUsersFromDB()

    return { 'users': users }, 200

class UserPendingApi(Resource):

  # patch to autorize user acess
  def patch(self):
       
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('user_id', location='json', type=int, help='id from user, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    user = getUserFromDB(args['user_id'])
    if user == None:
      abort(404, 'Usuário ' + str(args['user_id']) + ' não econtrado!')

    if user['entry_allowed'] == True:
      abort(409, 'Funcionário já autorizado!')

    userQuery = dbGetSingle(" SELECT * FROM tbl_employee WHERE employee_id = %s; ",[(user['id'])])
    if userQuery != None:
      abort(409, 'Usuário já possui cadastro como funcionário!')

    user['entry_allowed'] = True

    try:
      updateUserMsg = updateUserInDB(user)
      if updateUserMsg != 'Usuário atualizado!':
        raise Exception(updateUserMsg)

      dbExecute(
        ' INSERT INTO tbl_employee (employee_id, employee_comission) VALUES '
        ' (%s, %s); ', 
        [user['id'], 0.03])
    except Exception as e:
      dbRollback()
      traceback.print_exc()
      return 'Erro ao permitir o funcionario ' + str(e), 409
    dbCommit()

    return {}, 204

  # delete to deny user acess
  def delete(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('user_id', location='json', type=int, help='id from user, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    user = getUserFromDB(args['user_id'])
    
    if user == None:
      abort(404, 'Usuário ' + str(args['user_id']) + ' não econtrado!')

    if user['entry_allowed'] == True:
      abort(409, 'Funcionário já autorizado! Para desativa-lo utilize o update de funcionários')
    
    deleteMsg = deleteUserFromDb(args['user_id'])
    if deleteMsg != 'Usuário apagado!':
      abort(409, deleteMsg)

    return {}, 204
  
class UsersPendingApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    pendingUsers = getAllUsersFromDB(pendingUsers=True)

    return { 'users': pendingUsers }, 200