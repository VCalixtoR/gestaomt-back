import traceback
import random
from utils.dbUtils import *

def fixClientChildrenProductSizeId():

  print("# Starting fixClientChildrenProductSizeId patch...")
  
  dbObjectIns = startGetDbObject()
  try:
    print("\tGet Client Children...")
    cchildren = dbGetAll(
      ' SELECT children_id, children_client_id, children_name, children_birth_date, children_product_size_id FROM tbl_client_children cc ORDER BY cc.children_id; ',
      transactionMode=True,
      dbObjectIns=dbObjectIns
    )

    # use random numbers to print children before and after
    randomNumbers = [random.randrange(0,len(cchildren)) for _ in range(15)]

    print("\tChildren Before:")
    for number in randomNumbers:
      print(f"\t\t{cchildren[number]}")

    print("\tUpdating Children Product Size Id...")
    for cchild in cchildren:
      dbExecute(
        ' UPDATE tbl_client_children SET children_product_size_id = %s WHERE children_id = %s; ',
        [cchild['children_product_size_id']+1, cchild["children_id"]],
        transactionMode=True,
        dbObjectIns=dbObjectIns
      )
    
    print("\tGet Updated Client Children...")
    cchildren = dbGetAll(
      ' SELECT children_id, children_client_id, children_name, children_birth_date, children_product_size_id FROM tbl_client_children cc ORDER BY cc.children_id; ',
      transactionMode=True,
      dbObjectIns=dbObjectIns
    )

    print("\tChildren After:")
    for number in randomNumbers:
      print(f"\t\t{cchildren[number]}")

  except Exception as e:
    dbRollback(dbObjectIns)
    print(f"\tRollback done! An error ocurred: {str(e)}")
    traceback.print_exc()
    return False

  print("\tCommiting changes...")
  dbCommit(dbObjectIns)

  print("\tDone without errors!")
  return True

def createSaleHasPaymentMethodInstallment():

  print("# Starting createSaleHasPaymentMethodInstallment patch...")

  print("\tRenaming old installment to correct sintaxe...")
  try:
    dbExecute(
      ' ALTER TABLE tbl_payment_method_installment '
      ' RENAME COLUMN payment_method_Installment_number TO payment_method_installment_number; '
    )
  except Exception as e:
    print(f"\tAn error ocurred while renaming old installment: {str(e)}")
    traceback.print_exc()
    return False

  print("\tDropping and Creating table tbl_sale_has_payment_method_installment...")
  try:
    dbExecute(' DROP TABLE IF EXISTS tbl_sale_has_payment_method_installment; ')
    sqlScrypt = (
      ' CREATE TABLE IF NOT EXISTS tbl_sale_has_payment_method_installment( '
      '   sale_has_payment_method_installment_id INT NOT NULL AUTO_INCREMENT, '
      '   sale_id INT NOT NULL, '
      '   payment_method_installment_id INT NOT NULL, '
      '   payment_method_value FLOAT NOT NULL, '
	    '   PRIMARY KEY (sale_has_payment_method_installment_id), '
      '   FOREIGN KEY (sale_id) REFERENCES tbl_sale(sale_id), '
      '   FOREIGN KEY (payment_method_installment_id) REFERENCES tbl_payment_method_installment(payment_method_installment_id), '
      '   CHECK (payment_method_value > 0) '
      ' ); '
    )
    dbExecute(sqlScrypt)
  except Exception as e:
    print(f"\tAn error ocurred while dropping or creating tbl_sale_has_payment_method_installment: {str(e)}")
    traceback.print_exc()
    return False

  print("\tStarting transaction...")
  dbObjectIns = startGetDbObject()
  try:

    print("\tGet Sales...")
    sales = dbGetAll(
      ' SELECT s.sale_id, s.sale_payment_method_installment_id, s.sale_total_value FROM tbl_sale s ORDER BY s.sale_id; ',
      transactionMode=True,
      dbObjectIns=dbObjectIns
    )

    # use random numbers to print sales and saleHasPayments
    randomNumbers = [random.randrange(0,len(sales)) for _ in range(10)]

    print("\tSales:")
    for number in randomNumbers:
      print(f"\t\t{sales[number]}")

    print("\tInserting sale info into tbl_sale_has_payment_method_installment...")
    for sale in sales:
      dbExecute(
        ' INSERT INTO tbl_sale_has_payment_method_installment (sale_id, payment_method_installment_id, payment_method_value) VALUES (%s, %s, %s); ', 
        [sale["sale_id"], sale["sale_payment_method_installment_id"], sale["sale_total_value"]],
        transactionMode=True,
        dbObjectIns=dbObjectIns
      )
    
    print("\tGet SaleHasPayments...")
    saleHasPayments = dbGetAll(
      ' SELECT * FROM tbl_sale_has_payment_method_installment ORDER BY sale_has_payment_method_installment_id; ',
      transactionMode=True,
      dbObjectIns=dbObjectIns
    )

    print("\tSaleHasPayments:")
    for number in randomNumbers:
      print(f"\t\t{saleHasPayments[number]}")

  except Exception as e:
    dbRollback(dbObjectIns)
    print(f"\tRollback done! An error ocurred: {str(e)}")
    traceback.print_exc()
    return False
  
  print("\tCommiting changes...")
  dbCommit(dbObjectIns)

  print("\tDeleting sale collumn sale_payment_method_installment_id...")
  try:
  
    print("\tSales before:")
    rawSales = dbGetAll(' SELECT * FROM tbl_sale s ORDER BY s.sale_id; ')

    # use random numbers to print sales and saleHasPayments
    randomNumbers = [random.randrange(0,len(rawSales)) for _ in range(10)]

    for number in randomNumbers:
      print(f"\t\t{rawSales[number]}")

    # Transactions does not support ALTER TABLE
    dbExecute(' ALTER TABLE tbl_sale DROP CONSTRAINT tbl_sale_ibfk_3; ')
    dbExecute(' ALTER TABLE tbl_sale DROP COLUMN sale_payment_method_installment_id; ')
    
    print("\tSales after:")
    newSales = dbGetAll(' SELECT * FROM tbl_sale s ORDER BY s.sale_id; ')
    for number in randomNumbers:
      print(f"\t\t{newSales[number]}")

  except Exception as e:
    print(f"\tAn error ocurred while dropping or creating tbl_sale_has_payment_method_installment: {str(e)}")
    traceback.print_exc()
    return False

  print("# Done without errors!")
  return True