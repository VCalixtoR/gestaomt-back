from flask import Flask, abort
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS
from dotenv import load_dotenv, find_dotenv

from utils.sistemConfig import getMissingEnvironmentVar
from utils.dbUtils import dbStart
from utils.cryptoFunctions import loadGenerateKeys

from services.authentication import AuthWithLoginApi, AuthWithTokenApi
from services.user import UserApi, UserPendingApi, UsersApi, UsersPendingApi
from services.employee import EmployeeApi, EmployeesApi
from services.employeesale import EmployeeSalesApi, EmployeeSalesSummaryApi
from services.client import ClientApi, ClientsApi
from services.event import EventsApi
from services.product import ProductApi, ProductInfoApi, ProductsApi
from services.conditional import ConditionalApi, ConditionalsApi
from services.sale import SaleApi, SalesApi

# For homol and production ambients like render.com the environment variables are already loaded
if getMissingEnvironmentVar():
  print('# Loading and checking environment from .env')
  load_dotenv(find_dotenv())
  missingVar = getMissingEnvironmentVar()
  if missingVar:
    print('# Error - Missing ' + str(missingVar) + ' environment variable')
    exit()

# starts database
dbStart()
# load/generate security keys
loadGenerateKeys()

# loads flask API
app = Flask(__name__)
CORS(app, origins='*',
    headers=['Content-Type', 'Authorization'],
    expose_headers='Authorization')

api = Api(app)
api.add_resource(AuthWithLoginApi, '/auth-with-login')
api.add_resource(AuthWithTokenApi, '/auth-with-token')

api.add_resource(EventsApi, '/events')

api.add_resource(UserApi, '/user')
api.add_resource(UsersApi, '/users')
api.add_resource(UserPendingApi, '/user/pending')
api.add_resource(UsersPendingApi, '/users/pending')

api.add_resource(EmployeeApi, '/employee')
api.add_resource(EmployeesApi, '/employees')
api.add_resource(EmployeeSalesApi, '/employee/sales')
api.add_resource(EmployeeSalesSummaryApi, '/employee/sales/summary')

api.add_resource(ClientApi, '/client')
api.add_resource(ClientsApi, '/clients')

api.add_resource(ProductApi, '/product')
api.add_resource(ProductInfoApi, '/product/info')
api.add_resource(ProductsApi, '/products')

api.add_resource(ConditionalApi, '/conditional')
api.add_resource(ConditionalsApi, '/conditionals')

api.add_resource(SaleApi, '/sale')
api.add_resource(SalesApi, '/sales')