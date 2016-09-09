import threading
import pprint
import json
import re
import os

from bottle import route, run, Bottle, response, get, post, request, error, static_file, view, TEMPLATE_PATH

core = ''
app = Bottle()

TEMPLATE_PATH.append(os.path.dirname(os.path.realpath(__file__))+ '/views')

print(TEMPLATE_PATH)

def start(passed_core):
    global core
    core = passed_core
    threading.Thread(target=run, kwargs=dict(
        host='localhost', port=8080, debug=True)).start()

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
