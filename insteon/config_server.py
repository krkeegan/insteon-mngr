import threading
import json
import re

from bottle import (route, run, Bottle, response, get, post, put, delete,
                    request, error, static_file, view, TEMPLATE_PATH,
                    WSGIRefServer, redirect)

from insteon.base_objects import BYTE_TO_ID

core = ''

def start(passed_core):
    global core      # pylint: disable=W0603
    core = passed_core
    server = MyServer(host='0.0.0.0', port=8080, debug=True)
    threading.Thread(target=run, kwargs=dict(server=server)).start()
    return server

def stop(server):
    server.shutdown()

###################################################################
##
# API Responses
##
###################################################################

# Bottle 0.12 doesn't have a patch decorator
@route('/modems.json', method='PATCH')
def api_modem_put():
    for modem_id in request.json.keys():
        modem = core.get_device_by_addr(modem_id)
        update_device_attributes(modem, request.json[modem_id])
    return jsonify(json_core())

@get('/modems.json')
def api():
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_core())

@get('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links.json')
@get('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links.json')
def modem_links(device_id, group_number):
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, group_number))

@route('/modems/<modem_id:re:[A-Fa-f0-9]{6}>/groups.json', method='PATCH')
def api_modem_group_put(modem_id):
    modem = core.get_device_by_addr(modem_id)
    for group_number in request.json.keys():
        group = modem.get_object_by_group_num(int(group_number))
        update_device_attributes(group, request.json[group_number])
    return jsonify(json_core())

@post('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks.json')
@post('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks.json')
def add_defined_device_link(device_id, group_number):
    root = core.get_device_by_addr(device_id)
    controller_device = root.get_object_by_group_num(int(group_number))
    # Be careful, no documentation guarantees that data_3 is always the group
    responder_id = request.json['address']
    responder_group = int(request.json['data_3'])
    responder_root = core.get_device_by_addr(responder_id)
    responder = responder_root.get_object_by_group_num(int(responder_group))
    responder.add_user_link(controller_device, request.json)
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, group_number))

@route('/modems/<:re:[A-Fa-f0-9]{6}>/devices.json', method='PATCH')
def api_device_put():
    for device_id in request.json.keys():
        device = core.get_device_by_addr(device_id)
        update_device_attributes(device, request.json[device_id])
    return jsonify(json_core())

@route('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups.json', method='PATCH')
def api_device_group_put(device_id):
    for group_number in request.json.keys():
        device = core.get_device_by_addr(device_id)
        group = device.get_object_by_group_num(int(group_number))
        update_device_attributes(group, request.json[group_number])
    return jsonify(json_core())

###################################################################
##
# HTML Responses
##
###################################################################

@get('/static/<path:path>')
def callback(path):
    return static_file(path, root='insteon/web/static')

@get('/modems/<:re:[A-Fa-f0-9]{6}/?>')
def modem_page():
    return static_file('modem.html', root='insteon/web')

@get('/modems/<:re:[A-Fa-f0-9]{6}/groups/[0-9]{1,3}/?>')
def modem_group_page():
    return static_file('modem_group.html', root='insteon/web')

@get('/modems/<modem_id:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}/?>')
def device_page(modem_id, device_id):
    redirect('/modems/' + modem_id + '/devices/' + device_id +'/groups/1')

@get('/modems/<:re:[A-Fa-f0-9]{6}/devices/[A-Fa-f0-9]{6}/groups/[0-9]{1,3}/?>')
def device_group_page():
    return static_file('device_group.html', root='insteon/web')

@get('/')
def index_page():
    return static_file('index.html', root='insteon/web')

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
def error_405(error_parm):
    return jsonify(generate_error(405, 'Method not allowed.'))

###################################################################
##
# Data Generating Functions
##
###################################################################

