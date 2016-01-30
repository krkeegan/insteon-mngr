class Trigger_Manager(object):

    def __init__(self, parent):
        self._parent = parent
        self._triggers = {}

    def add_trigger(self, trigger_name, trigger_obj):
        '''The trigger_name must be unique to each trigger_obj.  Using the same
        name will cause the prior trigger to be overwritten in the trigger
        manager'''
        self._triggers[trigger_name] = trigger_obj

    # TODO remove expired triggers?

    def test_triggers(self, msg):
        if msg.allow_trigger:
            matched_keys = []
            for trigger_key, trigger in self._triggers.items():
                trigger_match = trigger.match_msg(msg)
                if trigger_match:
                    matched_keys.append(trigger_key)
            for trigger_key in matched_keys:
                # Delete trigger before running, to allow reusing same
                # trigger_key
                trigger = self._triggers[trigger_key]
                trigger_function = trigger.trigger_function
                del self._triggers[trigger_key]
                trigger_function()

    def delete_matching_attr(self, msg_name, attributes={}):
        pass


class PLMTrigger(object):

    def __init__(self, plm=None, attributes=None):
        '''Trigger functions will be called when a message matching all of the
        identified attributes is received the trigger is then deleted.'''
        if attributes is not None:
            self._attributes = attributes
        self._trigger_function = lambda: None
        self._name = None
        self._plm = plm

    @property
    def trigger_function(self):
        """Contains a function to be called on a trigger"""
        return self._trigger_function

    @trigger_function.setter
    def trigger_function(self, function):
        self._trigger_function = function

    @property
    def attributes(self):
        return self._attributes

    def match_msg(self, msg):
        '''Returns true if message matches the attributes defined for the trigger
        else returns false'''
        haystack = msg.parsed_attributes
        needle = self.attributes
        trigger_match = True
        for test_key in needle.keys():
            if ((test_key in haystack) and
                    (needle[test_key] != haystack[test_key])):
                trigger_match = False
                break
        return trigger_match

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    def queue(self):
        self._plm.trigger_mngr.add_trigger(self.name, self)

class InsteonTrigger(PLMTrigger):
    def __init__(self, plm=None, device=None, command_name=None, attributes=None):
        # pylint: disable=W0231
        '''device if defined will set the dev_from address
        command_name if defined will set the msg_length, plm_cmd,
        msg_type, and cmd_1
        attributes will override any of the above'''
        self._attributes = {}
        self._plm = plm
        if device is not None:
            self._set_dev_from_addr(device)
            self._plm = device.plm
        if command_name is not None:
            self._set_cmd(device, command_name)
        if attributes is not None:
            self._attributes.update(attributes)
        self._trigger_function = lambda: None

    def _set_dev_from_addr(self, device):
        self._attributes['from_addr_hi'] = device.dev_addr_hi
        self._attributes['from_addr_mid'] = device.dev_addr_mid
        self._attributes['from_addr_low'] = device.dev_addr_low

    def _set_cmd(self, device, command_name):
        # I think we expect all of these to be direct_ack??
        self._attributes['msg_type'] = 'direct_ack'
        try:
            cmd_schema = device.send_handler.msg_schema[command_name]
        except KeyError:
            print('command', command_name,
                  'not found for this device. Run DevCat?')
        else:
            self._attributes['cmd_1'] = cmd_schema['cmd_1']['default']
            self._attributes['msg_length'] = cmd_schema['msg_length']
            self._attributes['plm_cmd'] = 0x50
            if cmd_schema['msg_length'] == 'extended':
                self._attributes['plm_cmd'] = 0x51

    def match_msg(self, msg):
        '''Returns true if message matches the attributes defined for the trigger
        else returns false'''
        trigger_match = True
        if not msg.insteon_msg:
            trigger_match = False
        else:
            haystack = msg.parsed_attributes
            haystack['msg_type'] = msg.insteon_msg.message_type
            haystack['msg_length'] = msg.insteon_msg.msg_length
            needle = self.attributes
            for test_key in needle.keys():
                if ((test_key in haystack) and
                        (needle[test_key] != haystack[test_key])):
                    trigger_match = False
                    break
        return trigger_match
