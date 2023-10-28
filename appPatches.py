from dotenv import load_dotenv, find_dotenv
from patches.mysqlPatches import fixClientChildrenProductSizeId
from utils.sistemConfig import getMissingEnvironmentVar

# Env vars
print('# Checking env vars')
if getMissingEnvironmentVar():
  print('# Loading and checking environment from .env')
  load_dotenv(find_dotenv())
  missingVar = getMissingEnvironmentVar()
  if missingVar:
    print('# Error - Missing ' + str(missingVar) + ' environment variable')
    exit()

# Warning: Make a backup before using any changing script
fixClientChildrenProductSizeId()