import threading
import json
import re

from bottle import (route, run, Bottle, response, get, post, put, delete,
                    request, error, static_file, view, TEMPLATE_PATH,
                    WSGIRefServer, redirect)

from insteon import BYTE_TO_ID
from insteon.sequences import DeleteLinkPair

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
# patch
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
    return jsonify(json_links(device_id, int(group_number)))

# patch
@route('/modems/<modem_id:re:[A-Fa-f0-9]{6}>/groups.json', method='PATCH')
def api_modem_group_put(modem_id):
    modem = core.get_device_by_addr(modem_id)
    for group_number in request.json.keys():
        group = modem.get_object_by_group_num(int(group_number))
        update_device_attributes(group, request.json[group_number])
    return jsonify(json_core())

@post('/modems/<modem_id:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>.json')
def add_device(modem_id, device_id):
    modem = core.get_device_by_addr(modem_id)
    modem.add_device(device_id)
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_core())

@delete('/modems/<modem_id:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>.json')
def _delete_device(modem_id, device_id):
    modem = core.get_device_by_addr(modem_id)
    modem.delete_device(device_id)
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_core())

@post('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks.json')
@post('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks.json')
def add_defined_device_link(device_id, group_number):
    root = core.get_device_by_addr(device_id)
    controller_group = root.get_object_by_group_num(int(group_number))
    # Be careful, no documentation guarantees that data_3 is always the group
    responder_id = request.json['responder_id']
    responder_device = core.get_device_by_addr(responder_id)
    responder_device.add_user_link(controller_group, request.json, None)
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, int(group_number)))

# patch
@route('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks/<uid:re:[0-9]{6}>.json', method='PATCH')
@route('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks/<uid:re:[0-9]{6}>.json', method='PATCH')
def edit_defined_device_link(device_id, group_number, uid):
    controller_root = core.get_device_by_addr(device_id)
    controller = controller_root.get_object_by_group_num(int(group_number))
    user_link = core.find_user_link(int(uid))
    if user_link is not None:
        user_link.edit(controller, request.json)
    else:
        print('expired definedLink uid, try refreshing page')
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, int(group_number)))

@delete('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks/<uid:re:[0-9]{6}>.json')
@delete('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/definedLinks/<uid:re:[0-9]{6}>.json')
def delete_defined_device_link(device_id, group_number, uid):
    user_link = core.find_user_link(int(uid))
    user_link.delete()
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, int(group_number)))

@delete('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/unknownLinks/<key:re:[A-Fa-f0-9]{4}>.json')
@delete('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/unknownLinks/<key:re:[A-Fa-f0-9]{4}>.json')
def delete_unknown_link(device_id, group_number, key):
    device_root = core.get_device_by_addr(device_id)
    aldb_record = device_root.aldb.get_record(key)
    aldb_record.delete()
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, int(group_number)))

@delete('/modems/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/undefinedLinks/<responder_id:re:[A-Fa-f0-9]{6}><responder_key:re:[A-Fa-f0-9\-]{4}><controller_key:re:[A-Fa-f0-9\-]{4}>.json')
@delete('/modems/<:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}>/groups/<group_number:re:[0-9]{1,3}>/links/undefinedLinks/<responder_id:re:[A-Fa-f0-9]{6}><responder_key:re:[A-Fa-f0-9\-]{4}><controller_key:re:[A-Fa-f0-9\-]{4}>.json')
def delete_undefined_device_link(device_id, group_number, responder_id,
                                 responder_key, controller_key):
    device_root = core.get_device_by_addr(device_id)
    device_group = device_root.get_object_by_group_num(int(group_number))
    delete_sequence = DeleteLinkPair()
    if controller_key != '----':
        controller_device = core.get_device_by_addr(device_id)
        delete_sequence.set_controller_device_with_key(controller_device,
                                                       controller_key)
        link = controller_device.aldb.get_record(controller_key)
        link.link_sequence = delete_sequence
        delete_sequence.start()
    if responder_key != '----':
        responder_device = core.get_device_by_addr(responder_id)
        delete_sequence.set_responder_device_with_key(responder_device,
                                                      responder_key)
        link = responder_device.aldb.get_record(responder_key)
        link.link_sequence = delete_sequence
        delete_sequence.start()
    response.headers['Content-Type'] = 'application/json'
    return jsonify(json_links(device_id, int(group_number)))

# patch
@route('/modems/<:re:[A-Fa-f0-9]{6}>/devices.json', method='PATCH')
def api_device_put():
    for device_id in request.json.keys():
        device = core.get_device_by_addr(device_id)
        update_device_attributes(device, request.json[device_id])
    return jsonify(json_core())

