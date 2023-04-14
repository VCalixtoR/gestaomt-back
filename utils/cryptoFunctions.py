from Crypto.PublicKey import RSA
from pathlib import Path

private_key = None
public_key = None

# load or create and load keys
def loadGenerateKeys():

  global private_key, public_key

  print('# Loading keys')

  privatek_path = Path.cwd() / 'private-key.pem'
  publick_path = Path.cwd() / 'public-key.pem'

  # when first executed generate key pair
  if not privatek_path.is_file() or not publick_path.is_file():
    
    # private key
    pvk = RSA.generate(2048)
    pvk_str = pvk.exportKey()
    with open(privatek_path, "w") as pvk_file:
      print("{}".format(pvk_str.decode()), file=pvk_file)

    # public key
    pbk = pvk.publickey()
    pbk_str = pbk.exportKey()
    with open(publick_path, "w") as pbk_file:
      print("{}".format(pbk_str.decode()), file=pbk_file)
    
    print('# Private and public keys generated')

  private_key = open(privatek_path).read()
  public_key = open(publick_path).read()

def getPrivateK():

  global private_key

  if not private_key:
    loadGenerateKeys()

  return private_key

def getPublicK():

  global public_key

  if not public_key:
    loadGenerateKeys()

  return public_key