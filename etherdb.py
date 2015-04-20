#!/usr/bin/env python

import sys, json, re
from logging import getLogger, basicConfig

from webob import Request, Response
from webob.exc import HTTPException, HTTPNotFound, HTTPInternalServerError, HTTPSeeOther, HTTPMethodNotAllowed

import sqlite3

basicConfig(stream=sys.stderr, level=10)

log = getLogger('etherdb')
        

class EtherDBServer:
    def __init__(self):
        log.debug('opening the database')
        self.conn = sqlite3.connect('test.db')
    def do_request(self, req):
        name = req.path_info

        # re-call with trailing /
        if not name:
            return HTTPSeeOther(location=req.script_name + '/' + req.path_info + '?' + req.query_string)
        # force index.html
        if name[-1] == '/':
            name += 'index.html'

        if re.search('^/.*\.(?:html|js|css)$', name):
            if re.search('\.html$', name):
                content_type = 'text/html'
            elif re.search('\.js$', name):
                content_type = 'application/javascript'
            elif re.search('\.css$', name):
                content_type = 'text/css'
            else:
                content_type = 'text/plain'

            log.debug('name %s, content-type %s', name, content_type)

            f = open(name[1:])
            body = f.read()
            return Response(body=body, content_length=len(body), content_type=content_type)

        elif re.search('^/json/(?:load|save).json$', name):
            cursor = self.conn.cursor()
            cursor.execute('select rowid, * from test')

            cols = [x[0] for x in cursor.description]

            # filter rowid column
            id_idx = cols.index('rowid')
            cols = cols[:id_idx] + cols[id_idx+1:]

            if req.method == 'GET':
                rowdata = [cols]

                for row in cursor:
                    rowdata.append(row[:id_idx] + row[id_idx+1:])
                
                body = json.dumps({'data': rowdata})
                return Response(body=body, content_length=len(body), content_type='application/json')
            elif req.method == 'POST':
                log.debug('POST body: %s', req.body)
                parsed = json.loads(req.body)

                if parsed['type'] == 'change':
                    for change in parsed['data']:
                        # not a column header update
                        if change[0] != 0:
                            row_id = change[0] + 1
                            cmd = "update test set %s=%s where rowid=%d;" % (cols[change[1]], change[3], row_id)
                            log.debug(cmd)
                            cursor.execute(cmd)
                            self.conn.commit()
                
                body = "{ \"result\": \"ok\" }"
                return Response(body=body, content_length=len(body), content_type='application/json')
            else:
                raise HTTPMethodNotAllowed

        raise HTTPNotFound

def do_request(environ, start_response):
    req = Request(environ)
    log.debug('%s', repr(req))
    server = EtherDBServer()
    try:
        return server.do_request(req)(environ, start_response)
    except HTTPException, err:
        return err(environ, start_response)
    except:
        log.exception('at top level')
        raise

if __name__ == "__main__":
    from waitress import serve
    serve(do_request, host='127.0.0.1', port=8080)