# patch
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
    group_number = core.get_device_by_addr(device_id).base_group_number
    redirect('/modems/' + modem_id + '/devices/' + device_id +'/groups/' + str(group_number))

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
            for group in device.get_all_groups():
                ret[modem.dev_addr_str]['devices'][device.dev_addr_str]['groups'][group.group_number] = \
                    group.get_features_and_attributes()
        ret[modem.dev_addr_str]['groups'] = {}
        for group in modem.get_all_groups():
            ret[modem.dev_addr_str]['groups'][group.group_number] = \
                group.get_features_and_attributes()
    return ret

def json_links(device_id, group_number):
    ret = {}
    controller_device = core.get_device_by_addr(device_id)
    controller_group = controller_device.get_object_by_group_num(group_number)
    ret['definedLinks'] = _user_link_output(controller_group)
    ret['undefinedLinks'] = _undefined_link_output(controller_group)
    ret['unknownLinks'] = _unknown_link_output(controller_group)
    return ret

def _unknown_link_output(device):
    ret = {}
    for link in device.get_unknown_device_links():
        link_parsed = link.parse_record()
        link_addr = BYTE_TO_ID(link_parsed['dev_addr_hi'],
                               link_parsed['dev_addr_mid'],
                               link_parsed['dev_addr_low'])
        status = None
        if link.link_sequence is not None:
            if link.link_sequence.is_complete is False:
                status = 'Working'
            elif link.link_sequence.is_success is False:
                status = 'Failed'
        ret[link.key] = {'device': link_addr,
                         'status': status}
    return ret

def _undefined_link_output(controller_group):
    # Three classes of undefined links can exist
    # TODO need to add status items to this
    ret = {}
    for link in controller_group.get_undefined_links():
        link_parsed = link.parse_record()
        link_addr = BYTE_TO_ID(link_parsed['dev_addr_hi'],
                               link_parsed['dev_addr_mid'],
                               link_parsed['dev_addr_low'])
        if link_parsed['controller'] is True:
            responder_records = link.get_reciprocal_records()
            for responder in responder_records:
                responder_parsed = responder.parse_record()
                # Class 1 - controller with reciproal responders links
                responder_group = responder.device.get_object_by_group_num(
                    responder_parsed['data_3'])
                # TODO this will cause an error if the group doesn't exist
                ret[link_addr + responder.key + link.key] = {
                    'responder_id': link_addr,
                    'responder_name': responder_group.name,
                    'data_1': responder_parsed['data_1'],
                    'data_2': responder_parsed['data_2'],
                    'data_3': responder_parsed['data_3'],
                    'responder_key': responder.key,
                    'controller_key': link.key
                }
            if len(responder_records) == 0:
                # Class 2 - controller with no responder links
                responder_device = core.get_device_by_addr(link_addr)
                responder_group = responder_device.get_object_by_group_num(
                    responder_device.base_group_number
                )
                ret[link_addr + '----' + link.key] = {
                    'responder_id': link_addr,
                    'responder_name': responder_group.name,
                    'data_1': 0x00,
                    'data_2': 0x00,
                    'data_3': 0x00,
                    'responder_key': None,
                    'controller_key': link.key
                }
        else:
            # Class 3 - responder links with no controller link on this device
            ret[link.device.root.dev_addr_str + link.key + '----'] = {
                'responder_id': link.device.root.dev_addr_str,
                'responder_name': link.device.name,
                'data_1': link_parsed['data_1'],
                'data_2': link_parsed['data_2'],
                'data_3': link_parsed['data_3'],
                'responder_key': link.key,
                'controller_key': None
            }
    return ret

def _user_link_output(controller_group):
    ret = {}
    user_links = core.get_user_links_for_this_controller(controller_group)
    for link in user_links.values():
        status = 'Broken'
        if link.are_aldb_records_correct() is True:
            status = 'Good'
        elif link.link_sequence is not None:
            if link.link_sequence.is_complete is False:
                status = 'Working'
            elif link.link_sequence.is_success is False:
                status = 'Failed'
        ret[link.uid] = {
            'responder_id': link.responder_device.dev_addr_str,
            'responder_name': link.responder_group.name,
            'responder_group': link.data_3,
            'responder_key': link.responder_key,
            'controller_key': link.controller_key,
            'data_1': link.data_1,
            'data_2': link.data_2,
            'data_3': link.data_3,
            'status': status
        }
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
