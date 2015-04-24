#!/usr/bin/env python

import sys, json, re, sqlite3
from logging import getLogger, basicConfig

import six

from webob import Request, Response
from webob.exc import HTTPException, HTTPNotFound, HTTPInternalServerError, HTTPSeeOther, HTTPMethodNotAllowed

from waitress import serve


basicConfig(stream=sys.stderr, level=10)

log = getLogger('etherdb')
        

class EtherDBServer:
    def __init__(self, filename):
        self.filename = filename
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
            return Response(body=body, content_length=len(body), content_type=content_type, charset='utf-8')

        elif re.search('^/json/(?:load|save).json$', name):
            log.debug('opening the database')
            conn = sqlite3.connect(self.filename)
            cursor = conn.cursor()
            cursor.execute('select rowid, * from test')

            cols = tuple([x[0] for x in cursor.description])

            typecursor = conn.cursor()
            typecmd = 'select ' + ', '.join(['typeof({0})'.format(x) for x in cols]) + ' from test limit 1'
            typecursor.execute(typecmd)
            coltypes = typecursor.fetchone()
            print(coltypes)

            if req.method == 'GET':
                rowdata = [cols]

                for row in cursor:
                    rowdata.append(row)
                
                body = json.dumps({'data': rowdata})
                return Response(body=body, content_length=len(body), content_type='application/json', charset='utf-8')
            elif req.method == 'POST':
                log.debug('POST body: %s', req.body)
                parsed = json.loads(six.text_type(req.body, 'utf-8'))

                if parsed['type'] == 'change':
                    for change in parsed['data']:
                        # not a column header update
                        if change[0] != 0:
                            rowid = change[0]
                            if re.search('char|text|clob|blob', coltypes[change[1]], re.IGNORECASE):
                              cmd = "update test set %s=\"%s\" where rowid=%d;" % (cols[change[1]], change[3], rowid)
                            else:
                              cmd = "update test set %s=%s where rowid=%d;" % (cols[change[1]], change[3], rowid)
                            log.debug(cmd)
                            cursor.execute(cmd)
                            conn.commit()
                
                body = "{ \"result\": \"ok\" }"
                return Response(body=body, content_length=len(body), content_type='application/json', charset='utf-8')
            else:
                raise HTTPMethodNotAllowed

        raise HTTPNotFound

def do_request(filename, environ, start_response):
    req = Request(environ)
    log.debug('%s', repr(req))
    server = EtherDBServer(filename)
    try:
        return server.do_request(req)(environ, start_response)
    except HTTPException as err:
        return err(environ, start_response)
    except:
        log.exception('at top level')
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: %s FILE\n" % sys.argv[0])
        sys.exit(1)
    filename = sys.argv[1]

    serve(lambda *args: do_request(filename, *args), host='127.0.0.1', port=8080)