def json_core():
    ret = {}
    modems = core.get_all_modems()
    for modem in modems:
        ret[modem.dev_addr_str] = modem.get_features_and_attributes()
        ret[modem.dev_addr_str]['devices'] = {}
        for device in modem.get_all_devices():
            ret[modem.dev_addr_str]['devices'][device.dev_addr_str] = \
                device.get_features_and_attributes()
            ret[modem.dev_addr_str]['devices'][device.dev_addr_str]['groups'] = {}
            for group in [device] + device.get_all_groups():
                ret[modem.dev_addr_str]['devices'][device.dev_addr_str]['groups'][group.group_number] = \
                    group.get_features_and_attributes()
        ret[modem.dev_addr_str]['groups'] = {}
        for group in modem.get_all_groups():
            ret[modem.dev_addr_str]['groups'][group.group_number] = \
                group.get_features_and_attributes()
    return ret

def json_links(device_id, group_number):
    ret = {}
    root = core.get_device_by_addr(device_id)
    device = root.get_object_by_group_num(int(group_number))
    ret['definedLinks'] = _user_link_output(device)
    ret['undefinedLinks'] = _undefined_link_output(device)
    ret['unknownLinks'] = _unknown_link_output(device)
    return ret

def _unknown_link_output(device):
    ret = []
    for link in device.get_unknown_device_links():
        link_parsed = link.parse_record()
        link_addr = BYTE_TO_ID(link_parsed['dev_addr_hi'],
                               link_parsed['dev_addr_mid'],
                               link_parsed['dev_addr_low'])
        ret.append({'device': link_addr})
    return ret

def _undefined_link_output(device):
    ret = []
    for link in device.get_undefined_links():
        link_parsed = link.parse_record()
        link_addr = BYTE_TO_ID(link_parsed['dev_addr_hi'],
                               link_parsed['dev_addr_mid'],
                               link_parsed['dev_addr_low'])
        # TODO what do we do here if no responder link exists?
        # Set to some default data_1 and data_2
        if link_parsed['controller'] is True:
            for responder in link.get_reciprocal_records():
                responder_parsed = responder.parse_record()
                ret.append({
                    'responder': link_addr,
                    'responder_name': responder.device.name,
                    'data_1': responder_parsed['data_1'],
                    'data_2': responder_parsed['data_2'],
                    'data_3': responder_parsed['data_3']
                })
        else:
            ret.append({
                'responder_id': link.device.root.dev_addr_str,
                'responder_name': link.device.name,
                'data_1': link_parsed['data_1'],
                'data_2': link_parsed['data_2'],
                'data_3': link_parsed['data_3']
            })
    return ret

def _user_link_output(device):
    ret = []
    user_links = core.get_user_links_for_this_controller(device)
    for link in user_links:
        status = 'Broken'
        if link.aldb_records_exist() is True:
            status = 'Good'
        ret.append({
            'responder_id': link.device.root.dev_addr_str,
            'responder_name': link.device.name,
            'responder_group': link.device.group_number,
            'data_1': link.data_1,
            'data_2': link.data_2,
            'data_3': link.data_3,
            'status': status
        })
    return ret

###################################################################
##
# Data Storing Functions
##
###################################################################

def update_device_attributes(device, attributes):
    for key, value in attributes.items():
        device.attribute(key, value)

###################################################################
##
# Helper Functions
##
###################################################################

def generate_error(code, text):
    ret = {
        "error": {
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
    def run(self, app_parm): # pragma: no cover
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
        from wsgiref.simple_server import make_server
        import socket
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw):
                    pass
            self.options['handler_class'] = QuietHandler

        class FixedHandler(WSGIRequestHandler):
            def address_string(self): # Prevent reverse DNS lookups please.
                return self.client_address[0]

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', WSGIServer)

        if ':' in self.host: # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        srv = make_server(self.host, self.port, app_parm, server_cls, handler_cls)
        self.srv = srv ### THIS IS THE ONLY CHANGE TO THE ORIGINAL CLASS METHOD!
        srv.serve_forever()

    def shutdown(self): ### ADD SHUTDOWN METHOD.
        self.srv.shutdown()
        # self.server.server_close()
