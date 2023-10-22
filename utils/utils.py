# converts a number to a brl currency
def toBRCurrency(n):
  return "R$ " + "{:.2f}".format(n).replace('.',',')