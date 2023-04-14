from flask import Flask, abort
from flask_restful import Resource, Api, reqparse

from utils.dbUtils import *
from services.authentication import isAuthTokenValid

# when tbl_event_name changes please restart backend
globalEventNames = None

class EventsApi(Resource):
    
  def get(self):

    global globalEventNames
    
    argsParser = reqparse.RequestParser()
    argsParser.add_argument('Authorization', location='headers', type=str, help='Bearer with jwt given by server in user autentication, required', required=True)
    argsParser.add_argument('limit', location='args', type=int, help='number of rows returned, required', required=True)
    argsParser.add_argument('offset', location='args', type=int, help='start row from db, required', required=True)
    argsParser.add_argument('event_user_id', location='args', type=str, help='event user id')
    argsParser.add_argument('event_name_id', location='args', type=str, help='event name id')
    argsParser.add_argument('event_start_date_time', location='args', type=str, help='start event date filter')
    argsParser.add_argument('event_end_date_time', location='args', type=str, help='end event date filter')
    args = argsParser.parse_args()
    
    isValid, returnMessage = isAuthTokenValid(args)
    if not isValid:
      abort(401, 'Autenticação com o token falhou: ' + returnMessage)

    # get event names and stores in a global variable to not perform a select again
    if globalEventNames == None:

      globalEventNames = dbGetAll(' SELECT event_name_id, event_name FROM tbl_event_name; ')
      if not globalEventNames:
        raise Exception('Error trying to get global event names')
    
    # get events with filters
    filterScrypt, filterScryptNoLimit, filterArgs, filterArgsNoLimit = dbGetSqlFilterScrypt(
      [
        {'filterCollum':'e.event_user_id', 'filterOperator':'=', 'filterValue':args.get('event_user_id')},
        {'filterCollum':'en.event_name_id', 'filterOperator':'=', 'filterValue':args.get('event_name_id')},
        {'filterCollum':'e.event_date_time', 'filterOperator':'>=', 'filterValue':args.get('event_start_date_time')},
        {'filterCollum':'e.event_date_time', 'filterOperator':'<=', 'filterValue':args.get('event_end_date_time')}
      ],
      orderByCollumns='e.event_date_time', limitValue=args['limit'], offsetValue=args['offset'], getFilterWithoutLimits=True)

    eventsQuery = dbGetAll(
      ' SELECT event_id, event_name, event_user_id, person_name AS event_user_name, event_description_args, event_date_time '
      '   FROM tbl_event e '
      '   JOIN tbl_event_name en ON e.event_name_id = en.event_name_id '
      '   JOIN tbl_person p ON e.event_user_id = p.person_id ' 
      + filterScrypt, filterArgs)
    
    countEventsQuery = dbGetSingle(
      ' SELECT COUNT(*) AS count_events '
      '   FROM tbl_event e '
      '   JOIN tbl_event_name en ON e.event_name_id = en.event_name_id '
      '   JOIN tbl_person p ON e.event_user_id = p.person_id '
      + filterScryptNoLimit, filterArgsNoLimit)
    
    if not eventsQuery or not countEventsQuery:
      return { 'count_events' : 0, 'events' : [], 'event_names' : globalEventNames }, 200
    
    for eventRow in eventsQuery:
      eventRow['event_date_time'] = str(eventRow['event_date_time'])

    return { 'count_events' : countEventsQuery['count_events'], 'events' : eventsQuery, 'event_names' : globalEventNames }, 200