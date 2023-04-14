import os

def getMissingEnvironmentVar():

  if not os.getenv('FRONT_BASE_URL'):
    return 'FRONT_BASE_URL'
  
  if not os.getenv('SQL_HOST'):
    return 'SQL_HOST'
  if not os.getenv('SQL_SCHEMA'):
    return 'SQL_SCHEMA'
  if not os.getenv('SQL_PORT'):
    return 'SQL_PORT'
  if not os.getenv('SQL_USER'):
    return 'SQL_USER'
  if not os.getenv('SQL_PASSWORD'):
    return 'SQL_PASSWORD'

  if not os.getenv('SYS_DEBUG'):
    return 'SYS_DEBUG'

  return None