import threading
import pprint
import json
import re
import os

from bottle import route, run, Bottle, response, get, post, request, error, static_file, view, TEMPLATE_PATH, WSGIRefServer

core = ''
app = Bottle()

TEMPLATE_PATH.append(os.path.dirname(os.path.realpath(__file__))+ '/views')

print(TEMPLATE_PATH)

def start(passed_core):
    global core
    core = passed_core
    server = MyServer(host='0.0.0.0', port=8080, debug=True)
    threading.Thread(target=run, kwargs=dict(server=server)).start()
    return server

def stop(server):
    server.shutdown()

###################################################################
##
# API Endpoints
##
###################################################################

@post('/plms/<DevID>')
def add_plm(DevID):
    '''
    Add a plm.

    :param DevID: the device id
    :type post_id: hex
    :form port: the usb/serial port of the plm

    :reqheader Accept: application/json
    :resheader Content-Type: application/json

    :statuscode 200: no error
    '''
    DevID = DevID.upper()
    if not is_valid_DevID(DevID):
        return error_invalid_DevID()
    elif not is_unique_DevID(DevID):
        return error_DevID_not_unique()
    elif 'port' not in request.json:
        return error_missing_attribute('port')
    else:
        return 'good enough'

###################################################################
##
# Template Responses
##
###################################################################

@route('/')
@view('index')
def index_page():
    return dict(modems=list_modems())

@route('/modem/<DevID>')
@view('modem')
def modem_page(DevID):
    return dict(device_id=DevID)

###################################################################
##
# Static Responses
##
###################################################################

@route('/static/<path:path>')
def callback(path):
    return static_file(path, root='insteon/static')

###################################################################
##
# Error Responses
##
###################################################################

def error_invalid_DevID():
    return generate_error(400, 'Invalid Device ID.')

def error_DevID_not_unique():
    return generate_error(409, 'Device ID is already in use.')

def error_missing_attribute(attribute):
    return generate_error(400, 'Missing required attribute ' + attribute)

@error(405)
def error_405(error):
    return jsonify(generate_error(405, 'Method not allowed.'))

###################################################################
##
# Data Generating Functions
##
###################################################################

def list_modems():
    modems = core.get_all_modems()
    ret = []
    for modem in modems:
        ret.append( { modem.dev_addr_str : {
            'dev_cat': modem.dev_cat,
            'sub_cat': modem.sub_cat,
            'firmware': modem.firmware,
            'port': modem.port,
            'port_active': modem.port_active
            }}
        )
    return ret


###################################################################
##
# Helper Functions
##
###################################################################

def generate_error(code, text):
    ret = {"error": {
            "code": code,
            "message": text
        }
    }
    response.status = code
    return ret

def is_valid_DevID(DevID):
    ret = False
    pattern = re.compile("^([A-F]|[0-9]){6}$")
    if pattern.match(DevID):
        ret = True
    return ret

def is_unique_DevID(DevID):
    is_unique = True
    plms = core.get_all_plms()
    for plm in plms:
        if plm.dev_addr_str == DevID:
            is_unique = False
            break
        else:
            devices = plm.get_all_devices()
            for device in devices:
                if device.dev_addr_str == DevID:
                    is_unique = False
                    break
    return is_unique

def jsonify(data):
    return json.dumps(data, indent=4, sort_keys=True)

class MyServer(WSGIRefServer):
    def run(self, app): # pragma: no cover
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
        from wsgiref.simple_server import make_server
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self): # Prevent reverse DNS lookups please.
                return self.client_address[0]
            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls  = self.options.get('server_class', WSGIServer)

        if ':' in self.host: # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        srv = make_server(self.host, self.port, app, server_cls, handler_cls)
        self.srv = srv ### THIS IS THE ONLY CHANGE TO THE ORIGINAL CLASS METHOD!
        srv.serve_forever()

    def shutdown(self): ### ADD SHUTDOWN METHOD.
        self.srv.shutdown()
        # self.server.server_close()
