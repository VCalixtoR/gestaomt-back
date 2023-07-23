from flask import Flask, abort
from flask_restful import Resource, Api, reqparse
import traceback

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

class ProductApi(Resource):

  def put(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('product_code', location='json', type=str, help='product code, required', required=True)
    argsParser.add_argument('product_name', location='json', type=str, help='product name, required', required=True)
    argsParser.add_argument('product_collection_ids', location='json', type=list, help='product list of assigned collections ids')
    argsParser.add_argument('product_type_ids', location='json', type=list, help='product list of assigned types')
    argsParser.add_argument('customized_products', location='json', type=list, help='product variations list, required', required=True)
    argsParser.add_argument('product_observations', location='json', type=str, help='product observations')
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # test product
    productQuery = dbGetSingle("SELECT * FROM tbl_product WHERE product_code = %s AND is_product_active = TRUE; ",[(args['product_code'])])
    if productQuery != None:
      return 'Existe um produto ativo com o mesmo código, escolha um novo código ou desative o outro produto', 409
    
    productQuery = dbGetSingle("SELECT * FROM tbl_product WHERE product_name = %s AND is_product_active = TRUE; ",[(args['product_name'])])
    if productQuery != None:
      return 'Existe um produto ativo com o mesmo nome, escolha um novo nome ou desative o outro produto', 409

    if args.get('customized_products') is None or len(args['customized_products']) == 0:
      return 'Produtos customizaveis inválidos', 422

    # customized products
    for pos in range(len(args['customized_products'])):
      customizedProduct = args['customized_products'][pos]

      # checks for duplicants
      for sndpos in range(pos+1, len(args['customized_products'])):
        sndCustomizedProduct = args['customized_products'][sndpos]

        if (customizedProduct.get('product_color_id') == sndCustomizedProduct.get('product_color_id') and
          customizedProduct.get('product_other_id') == sndCustomizedProduct.get('product_other_id') and
          customizedProduct.get('product_size_id') == sndCustomizedProduct.get('product_size_id')):
          
          return 'Existe duplicatas nos produtos', 422

      # price
      if customizedProduct.get('product_price') is None or customizedProduct['product_price'] <= 0:
        return 'Preço do produto inválido para uma das variações', 422
      
      # quantity
      if customizedProduct.get('product_quantity') is None or customizedProduct['product_quantity'] < 0:
        return 'Quantidade do produto inválida para uma das variações', 422
      
      # size
      if customizedProduct.get('product_size_id') is None:
        return 'Tamanho do produto inválido para uma das variações', 422
    
    dbObjectIns = startGetDbObject()
    try:
      # inserts product
      dbExecute(
        ' INSERT INTO tbl_product (product_code, product_name, product_observations) VALUES (%s, %s, %s) ',
        [args['product_code'], args['product_name'], args['product_observations']], True, dbObjectIns)
      
      productQuery = dbGetSingle(
        " SELECT product_id FROM tbl_product WHERE product_code = %s AND is_product_active = TRUE; ",
        [(args['product_code'])], True, dbObjectIns)
      
      if not productQuery:
        raise Exception('Exception empty select after insert from tbl_product put')
      
      productId = productQuery['product_id']
      
      # inserts has collections
      if args.get('product_collection_ids') is not None:
        for collectionId in args['product_collection_ids']:
          dbExecute(
            ' INSERT INTO tbl_product_has_collection (product_id, product_collection_id) VALUES (%s, %s) ',
            [productId, collectionId], True, dbObjectIns)
      
      # inserts has types
      if args.get('product_type_ids') is not None:
        for typeId in args['product_type_ids']:
          dbExecute(
            ' INSERT INTO tbl_product_has_type (product_id, product_type_id) VALUES (%s, %s) ',
            [productId, typeId], True, dbObjectIns)
      
      # inserts customized products to finish
      for customizedProduct in args['customized_products']:
        dbExecute(
          ' INSERT INTO tbl_customized_product (product_id, product_color_id, product_other_id, product_size_id, '
          ' customized_product_price, customized_product_quantity) '
          '   VALUES (%s, %s, %s, %s, %s, %s) ',
          [
            productId,
            customizedProduct['product_color_id'] if customizedProduct.get('product_color_id') else None,
            customizedProduct['product_other_id'] if customizedProduct.get('product_other_id') else None,
            customizedProduct['product_size_id'],
            customizedProduct['product_price'],
            customizedProduct['product_quantity']
          ], True, dbObjectIns)
      
    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao criar o usuario ' + str(e), 500
    dbCommit(dbObjectIns)
    
    return {}, 201
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('product_code', location='args', type=str, help='product code, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # product
    productQuery = dbGetSingle(
      ' SELECT product_id, product_code, product_name, product_observations, is_product_immutable, is_product_active, product_creation_date_time '
	    '   FROM tbl_product p '
      '   WHERE p.product_code = %s AND p.is_product_active = TRUE; ',
      [(args['product_code'])])
    
    if not productQuery:
      return 'Produto não encontrado', 404

    productQuery['product_creation_date_time'] = str(productQuery['product_creation_date_time'])

    # collections
    rawCollections = dbGetAll(
      ' SELECT product_collection_name '
      '   FROM tbl_product p '
      '   JOIN tbl_product_has_collection phc ON p.product_id = phc.product_id '
      '   JOIN tbl_product_collection pc ON phc.product_collection_id = pc.product_collection_id '
      '   WHERE p.product_id = %s; ',
      [(productQuery['product_id'])])
    productQuery['collections'] = [collection['product_collection_name'] for collection in rawCollections]

    # types
    rawTypes = dbGetAll(
      ' SELECT product_type_name  '
	    '   FROM tbl_product p '
      '   JOIN tbl_product_has_type pht ON p.product_id = pht.product_id '
      '   JOIN tbl_product_type pt ON pht.product_type_id = pt.product_type_id '
      '   WHERE p.product_id = %s; ',
      [(productQuery['product_id'])])
    productQuery['types'] = [typet['product_type_name'] for typet in rawTypes]

    # customized products
    customizedProductsQuery = dbGetAll(
      ' SELECT cp.customized_product_id, product_color_name, product_other_name, product_size_name, customized_product_price AS product_price, customized_product_quantity AS product_quantity '
	    '   FROM tbl_product p '
      '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
      '   JOIN tbl_product_size pz ON cp.product_size_id = pz.product_size_id '
      '   LEFT JOIN tbl_product_color pc ON cp.product_color_id = pc.product_color_id '
      '   LEFT JOIN tbl_product_other po ON cp.product_other_id = po.product_other_id '
      '   WHERE cp.is_customized_product_active = TRUE AND p.product_id = %s '
      '   ORDER BY product_size_name, product_color_name, product_other_name; ',
      [(productQuery['product_id'])])
    
    if not customizedProductsQuery:
      return 'Produto não encontrado', 404

    productQuery['customized_products'] = customizedProductsQuery
    
    return productQuery, 200

  # patch to update products and customized products - maybe the most complex request code
  def patch(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('product_id', location='json', type=int, help='product id, required', required=True)
    argsParser.add_argument('product_code', location='json', type=str, help='product code, required', required=True)
    argsParser.add_argument('product_name', location='json', type=str, help='product name, required', required=True)
    argsParser.add_argument('product_collection_ids', location='json', type=list, help='product list of assigned collections ids')
    argsParser.add_argument('product_type_ids', location='json', type=list, help='product list of assigned types')
    argsParser.add_argument('customized_products', location='json', type=list, help='product variations list, required', required=True)
    argsParser.add_argument('product_observations', location='json', type=str, help='product observations')
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # get and test product
    productQuery = dbGetSingle(
      ' SELECT * FROM tbl_product WHERE product_id = %s AND is_product_active = TRUE; ',
      [(args['product_id'])])
    
    if productQuery == None:
      return 'Id do produto a ser atualizado inválido', 422
    
    if dbGetSingle(
      ' SELECT * FROM tbl_product WHERE product_id != %s AND product_code = %s AND is_product_active = TRUE; ',
      [args['product_id'], args['product_code']]) != None:
      return 'Existe um outro produto ativo com o mesmo código, escolha um novo código ou desative o outro produto', 409
    
    if dbGetSingle(
      ' SELECT * FROM tbl_product WHERE product_id != %s AND product_name = %s AND is_product_active = TRUE; ',
      [args['product_id'], args['product_name']]) != None:
      return 'Existe um outro produto ativo com o mesmo nome, escolha um novo nome ou desative o outro produto', 409
    
    # get collections
    rawCollections = dbGetAll(
      ' SELECT pc.product_collection_id '
      '   FROM tbl_product p '
      '   JOIN tbl_product_has_collection phc ON p.product_id = phc.product_id '
      '   JOIN tbl_product_collection pc ON phc.product_collection_id = pc.product_collection_id '
      '   WHERE p.product_id = %s '
      '   ORDER BY product_collection_id; ',
      [(productQuery['product_id'])])
    productQuery['product_collection_ids'] = [collection['product_collection_id'] for collection in rawCollections]

    # get types
    rawTypes = dbGetAll(
      ' SELECT pt.product_type_id  '
	    '   FROM tbl_product p '
      '   JOIN tbl_product_has_type pht ON p.product_id = pht.product_id '
      '   JOIN tbl_product_type pt ON pht.product_type_id = pt.product_type_id '
      '   WHERE p.product_id = %s '
      '   ORDER BY product_type_id; ',
      [(productQuery['product_id'])])
    productQuery['product_type_ids'] = [typet['product_type_id'] for typet in rawTypes]

    # get and test customized products
    customizedProductQuery = dbGetAll(
      ' SELECT cp.customized_product_id, cp.product_id, cp.product_color_id, cp.product_other_id, cp.product_size_id, '
      ' cp.is_customized_product_immutable, cp.is_customized_product_active '
      '   FROM tbl_product p '
      '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
      '   WHERE p.product_id = %s; ',
      [(productQuery['product_id'])])
    
    if customizedProductQuery == None:
      return 'Produtos customizados inexistentes', 422

    # test request customized products
    if args.get('customized_products') is None or len(args['customized_products']) == 0:
      return 'Produtos customizaveis inválidos', 422
    
    for pos in range(len(args['customized_products'])):
      customizedProduct = args['customized_products'][pos]

      # used later to update in db
      customizedProduct['updated'] = False

      # checks for duplicants
      for sndpos in range(pos+1, len(args['customized_products'])):
        sndCustomizedProduct = args['customized_products'][sndpos]

        if (customizedProduct.get('product_color_id') == sndCustomizedProduct.get('product_color_id') and
          customizedProduct.get('product_other_id') == sndCustomizedProduct.get('product_other_id') and
          customizedProduct.get('product_size_id') == sndCustomizedProduct.get('product_size_id')):

          return 'Existe duplicatas nos produtos', 422

      # checks price
      if customizedProduct.get('product_price') is None or customizedProduct['product_price'] <= 0:
        return 'Preço do produto inválido para uma das variações', 422
      
      # checks quantity
      if customizedProduct.get('product_quantity') is None or customizedProduct['product_quantity'] < 0:
        return 'Quantidade do produto inválida para uma das variações', 422
      
      # checks size
      if customizedProduct.get('product_size_id') is None:
        return 'Tamanho do produto inválido para uma das variações', 422
    
    dbObjectIns = startGetDbObject()
    try:
      productId = productQuery['product_id']
      
      ### Product ###

      # if product is immutable (a sale/conditional is associated with it) and its data has changed(code or name), disables it and makes a new one
      if (
        productQuery['is_product_immutable'] and (
        productQuery['product_code'] != args['product_code'] or 
        productQuery['product_name'] != args['product_name'])):
          
        # disables immutable old product
        dbExecute(
          ' UPDATE tbl_product SET '
          '   is_product_active = FALSE '
          '   WHERE product_id = %s; ',
          [(productId)], True, dbObjectIns)
        
        # removes its not immutable custom products, and sets customizedProductQuery to [] to avoid incorrect reuse later
        for customProduct in customizedProductQuery:
          if not customProduct['is_customized_product_immutable']:
            dbExecute(
              ' DELETE FROM tbl_customized_product WHERE customized_product_id = %s; ',
              [(customProduct['customized_product_id'])], True, dbObjectIns)
        customizedProductQuery = []

        # removes its collections
        dbExecute(
          ' DELETE FROM tbl_product_has_collection WHERE product_id = %s; ',
          (productId,), True, dbObjectIns)

        # removes its types
        dbExecute(
          ' DELETE FROM tbl_product_has_type WHERE product_id = %s; ',
          (productId,), True, dbObjectIns)

        # inserts new product and get the new product id to use in customized products updates later
        dbExecute(
          ' INSERT INTO tbl_product (product_code, product_name, product_observations) VALUES (%s, %s, %s) ',
          [args['product_code'], args['product_name'], args['product_observations']], True, dbObjectIns)
        
        productIdQuery = dbGetSingle(
          " SELECT product_id FROM tbl_product WHERE product_code = %s AND product_name = %s AND is_product_active = TRUE; ",
          [args['product_code'], args['product_name']], True, dbObjectIns)
      
        if not productIdQuery:
          raise Exception('Exception empty select after update and insert from tbl_product patch')
        
        productId = productIdQuery['product_id']

        # inserts has collections
        if args.get('product_collection_ids') is not None:
          for collectionId in args['product_collection_ids']:
            dbExecute(
              ' INSERT INTO tbl_product_has_collection (product_id, product_collection_id) VALUES (%s, %s); ',
              [productId, collectionId], True, dbObjectIns)
        
        # inserts has types
        if args.get('product_type_ids') is not None:
          for typeId in args['product_type_ids']:
            dbExecute(
              ' INSERT INTO tbl_product_has_type (product_id, product_type_id) VALUES (%s, %s) ',
              [productId, typeId], True, dbObjectIns)
        
      # else removes or updates its collections or types if necessary
      else:

        # code or name - in this case, product is not immutable
        if (productQuery['product_code'] != args['product_code'] or 
          productQuery['product_name'] != args['product_name'] or
          productQuery['product_observations'] != args['product_observations']):

          dbExecute(
            ' UPDATE tbl_product SET '
            '   product_code = %s, '
            '   product_name = %s, '
            '   product_observations = %s '
            '   WHERE product_id = %s; ',
            [args['product_code'], args['product_name'], args['product_observations'], productId], True, dbObjectIns)

        # product collections
        if (args.get('product_collection_ids') is not None):

          for dbProductCollectionId in productQuery['product_collection_ids']:
            if dbProductCollectionId not in args['product_collection_ids']:
              dbExecute(
                ' DELETE FROM tbl_product_has_collection WHERE product_id = %s AND product_collection_id = %s; ',
                [productId, dbProductCollectionId], True, dbObjectIns)
          
          for argsProductCollectionId in args['product_collection_ids']:
            if argsProductCollectionId not in productQuery['product_collection_ids']:
              dbExecute(
                ' INSERT INTO tbl_product_has_collection (product_id, product_collection_id) VALUES (%s, %s) ',
                [productId, argsProductCollectionId], True, dbObjectIns)
        
        # product types
        if (args.get('product_type_ids') is not None):

          for dbProductTypesId in productQuery['product_type_ids']:
            if dbProductTypesId not in args['product_type_ids']:
              dbExecute(
                ' DELETE FROM tbl_product_has_type WHERE product_id = %s AND product_type_id = %s; ',
                [productId, dbProductTypesId], True, dbObjectIns)
          
          for argsProductTypeId in args['product_type_ids']:
            if argsProductTypeId not in productQuery['product_type_ids']:
              dbExecute(
                ' INSERT INTO tbl_product_has_type (product_id, product_type_id) VALUES (%s, %s) ',
                [productId, argsProductTypeId], True, dbObjectIns)

      ### Customized Products ###
      for dbCustomizedProduct in customizedProductQuery:
        productFound = False

        for argsCustomizedProduct in args['customized_products']:

          if (dbCustomizedProduct.get('product_color_id') == argsCustomizedProduct.get('product_color_id') and
            dbCustomizedProduct.get('product_other_id') == argsCustomizedProduct.get('product_other_id') and
            dbCustomizedProduct.get('product_size_id') == argsCustomizedProduct.get('product_size_id')):
            productFound = True
            break

        # if dbCustomizedProduct is in args - only updates it because its data is equal except its price and quantity
        if productFound:
          dbExecute(
            ' UPDATE tbl_customized_product SET '
            '   product_id = %s, '
            '   customized_product_price = %s, '
            '   customized_product_quantity = %s, '
            '   is_customized_product_active = TRUE '
            '   WHERE customized_product_id = %s; ',
            [ productId,
              argsCustomizedProduct['product_price'],
              argsCustomizedProduct['product_quantity'],
              dbCustomizedProduct['customized_product_id']
            ], True, dbObjectIns)
          
          # set updated = True for those customized products to avoid reupdating later
          argsCustomizedProduct['updated'] = True

        # if dbCustomizedProduct not found in args - remove db product by deleting or disabling it
        else:
          # disable if is immutable
          if dbCustomizedProduct['is_customized_product_immutable']:
            dbExecute(
              ' UPDATE tbl_customized_product SET '
              '   is_customized_product_active = FALSE '
              '   WHERE customized_product_id = %s; ',
              [(dbCustomizedProduct['customized_product_id'])], True, dbObjectIns)
          # delete if not
          else:
            dbExecute(
              ' DELETE FROM tbl_customized_product WHERE customized_product_id = %s; ',
              [(dbCustomizedProduct['customized_product_id'])], True, dbObjectIns)

      # for the rest of not updated customized products, inserts in db    
      for argsCustomizedProduct in args['customized_products']:
        if not argsCustomizedProduct['updated']:
          dbExecute(
            ' INSERT INTO tbl_customized_product (product_id, product_color_id, product_other_id, product_size_id, '
            ' customized_product_price, customized_product_quantity) '
            '   VALUES (%s, %s, %s, %s, %s, %s) ',
            [
              productId,
              argsCustomizedProduct['product_color_id'] if argsCustomizedProduct.get('product_color_id') else None,
              argsCustomizedProduct['product_other_id'] if argsCustomizedProduct.get('product_other_id') else None,
              argsCustomizedProduct['product_size_id'],
              argsCustomizedProduct['product_price'],
              argsCustomizedProduct['product_quantity']
            ], True, dbObjectIns)
      
    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao atualizar o produto ' + str(e), 500
    dbCommit(dbObjectIns)

    return {}, 204
  
  def delete(self):

    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('product_id', location='json', type=int, help='product id, required', required=True)
    args = argsParser.parse_args()

    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # get and test product
    productQuery = dbGetSingle(
      ' SELECT * FROM tbl_product WHERE product_id = %s AND is_product_active = TRUE; ',
      [(args['product_id'])])
    
    if productQuery == None:
      return 'Id do produto a ser removido inválido', 422

    # get has collections
    rawHasCollections = dbGetAll(
      ' SELECT phc.product_has_collection_id '
      '   FROM tbl_product p '
      '   JOIN tbl_product_has_collection phc ON p.product_id = phc.product_id '
      '   WHERE p.product_id = %s; ',
      [(productQuery['product_id'])])
    productQuery['product_has_collection_ids'] = [hasCollection['product_has_collection_id'] for hasCollection in rawHasCollections]

    # get has types
    rawHasTypes = dbGetAll(
      ' SELECT pht.product_has_type_id  '
	    '   FROM tbl_product p '
      '   JOIN tbl_product_has_type pht ON p.product_id = pht.product_id '
      '   WHERE p.product_id = %s; ',
      [(productQuery['product_id'])])
    productQuery['product_has_type_ids'] = [hasTypes['product_has_type_id'] for hasTypes in rawHasTypes]

    # get customized products
    customizedProductQuery = dbGetAll(
      ' SELECT cp.customized_product_id, cp.product_id, cp.product_color_id, cp.product_other_id, cp.product_size_id, '
      ' cp.is_customized_product_immutable, cp.is_customized_product_active '
      '   FROM tbl_product p '
      '   JOIN tbl_customized_product cp ON p.product_id = cp.product_id '
      '   WHERE p.product_id = %s; ',
      [(productQuery['product_id'])])
    
    if customizedProductQuery == None:
      return 'Produtos customizados inexistentes', 422
    
    dbObjectIns = startGetDbObject()
    try:
      hasImmutableRows = False

      # customized products
      for customizedProduct in customizedProductQuery:

        if customizedProduct['is_customized_product_immutable']:
          hasImmutableRows = True

          if customizedProduct['is_customized_product_active']:
            dbExecute(
              ' UPDATE tbl_customized_product SET '
              '   is_customized_product_active = FALSE '
              '   WHERE customized_product_id = %s; ',
              [(customizedProduct['customized_product_id'])], True, dbObjectIns)
          
        else:
          dbExecute(
            ' DELETE FROM tbl_customized_product WHERE customized_product_id = %s; ',
            [(customizedProduct['customized_product_id'])], True, dbObjectIns)

      # types
      for hasTypesId in productQuery['product_has_type_ids']:
        dbExecute(
          ' DELETE FROM tbl_product_has_type WHERE product_has_type_id = %s; ',
          [(hasTypesId)], True, dbObjectIns)

      # collections
      for hasCollectionId in productQuery['product_has_collection_ids']:
        dbExecute(
          ' DELETE FROM tbl_product_has_collection WHERE product_has_collection_id = %s; ',
          [(hasCollectionId)], True, dbObjectIns)

      # product
      if productQuery['is_product_immutable'] or hasImmutableRows:
        dbExecute(
          ' UPDATE tbl_product SET '
          '   is_product_active = FALSE '
          '   WHERE product_id = %s; ',
          [(args['product_id'])], True, dbObjectIns)
        
      else:
        dbExecute(
          ' DELETE FROM tbl_product WHERE product_id = %s; ',
          [(args['product_id'])], True, dbObjectIns)
      
    except Exception as e:
      dbRollback(dbObjectIns)
      traceback.print_exc()
      return 'Erro ao criar o usuario ' + str(e), 500
    dbCommit(dbObjectIns)
    
    return {}, 204

class ProductsApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='query limit, required', required=True)
    argsParser.add_argument('offset', location='args', type=int, help='query offset, required', required=True)
    argsParser.add_argument('order_by', location='args', type=str, help='query orderby', required=True)
    argsParser.add_argument('order_by_asc', location='args', type=str, help='query orderby ascendant', required=True)
    argsParser.add_argument('product_code', location='args', type=str, help='product code')
    argsParser.add_argument('product_name', location='args', type=str, help='product name')
    argsParser.add_argument('product_color_id', location='args', type=int, help='product color id')
    argsParser.add_argument('product_other_id', location='args', type=int, help='product other id')
    argsParser.add_argument('product_size_id', location='args', type=int, help='product size id')
    argsParser.add_argument('product_collection_id', location='args', type=int, help='product list of assigned collections ids')
    argsParser.add_argument('product_type_id', location='args', type=int, help='product list of assigned types')
    argsParser.add_argument('product_quantity_initial', location='args', type=int, help='initial product quantity')
    argsParser.add_argument('product_quantity_final', location='args', type=int, help='final product quantity')
    argsParser.add_argument('product_price_initial', location='args', type=float, help='initial product price')
    argsParser.add_argument('product_price_final', location='args', type=float, help='final product price')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    orderByAsc = (args['order_by_asc'] == '1' or args['order_by_asc'].lower() == 'true')
    
    cpFilterScrypt, cpFilterArgs = dbGetSqlFilterScrypt(
      [
        {'filterCollum':'cp.is_customized_product_active', 'filterOperator':'=', 'filterValue':True},
        {'filterCollum':'cp.product_color_id', 'filterOperator':'=', 'filterValue':args.get('product_color_id')},
        {'filterCollum':'cp.product_other_id', 'filterOperator':'=', 'filterValue':args.get('product_other_id')},
        {'filterCollum':'cp.product_size_id', 'filterOperator':'=', 'filterValue':args.get('product_size_id')},
        {'filterCollum':'cp.customized_product_quantity', 'filterOperator':'>=', 'filterValue':args.get('product_quantity_initial')},
        {'filterCollum':'cp.customized_product_quantity', 'filterOperator':'<=', 'filterValue':args.get('product_quantity_final')},
        {'filterCollum':'cp.customized_product_price', 'filterOperator':'>=', 'filterValue':args.get('product_price_initial')},
        {'filterCollum':'cp.customized_product_price', 'filterOperator':'<=', 'filterValue':args.get('product_price_final')}
      ],
      groupByCollumns='cp.product_id', filterEnding='')
    
    phcFilterScrypt, phcFilterArgs = dbGetSqlFilterScrypt(
      [{'filterCollum':'pc.product_collection_id', 'filterOperator':'LIKE%_%', 'filterValue':args.get('product_collection_id')}],
      groupByCollumns='phc.product_id', filterEnding='')
    
    phtFilterScrypt, phtFilterArgs = dbGetSqlFilterScrypt(
      [{'filterCollum':'pt.product_type_id', 'filterOperator':'LIKE%_%', 'filterValue':args.get('product_type_id')}],
      groupByCollumns='pht.product_id', filterEnding='')
    
    geralFilterScrypt, geralFilterScryptNoLimit, geralFilterArgs, geralFilterArgsNoLimit =  dbGetSqlFilterScrypt(
      [
        {'filterCollum':'p.is_product_active', 'filterOperator':'=', 'filterValue':True},
        {'filterCollum':'p.product_code', 'filterOperator':'LIKE%_%', 'filterValue':args.get('product_code')},
        {'filterCollum':'p.product_name', 'filterOperator':'LIKE%_%', 'filterValue':args.get('product_name')},
        {'filterCollum':'pc_names.product_collection_ids', 'filterOperator':'LIKE%_%', 'filterValue':args.get('product_collection_id')},
        {'filterCollum':'pt_names.product_type_ids', 'filterOperator':'LIKE%_%', 'filterValue':args.get('product_type_id')}
      ],
      groupByCollumns='p.product_id', orderByCollumns=args['order_by'], orderByAsc=orderByAsc, limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)
    
    allFilterArgs = cpFilterArgs + phcFilterArgs + phtFilterArgs + geralFilterArgs
    allFilterArgsNoLimit = cpFilterArgs + phcFilterArgs + phtFilterArgs + geralFilterArgsNoLimit
    allFilterScrypt = (
      '     FROM tbl_product p '
      '     JOIN ( '
      '       SELECT cp.product_id , '
      '         GROUP_CONCAT(pc.product_color_id) AS product_color_ids, '
      '         GROUP_CONCAT(pc.product_color_name) AS product_color_names, '

      '         GROUP_CONCAT(po.product_other_id) AS product_other_ids, '
      '         GROUP_CONCAT(po.product_other_name) AS product_other_names, '

      '         GROUP_CONCAT(ps.product_size_id) AS product_size_ids, '
      '         GROUP_CONCAT(ps.product_size_name) AS product_size_names, '

      '         GROUP_CONCAT(cp.customized_product_price) AS customized_product_prices, '
      '         GROUP_CONCAT(cp.customized_product_quantity) AS customized_product_quantityes '
      '           FROM tbl_customized_product cp '
      '           JOIN tbl_product_size ps ON cp.product_size_id = ps.product_size_id '
      '           LEFT JOIN tbl_product_color pc ON cp.product_color_id = pc.product_color_id '
      '           LEFT JOIN tbl_product_other po ON cp.product_other_id = po.product_other_id '
      + cpFilterScrypt +
      '     ) cp ON p.product_id = cp.product_id '
      '     LEFT JOIN ( '
      '       SELECT product_id, '
      '         GROUP_CONCAT(pc.product_collection_id) AS product_collection_ids, '
      '         GROUP_CONCAT(pc.product_collection_name) AS product_collection_names '
      '           FROM tbl_product_collection pc '
      '           JOIN tbl_product_has_collection phc ON pc.product_collection_id = phc.product_collection_id '
      + phcFilterScrypt +
      '     ) pc_names ON p.product_id = pc_names.product_id '
      '     LEFT JOIN ( '
      '       SELECT product_id, '
      '         GROUP_CONCAT(pt.product_type_id) AS product_type_ids, '
      '         GROUP_CONCAT(pt.product_type_name) AS product_type_names '
      '           FROM tbl_product_type pt '
      '           JOIN tbl_product_has_type pht ON pt.product_type_id = pht.product_type_id '
      + phtFilterScrypt +
      '     ) pt_names ON p.product_id = pt_names.product_id '
    )

    countScrypt = (
      ' SELECT COUNT(*) as countp '
      + allFilterScrypt
      + geralFilterScryptNoLimit
    )
    geralScrypt = (
      ' SELECT p.product_id, p.product_code, p.product_name, p.is_product_active, p.product_creation_date_time, '
      '   cp.product_color_ids, cp.product_color_names, cp.product_other_ids, cp.product_other_names, cp.product_size_ids, cp.product_size_names, '
      '   cp.customized_product_prices, cp.customized_product_quantityes, '
      '   pc_names.product_collection_names, pc_names.product_collection_ids, '
      '   pt_names.product_type_ids, pt_names.product_type_names '
      + allFilterScrypt 
      + geralFilterScrypt
    )

    countProducts = dbGetSingle(countScrypt, allFilterArgsNoLimit)
    productsQuery = dbGetAll(geralScrypt, allFilterArgs)

    if not countProducts or not productsQuery:
      return { 'count': 0, 'products': [] }, 200

    for productRow in productsQuery:
      productRow['product_creation_date_time'] = str(productRow['product_creation_date_time'])
    
    return { 'count': countProducts['countp'], 'products': productsQuery }, 200
  
class ProductInfoApi(Resource):
    
  def get(self):
      
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)
    
    query = {}
    query['products'] = dbGetAll(' SELECT product_id, product_name, product_code FROM tbl_product p WHERE p.is_product_active = TRUE; ')
    query['collections'] = dbGetAll(' SELECT * FROM tbl_product_collection ORDER BY product_collection_pos; ')
    query['types'] = dbGetAll(' SELECT * FROM tbl_product_type ORDER BY product_type_pos; ')
    query['colors'] = dbGetAll(' SELECT * FROM tbl_product_color ORDER BY product_color_pos; ')
    query['others'] = dbGetAll(' SELECT * FROM tbl_product_other ORDER BY product_other_pos; ')
    query['sizes'] = dbGetAll(' SELECT * FROM tbl_product_size ORDER BY product_size_pos; ')
    
    return query, 200