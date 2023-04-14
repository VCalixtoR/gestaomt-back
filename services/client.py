import traceback

from flask import Flask, abort, request
from flask_restful import Resource, Api, reqparse

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

def formatGroupedClientContacts(contactIds, contactTypes, contactValues):

  if not contactIds or not contactTypes or not contactValues:
    return None

  contacts = []
  contactIdsL = contactIds.split(',')
  contactTypesL = contactTypes.split(',')
  contactValuesL = contactValues.split(',')

  for i in range(len(contactIdsL)):
    contacts.append({ 'contact_id' : contactIdsL[i], 'contact_type' : contactTypesL[i], 'contact_value' : contactValuesL[i] })

  return contacts

def formatGroupedClientChildren(childrenIds, childrenNames, childrenBirthDates, childrenSizeIds, childrenSizeNames):
    
  if not childrenIds or not childrenNames or not childrenBirthDates or not childrenSizeNames:
    return None

  children = []
  childrenIdsL = childrenIds.split(',')
  childrenNamesL = childrenNames.split(',')
  childrenBirthDatesL = childrenBirthDates.split(',')
  childrenSizeIdsL = childrenSizeIds.split(',')
  childrenSizeNamesL = childrenSizeNames.split(',')

  for i in range(len(childrenIdsL)):
    children.append({ 'children_id' : childrenIdsL[i], 'children_name' : childrenNamesL[i], 'children_birth_date' : str(childrenBirthDatesL[i]), 'children_product_size_id' : childrenSizeIdsL[i], 'children_product_size_name' : childrenSizeNamesL[i] })

  return children

def getClientFromDB(clientId):

  clientQuery = dbGetSingle(
    ' SELECT client_id, person_name AS client_name, person_cpf AS client_cpf, person_birth_date AS client_birth_date, person_gender AS client_gender, '
    ' client_cep, client_adress, client_city, client_neighborhood, client_state, client_number, client_complement, '
    ' client_contact_ids, client_contact_types, client_contact_values, '
    ' client_children_ids, client_children_names, client_children_birth_dates, client_children_product_size_ids, client_children_product_size_names '
    '   FROM tbl_person AS p JOIN tbl_client AS c ON p.person_id = c.client_id '
    '   LEFT JOIN ( '
    '     SELECT contact_client_id, '
    '	    GROUP_CONCAT(contact_id SEPARATOR \',\') AS client_contact_ids, '
    '     GROUP_CONCAT(contact_type SEPARATOR \',\') AS client_contact_types,  '
    '	    GROUP_CONCAT(contact_value SEPARATOR \',\') AS client_contact_values '
    '	      FROM tbl_client_contact GROUP BY contact_client_id '
    '   ) AS ccontact ON c.client_id = ccontact.contact_client_id '
    '   LEFT JOIN ( '
    '     SELECT children_client_id, '
    '	    GROUP_CONCAT(children_id SEPARATOR \',\') AS client_children_ids, '
    '	    GROUP_CONCAT(children_name SEPARATOR \',\') AS client_children_names, '
    '     GROUP_CONCAT(children_birth_date SEPARATOR \',\') AS client_children_birth_dates, '
    '     GROUP_CONCAT(product_size_id SEPARATOR \',\') AS client_children_product_size_ids, '
    '     GROUP_CONCAT(product_size_name SEPARATOR \',\') AS client_children_product_size_names '
    '	      FROM tbl_client_children '
    '       JOIN tbl_product_size ON tbl_client_children.children_product_size_id = tbl_product_size.product_size_id '
    '       GROUP BY children_client_id '
    '   ) AS cchildren ON c.client_id = cchildren.children_client_id '
    '   WHERE client_id = %s; ', [(clientId)])

  if not clientQuery:
    return None
  
  if clientQuery['client_birth_date']:
    clientQuery['client_birth_date'] = str(clientQuery['client_birth_date'])
  
  clientQuery['contacts'] = formatGroupedClientContacts(
    clientQuery['client_contact_ids'], clientQuery['client_contact_types'], clientQuery['client_contact_values'])
  
  clientQuery['children'] = formatGroupedClientChildren(
    clientQuery['client_children_ids'], clientQuery['client_children_names'], clientQuery['client_children_birth_dates'], 
    clientQuery['client_children_product_size_ids'], clientQuery['client_children_product_size_names'])
  
  del clientQuery['client_contact_ids']
  del clientQuery['client_contact_types']
  del clientQuery['client_contact_values']

  del clientQuery['client_children_ids']
  del clientQuery['client_children_names']
  del clientQuery['client_children_birth_dates']
  del clientQuery['client_children_product_size_ids']
  del clientQuery['client_children_product_size_names']

  return clientQuery

