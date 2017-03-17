import threading
import json
import re
import os

from bottle import (route, run, Bottle, response, get, post, put, delete,
                    request, error, static_file, view, TEMPLATE_PATH,
                    WSGIRefServer)

from insteon.base_objects import BYTE_TO_ID

core = ''

TEMPLATE_PATH.append(os.path.dirname(os.path.realpath(__file__))+ '/views')

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
    return dict(device_id=DevID,
                attributes=get_modem(DevID),
                groups=list_groups(DevID),
                devices=list_devices(DevID)
               )

@post('/modem/<DevID>')
@view('modem')
def modem_settings(DevID):
    modem = core.get_device_by_addr(DevID)
    modem.name = request.forms.get('name')
    return modem_page(DevID)

@route('/modem/<DevID>/group/<group_number>')
@view('modem_group')
def modem_group_page(DevID, group_number):
    return dict(modem_id = DevID,
                group_number = group_number,
                attributes = get_modem_group(DevID, group_number)
               )

@post('/modem/<DevID>/group/<group_number>')
@view('modem_group')
def modem_group_settings(DevID, group_number):
    modem = core.get_device_by_addr(DevID)
    group = modem.get_object_by_group_num(int(group_number))
    group.name = request.forms.get('name')
    return modem_group_page(DevID, group_number)

@post('/modem/<modem_id>/device/<DevID>')
@view('device')
def device_settings(modem_id, DevID):
    modem = core.get_device_by_addr(modem_id)
    device = modem.get_device_by_addr(DevID)
    device.name = request.forms.get('name')
    return device_page(modem_id, DevID)

@route('/modem/<modem_id>/device/<DevID>')
@view('device')
def device_page(modem_id, DevID):
    return dict(modem_id = modem_id,
                device_id = DevID,
                attributes = get_device(modem_id, DevID)
               )

@route('/modem/<modem_id>/device/<DevID>/group/<group_number>')
@view('device_group')
def device_group_page(modem_id, DevID, group_number):
    return dict(modem_id = modem_id,
                device_id = DevID,
                group_number = group_number,
                attributes = get_device_group(modem_id, DevID, group_number)
               )

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
def error_405(error_parm):
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
        ret.append({modem.dev_addr_str : {
            'dev_cat': modem.dev_cat,
            'sub_cat': modem.sub_cat,
            'firmware': modem.firmware,
            'port': modem.port,
            'port_active': modem.port_active,
            'type': modem.type,
            'name': modem.name
        }}
                  )
    return ret

def list_groups(DevID):
    device = core.get_device_by_addr(DevID)
    groups = device.get_all_groups()
    groups_sort = {}
    for group in groups:
        groups_sort[group.group_number] = group
    ret = []
    for group_number in sorted(groups_sort):
        ret.append(
            {group_number : {
                'group_name': groups_sort[group_number].name
            }}
        )
    return ret

def list_devices(Modem):
    modem = core.get_device_by_addr(Modem)
    devices = modem.get_all_devices()
    ret = []
    for device in devices:
        ret.append(
            {device.dev_addr_str : {
                'device_name': device.name
            }}
        )
    return ret

def get_modem(DevID):
    modem = core.get_modem_by_id(DevID)
    ret = {
        'dev_cat': modem.dev_cat,
        'sub_cat': modem.sub_cat,
        'firmware': modem.firmware,
        'port_active': modem.port_active,
        'type': modem.type,
        'dev_addr_str': modem.dev_addr_str,
        'name': modem.name
    }
    if modem.type == 'hub':
        ret['user'] = modem.user
        ret['password'] = modem.password
        ret['ip'] = modem.ip
        ret['port'] = modem.tcp_port
    else:
        ret['port'] = modem.port
    return ret

def get_modem_group(DevID, group_number):
    modem = core.get_modem_by_id(DevID)
    group = modem.get_object_by_group_num(int(group_number))
    ret = get_links(DevID, group_number)
    ret.update({
        'name': group.name,
        'modem_name': modem.name,
    })
    return ret

def get_device_group(modem_id, DevID, group_number):
    modem = core.get_modem_by_id(modem_id)
    device = modem.get_device_by_addr(DevID)
    group = device.get_object_by_group_num(int(group_number))
    ret = get_links(DevID, group_number)
    ret.update({
        'name': group.name,
        'modem_name': modem.name,
        'dev_addr_str': device.dev_addr_str,
        'device_name': device.name,
        'group_name': group.name
    })
    return ret

def get_links(DevID, group_number):
    ret = {}
    root = core.get_device_by_addr(DevID)
    device = root.get_object_by_group_num(int(group_number))
    user_links = core.get_matching_user_links(device)
    ret['defined_links'] = user_link_output(user_links)
    undefined_controller = get_undefined_controller(root, group_number, user_links)
    undefined_responder = get_undefined_responder(root, group_number, user_links)
    ret['undefined_links'] = undefined_link_output(undefined_controller)
    ret['undefined_links'].extend(undefined_link_output(undefined_responder))
    # TODO add Responder links on other devices
    # TODO Finally need a section to deal with responder links where the
    # is not a device we know controller
    return ret

def undefined_link_output(links):
    ret = []
    for link in links:
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
                    'on_level': responder_parsed['data_1'],
                    'status': responder_parsed['data_2']
                })
        else:
            ret.append({
                'responder': link.device.dev_addr_str,
                'on_level': link_parsed['data_1'],
                'status': link_parsed['data_2']
            })
    return ret

def get_undefined_responder(root, group_number, user_links):
    ret = []
    attributes = {
        'responder': True,
        'group': int(group_number),
        'dev_addr_hi': root.dev_addr_hi,
        'dev_addr_mid': root.dev_addr_mid,
        'dev_addr_low': root.dev_addr_low
    }
    aldb_responder_links = core.get_matching_aldb_records(attributes)
    for aldb_link in aldb_responder_links:
        found = False
        if len(aldb_link.get_reciprocal_records()) > 0:
            # A responder link exists on the device, this will be listed
            # in the undefined controller function
            continue
        for user_link in user_links:
            if user_link.matches_aldb(aldb_link):
                found = True
                break
        if found is False:
            ret.append(aldb_link)
    return ret

def get_undefined_controller(root, group_number, user_links):
    ret = []
    attributes = {
        'controller': True,
        'group': int(group_number)
    }
    aldb_controller_links = root.aldb.get_matching_records(attributes)
    for aldb_link in aldb_controller_links:
        found = False
        for user_link in user_links:
            if user_link.matches_aldb(aldb_link):
                found = True
                break
        if found is False:
            ret.append(aldb_link)
    return ret

def user_link_output(user_links):
    ret = []
    for link in user_links:
        ret.append({
            'responder': link._device.dev_addr_str,
            'on_level': link._data_1,
            'status': link._data_2
        })
    return ret

def get_device(modem_id, DevID):
    modem = core.get_modem_by_id(modem_id)
    device = modem.get_device_by_addr(DevID)
    ret = {
        'dev_cat': device.dev_cat,
        'sub_cat': device.sub_cat,
        'firmware': device.firmware,
        'dev_addr_str': device.dev_addr_str,
        'name': device.name,
        'modem_name': modem.name
    }
    return ret

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
