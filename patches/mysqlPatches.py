import traceback
import random
from utils.dbUtils import *

def createSaleHasPaymentMethodInstallment():

  print("# Starting createSaleHasPaymentMethodInstallment patch...")

  print("\tDropping and Creating table tbl_sale_has_payment_method_installment...")
  try:
    dbExecute(' DROP TABLE IF EXISTS tbl_sale_has_payment_method_installment; ')
    sqlScrypt = (
      ' CREATE TABLE IF NOT EXISTS tbl_sale_has_payment_method_installment( '
      '   sale_has_payment_method_installment_id INT NOT NULL AUTO_INCREMENT, '
      '   sale_id INT NOT NULL, '
      '   payment_method_Installment_id INT NOT NULL, '
      '   payment_method_total_value FLOAT NOT NULL, '
	    '   PRIMARY KEY (sale_has_payment_method_installment_id), '
      '   FOREIGN KEY (sale_id) REFERENCES tbl_sale(sale_id), '
      '   FOREIGN KEY (payment_method_Installment_id) REFERENCES tbl_payment_method_installment(payment_method_installment_id), '
      '   CHECK (payment_method_total_value > 0) '
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
        ' INSERT INTO tbl_sale_has_payment_method_installment (sale_id, payment_method_Installment_id, payment_method_total_value) VALUES (%s, %s, %s); ', 
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