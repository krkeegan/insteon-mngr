import threading
import json
import re
import pkg_resources

from bottle import (route, run, Bottle, response, get, post, put, delete,
                    request, error, static_file, view, TEMPLATE_PATH,
                    WSGIRefServer, redirect)

from insteon_mngr import BYTE_TO_ID
from insteon_mngr.sequences import DeleteLinkPair

core = None

STATIC_PATH = pkg_resources.resource_filename(__name__, '/web/static')
ROOT_PATH = pkg_resources.resource_filename(__name__, '/web')

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
    # TODO this may be an issue, if both links exist the sequence will be started twice
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
    return static_file(path, root=STATIC_PATH)

@get('/modems/<:re:[A-Fa-f0-9]{6}/?>')
def modem_page():
    return static_file('modem.html', root=ROOT_PATH)

@get('/modems/<:re:[A-Fa-f0-9]{6}/groups/[0-9]{1,3}/?>')
def modem_group_page():
    return static_file('modem_group.html', root=ROOT_PATH)

@get('/modems/<modem_id:re:[A-Fa-f0-9]{6}>/devices/<device_id:re:[A-Fa-f0-9]{6}/?>')
def device_page(modem_id, device_id):
    group_number = core.get_device_by_addr(device_id).base_group_number
    redirect('/modems/' + modem_id + '/devices/' + device_id +'/groups/' + str(group_number))

@get('/modems/<:re:[A-Fa-f0-9]{6}/devices/[A-Fa-f0-9]{6}/groups/[0-9]{1,3}/?>')
def device_group_page():
    return static_file('device_group.html', root=ROOT_PATH)

@get('/')
def index_page():
    return static_file('index.html', root=ROOT_PATH)

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
    links = controller_group.get_relevant_links()
    ret['definedLinks'] = _user_link_output(controller_group)
    ret['undefinedLinks'] = {}
    ret['unknownLinks'] = {}
    ret['bad_links'] = {}
    if controller_group.group_number == controller_device.base_group_number:
        for link in controller_device.get_bad_links():
            ret['bad_links'].update(link.json())
    for link in links:
        if link.status() == 'undefined':
            ret['undefinedLinks'].update(link.json())
        elif link.status() == 'unknown':
            ret['unknownLinks'].update(link.json())
    return ret

def _bad_links_output(controller_device):
    ret = {}
    for link in controller_device.get_bad_links():
        link_parsed = link.parse_record()
        if (link_parsed['controller'] is True or
                controller_device == link.device):
            # Controller links are on this device
            # if not responder then this is an orphaned responder on this dev
            link_addr = controller_device.dev_addr_str
            link_key = link.key
            group_number = link_parsed['group']
        else:
            # Responder link on other device, no controller on this device
            link_addr = link.device.dev_addr_str
            link_key = link.key
            group_number = link_parsed['data_3']
        ret[link_addr + '-' + link_key] = {'device': link.device.dev_addr_str,
                                           'group_number': group_number}
    return ret

def _user_link_output(controller_group):
    ret = {}
    user_links = core.get_user_links_for_this_controller(controller_group)
    for link in user_links.values():
        ret.update(link.json())
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
    plms = core.get_all_modems()
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