class ClientApi(Resource):

  def put(self):
        
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('client_name', location='json', type=str, help='Client name, required', required=True)
    argsParser.add_argument('client_cpf', location='json', type=str, help='Client cpf')
    argsParser.add_argument('client_gender', location='json', type=str, help='Client gender, required', required=True)
    argsParser.add_argument('client_birth_date', location='json', type=str, help='Client birth date')
    argsParser.add_argument('client_cep', location='json', type=str, help='Client cep')
    argsParser.add_argument('client_adress', location='json', type=str, help='Client adress')
    argsParser.add_argument('client_city', location='json', type=str, help='Client city')
    argsParser.add_argument('client_neighborhood', location='json', type=str, help='Client neighborhood')
    argsParser.add_argument('client_state', location='json', type=str, help='Client state')
    argsParser.add_argument('client_number', location='json', type=str, help='Client number')
    argsParser.add_argument('client_complement', location='json', type=str, help='Client complement')
    argsParser.add_argument('client_contacts', location='json',  type=list, help='Client contacts json structure')
    argsParser.add_argument('client_children', location='json', type=list, help='Client children json structure')
    args = argsParser.parse_args()
    
    if(args['Authorization']):
      isValid, returnMessage = isAuthTokenValid(args)
      if not isValid:
        abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    sqlQuery = dbGetSingle(' SELECT * FROM tbl_person WHERE person_name = %s; ', [(args['client_name'])])
    if sqlQuery != None:
      return 'Nome já utilizado!', 409

    if args['client_cpf']:
      sqlQuery = dbGetSingle(' SELECT * FROM tbl_person WHERE person_cpf = %s; ', [(args['client_cpf'])])
      if sqlQuery != None:
        return 'Cpf já utilizado!', 409
    
    # verify contacts
    if args.get('client_contacts'):
      for contact in args['client_contacts']:
        if not contact.get('contact_type'):
          return 'Um dos contatos associados não possui o tipo', 422
        if not contact.get('contact_value'):
          return 'Um dos contatos associados está sem o valor', 422
    
    # verify children
    if args.get('client_children'):
      for children in args['client_children']:
        if not children.get('children_name'):
          return 'Uma das crianças associadas não possui o nome', 422
        if not children.get('children_birth_date'):
          return 'Uma das crianças associadas não possui o aniversário', 422
        if not children.get('children_product_size_id'):
          return 'Uma das crianças associadas não possui o tamanho de produtos', 422

    try:
      # inserts person
      dbExecute(
        ' INSERT INTO tbl_person (person_name, person_cpf, person_birth_date, person_gender) VALUES ' \
        ' (%s, %s, %s, %s); ',
        [args['client_name'], args['client_cpf'], args['client_birth_date'], args['client_gender']], False)
        
      personIdQuery = dbGetSingle(' SELECT person_id AS client_id FROM tbl_person WHERE person_name = %s; ', [(args['client_name'])], False)

      if not personIdQuery:
        raise Exception('Empty select personIdQuery after insert from tbl_person put')

      # inserts client
      dbExecute(
        ' INSERT INTO tbl_client (client_id, client_cep, client_adress, client_city, ' 
        ' client_neighborhood, client_state, client_number, client_complement) VALUES '
        ' (%s, %s, %s, %s, %s, %s, %s, %s); ',
        [personIdQuery['client_id'], args['client_cep'], args['client_adress'], args['client_city'], 
        args['client_neighborhood'], args['client_state'], args['client_number'], args['client_complement']], False)
      
      # inserts client contacts
      if args.get('client_contacts'):
        for contact in args['client_contacts']:
          dbExecute( 
            'INSERT INTO tbl_client_contact (contact_client_id, contact_type, contact_value) VALUES '
            ' (%s, %s, %s); ',
            [personIdQuery['client_id'], contact['contact_type'], contact['contact_value']], False)
      
      # inserts client children
      if args.get('client_children'):
        for children in args['client_children']:
          dbExecute(
            ' INSERT INTO tbl_client_children (children_client_id, children_name, children_birth_date, children_product_size_id) VALUES '
            ' (%s, %s, %s, %s); ',
            [personIdQuery['client_id'], children['children_name'], children['children_birth_date'], children['children_product_size_id']], False)

    except Exception as e:
      dbRollback()
      traceback.print_exc()
      return 'Erro ao criar cliente ' + str(e), 500
    dbCommit()
    
    return {}, 201
  
  def get(self):
        
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('client_id', location='args', type=int, help='client id, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    client = getClientFromDB(args['client_id'])
    if not client:
      abort(404, 'Cliente não econtrado!')

    return client, 200
  
  def patch(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('client_id', location='json', type=str, help='Client id, required', required=True)
    argsParser.add_argument('client_name', location='json', type=str, help='Client name')
    argsParser.add_argument('client_cpf', location='json', type=str, help='Client cpf')
    argsParser.add_argument('client_gender', location='json', type=str, help='Client gender')
    argsParser.add_argument('client_birth_date', location='json', type=str, help='Client birth date')
    argsParser.add_argument('client_cep', location='json', type=str, help='Client cep')
    argsParser.add_argument('client_adress', location='json', type=str, help='Client adress')
    argsParser.add_argument('client_city', location='json', type=str, help='Client city')
    argsParser.add_argument('client_neighborhood', location='json', type=str, help='Client neighborhood')
    argsParser.add_argument('client_state', location='json', type=str, help='Client state')
    argsParser.add_argument('client_number', location='json', type=str, help='Client number')
    argsParser.add_argument('client_complement', location='json', type=str, help='Client complement')
    argsParser.add_argument('client_contacts', location='json', type=list, help='Client contacts json structure')
    argsParser.add_argument('client_children', location='json', type=list, help='Client children json structure')
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    client = getClientFromDB(args['client_id'])
    if not client:
      abort(404, 'Cliente não econtrado!')

    try:
      # person
      dbExecute(
        ' UPDATE tbl_person SET '
        '   person_name = %s, '
        '   person_birth_date = %s, '
        '   person_cpf = %s, '
        '   person_gender = %s '
        '   WHERE person_id = %s; ', 
        [
          client['client_name'] if not args.get('client_name') else args['client_name'],
          client['client_birth_date'] if not args.get('client_birth_date') else args['client_birth_date'],
          client['client_cpf'] if not args.get('client_cpf') else args['client_cpf'],
          client['client_gender'] if not args.get('client_gender') else args['client_gender'],
          client['client_id']
        ], False)

      # client    
      dbExecute(
        ' UPDATE tbl_client SET '
        '   client_cep = %s, '
        '   client_adress = %s, '
        '   client_city = %s, '
        '   client_neighborhood = %s, '
        '   client_state = %s, '
        '   client_number = %s, '
        '   client_complement = %s '
        '   WHERE client_id = %s; ',
        [
          client['client_cep'] if not args.get('client_cep') else args['client_cep'],
          client['client_adress'] if not args.get('client_adress') else args['client_adress'],
          client['client_city'] if not args.get('client_city') else args['client_city'],
          client['client_neighborhood'] if not args.get('client_neighborhood') else args['client_neighborhood'],
          client['client_state'] if not args.get('client_state') else args['client_state'],
          client['client_number'] if not args.get('client_number') else args['client_number'],
          client['client_complement'] if not args.get('client_complement') else args['client_complement'],
          client['client_id']
        ], False)

      # client contacts
      if args.get('client_contacts'):
        dbExecute(' DELETE FROM tbl_client_contact WHERE contact_client_id = %s; ', [(client['client_id'])], False)
        for contact in args['client_contacts']:
          dbExecute(
            ' INSERT INTO tbl_client_contact (contact_client_id, contact_type, contact_value) VALUES '
            ' (%s, %s, %s); ',
            [client['client_id'], contact['contact_type'], contact['contact_value']], False)

      # client children
      if args.get('client_children'):
        dbExecute(' DELETE FROM tbl_client_children WHERE children_client_id = %s; ', [(client['client_id'])], False)
        for children in args['client_children']:
          dbExecute(
            ' INSERT INTO tbl_client_children (children_client_id, children_name, children_birth_date, children_product_size_id) VALUES '
            ' (%s, %s, %s, %s); ',
            [client['client_id'], children['children_name'], children['children_birth_date'], children['children_product_size_id']], False)
      
    except Exception as e:
      dbRollback()
      traceback.print_exc()
      return 'Erro ao atualizar o cliente ' + str(e)
    dbCommit()

    return [], 204

class ClientsApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='number of rows returned, required', required=True)
    argsParser.add_argument('offset', location='args', type=int, help='start row from db, required', required=True)
    argsParser.add_argument('client_name', location='args', type=str, help='client name')
    argsParser.add_argument('children_name', location='args', type=str, help='client children name')
    argsParser.add_argument('children_birth_date_start', location='args', type=str, help='start client children birth date')
    argsParser.add_argument('children_birth_date_end', location='args', type=str, help='end client children birth date')
    argsParser.add_argument('last_sale_date_start', location='args', type=str, help='start for last sale date')
    argsParser.add_argument('last_sale_date_end', location='args', type=str, help='end for last sale date')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    childrenFilterScrypt, childrenFilterArgs = dbGetSqlFilterScrypt(
      [
        {'filterCollum':'children_name', 'filterOperator':'LIKE%_%', 'filterValue':args.get('children_name')},
        {'filterCollum':'children_birth_date', 'filterOperator':'>=', 'filterValue':args.get('children_birth_date_start')},
        {'filterCollum':'children_birth_date', 'filterOperator':'<=', 'filterValue':args.get('children_birth_date_end')}
      ], groupByCollumns='children_client_id', filterEnding='')

    geralFilterScrypt, geralFilterScryptNoLimit, geralFilterArgs, geralFilterArgsNoLimit =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'p.person_name', 'filterOperator':'LIKE%_%', 'filterValue':args.get('client_name')},
        {'filterCollum':'last_sale_date', 'filterOperator':'>=', 'filterValue':args.get('last_sale_date_start')},
        {'filterCollum':'last_sale_date', 'filterOperator':'<=', 'filterValue':args.get('last_sale_date_end')}
      ],
      orderByCollumns='p.person_name', limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)

    leftJoinOnChildren = not args.get('children_name') and not args.get('children_birth_date_start') and not args.get('children_birth_date_end')

    geralSqlScrypt = (
      ' SELECT c.client_id, p.person_name AS client_name, p.person_cpf AS client_cpf, p.person_birth_date AS client_birth_date, p.person_gender AS client_gender, '
      ' c.client_cep, c.client_adress, c.client_city, c.client_neighborhood, c.client_state, c.client_number, c.client_complement, '
      ' client_contact_ids, client_contact_types, client_contact_values, '
      ' client_children_ids, client_children_names, client_children_birth_dates, client_children_product_size_ids, client_children_product_size_names, '
      ' csale.last_sale_date, stmp.sale_total_value AS last_sale_total_value '
      '   FROM tbl_person p '
      '   JOIN tbl_client c ON p.person_id = c.client_id '
      '   LEFT JOIN ( '
      '     SELECT contact_client_id, '
      '	      GROUP_CONCAT(contact_id SEPARATOR \',\') AS client_contact_ids, '
      '       GROUP_CONCAT(contact_type SEPARATOR \',\') AS client_contact_types,  '
      '	      GROUP_CONCAT(contact_value SEPARATOR \',\') AS client_contact_values '
      '	        FROM tbl_client_contact GROUP BY contact_client_id '
      '   ) AS ccontact ON c.client_id = ccontact.contact_client_id '
      '   ' + ('LEFT' if leftJoinOnChildren else '') + ' JOIN ( '
      '     SELECT children_client_id, '
      '	      GROUP_CONCAT(children_id SEPARATOR \',\') AS client_children_ids, '
      '	      GROUP_CONCAT(children_name SEPARATOR \',\') AS client_children_names, '
      '       GROUP_CONCAT(children_birth_date SEPARATOR \',\') AS client_children_birth_dates, '
      '       GROUP_CONCAT(product_size_id SEPARATOR \',\') AS client_children_product_size_ids, '
      '       GROUP_CONCAT(product_size_name SEPARATOR \',\') AS client_children_product_size_names '
      '	        FROM tbl_client_children '
      '         JOIN tbl_product_size ON tbl_client_children.children_product_size_id = tbl_product_size.product_size_id '
      + childrenFilterScrypt +
      '   ) AS cchildren ON c.client_id = cchildren.children_client_id '
      '   LEFT JOIN ( '
      '     SELECT s.sale_client_id, MAX(s.sale_creation_date_time) AS last_sale_date '
      '       FROM tbl_sale s '
      '       GROUP BY s.sale_client_id '
      '   ) AS csale ON c.client_id = csale.sale_client_id '
      '   LEFT JOIN tbl_sale stmp ON csale.sale_client_id = stmp.sale_client_id '
      + geralFilterScrypt)
    
    countSqlScrypt = (
      ' SELECT COUNT(*) as countcli '
      '   FROM tbl_person p '
      '   JOIN tbl_client c ON p.person_id = c.client_id '
      '   LEFT JOIN ( '
      '     SELECT contact_client_id, '
      '	      GROUP_CONCAT(contact_id SEPARATOR \',\') AS client_contact_ids, '
      '       GROUP_CONCAT(contact_type SEPARATOR \',\') AS client_contact_types,  '
      '	      GROUP_CONCAT(contact_value SEPARATOR \',\') AS client_contact_values '
      '	        FROM tbl_client_contact GROUP BY contact_client_id '
      '   ) AS ccontact ON c.client_id = ccontact.contact_client_id '
      '   ' + ('LEFT' if leftJoinOnChildren else '') + ' JOIN ( '
      '     SELECT children_client_id, '
      '	      GROUP_CONCAT(children_id SEPARATOR \',\') AS client_children_ids, '
      '	      GROUP_CONCAT(children_name SEPARATOR \',\') AS client_children_names, '
      '       GROUP_CONCAT(children_birth_date SEPARATOR \',\') AS client_children_birth_dates, '
      '       GROUP_CONCAT(product_size_id SEPARATOR \',\') AS client_children_product_size_ids, '
      '       GROUP_CONCAT(product_size_name SEPARATOR \',\') AS client_children_product_size_names '
      '	        FROM tbl_client_children '
      '         JOIN tbl_product_size ON tbl_client_children.children_product_size_id = tbl_product_size.product_size_id '
      + childrenFilterScrypt +
      '   ) AS cchildren ON c.client_id = cchildren.children_client_id '
      '   LEFT JOIN ( '
      '     SELECT s.sale_client_id, MAX(s.sale_creation_date_time) AS last_sale_date '
      '       FROM tbl_sale s '
      '       GROUP BY s.sale_client_id '
      '   ) AS csale ON c.client_id = csale.sale_client_id '
      '   LEFT JOIN tbl_sale stmp ON csale.sale_client_id = stmp.sale_client_id '
      + geralFilterScryptNoLimit)

    clientSqlQuery = dbGetAll(geralSqlScrypt, childrenFilterArgs + geralFilterArgs)
    countSqlQuery = dbGetSingle(countSqlScrypt, childrenFilterArgs + geralFilterArgsNoLimit)

    if not clientSqlQuery or not countSqlQuery:
      return { 'count_clients': 0, 'clients': [] }, 200
    
    for clientRow in clientSqlQuery:
      
      if clientRow['client_birth_date']:
        clientRow['client_birth_date'] = str(clientRow['client_birth_date'])

      if not clientRow['last_sale_total_value']:
        clientRow['last_sale_total_value'] = 0
      
      if clientRow.get('last_sale_date'):
        clientRow['last_sale_date'] = str(clientRow['last_sale_date'])

      clientRow['contacts'] = formatGroupedClientContacts(
        clientRow['client_contact_ids'], clientRow['client_contact_types'], clientRow['client_contact_values'])
    
      clientRow['children'] = formatGroupedClientChildren(
        clientRow['client_children_ids'], clientRow['client_children_names'], clientRow['client_children_birth_dates'],
        clientRow['client_children_product_size_ids'], clientRow['client_children_product_size_names'])

      del clientRow['client_contact_ids']
      del clientRow['client_contact_types']
      del clientRow['client_contact_values']

      del clientRow['client_children_ids']
      del clientRow['client_children_names']
      del clientRow['client_children_birth_dates']
      del clientRow['client_children_product_size_ids']
      del clientRow['client_children_product_size_names']
    
    return { 'count_clients': countSqlQuery['countcli'], 'clients': clientSqlQuery }, 200