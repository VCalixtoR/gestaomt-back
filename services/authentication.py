from flask import Flask, abort, request
from flask_restful import Resource, Api, reqparse
from datetime import datetime
from base64 import b64decode
import jwt

from utils.cryptoFunctions import getPrivateK,  getPublicK
from utils.dbUtils import *

def createAuthToken(tokenUserId):

  tokenDateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  tokenJwt = jwtEncode(tokenUserId, tokenDateTime)
    
  ret = {
    'token_date_time': tokenDateTime,
    'token_jwt': tokenJwt,
    'token_user_id': tokenUserId
  }
    
  return ret

def jwtEncode(tokenUserId, tokenDateTime):

  tokenJwt = jwt.encode({'token_user_id': tokenUserId, 'token_date_time': tokenDateTime}, getPrivateK(), algorithm="RS256")
  return tokenJwt

def jwtDecode(tokenJwt):

  tokenData = jwt.decode(tokenJwt, getPublicK(), algorithms=["RS256"])
  return tokenData
    
def isAuthTokenValid(args):

  tokenJwt = args['Authorization'].replace('Bearer ', '')
  tokenData = jwtDecode(tokenJwt)
    
  if not tokenData:
    return (False, 'Token inválido!')
    
  authTokenQuery = dbGetSingle('SELECT token_user_id, token_date_time FROM tbl_auth_token WHERE token_user_id = %s; ', [(tokenData['token_user_id'])])
  if not authTokenQuery:
    return (False, 'Não foi encontrado o token no banco de dados!')
        
  tokenDateTimeF = authTokenQuery['token_date_time'].strftime("%Y-%m-%d %H:%M:%S")
  if tokenDateTimeF != tokenData['token_date_time']:
    return (False, 'Token expirado!')
    
  return (True, '')
    
def updateUserToken(tokenUserId, tokenDateTime):
    
  dbExecute('DELETE FROM tbl_auth_token WHERE token_user_id = %s; ',[(tokenUserId)])
  dbExecute('INSERT INTO tbl_auth_token (token_user_id, token_date_time) VALUES (%s, %s); ', ( tokenUserId, tokenDateTime ))
  
class AuthWithLoginApi(Resource):
    
  def post(self):
    
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Email and hash password of the user, used to authentication, required', required=True)
    args = argsParser.parse_args()

    userMail, userHashPassword = b64decode(args['Authorization'].replace('Basic ', '')).decode('utf-8').split(':', 1)
      
    userQuery = dbGetSingle('SELECT user_id, user_hash_password FROM tbl_user WHERE user_mail = %s; ', [(userMail)])
      
    if userQuery == None or len(userQuery) != 2:
      abort(401, 'Usuário não encontrado!')
    
    if userQuery['user_hash_password'] != userHashPassword:
      abort(401, 'Senha incorreta!')

    newToken = createAuthToken(userQuery['user_id'])
    updateUserToken(newToken['token_user_id'], newToken['token_date_time'])
      
    return { 'token_jwt': newToken['token_jwt'] }, 200
    
class AuthWithTokenApi(Resource):
    
  def post(self):
        
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
        
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
            
    tokenJwt = args['Authorization'].replace('Bearer ', '')
        
    oldTokenData = jwtDecode(tokenJwt)
    newToken = createAuthToken(oldTokenData['token_user_id'])
    updateUserToken(newToken['token_user_id'], newToken['token_date_time'])
        
    return { 'token_jwt': newToken['token_jwt'] }, 200
    
  def delete(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
        
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
            
    tokenJwt = args['Authorization'].replace('Bearer ', '')
        
    oldTokenData = jwtDecode(tokenJwt)
    dbExecute('DELETE FROM tbl_auth_token WHERE token_user_id = %s', [(oldTokenData['token_user_id'])])
        
    return {}, 204 