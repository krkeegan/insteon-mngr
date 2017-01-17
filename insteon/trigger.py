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

    def match_msg(self, msg):
        if msg.allow_trigger:
            haystack = msg.parsed_attributes
            if msg.insteon_msg:
                haystack['insteon_msg_type'] = msg.insteon_msg.message_type
            matched_keys = []
            for trigger_key, trigger in self._triggers.items():
                needle = trigger.attributes
                trigger_match = True
                for test_key, test_val in needle.items():
                    if ((test_key in haystack) and
                            (needle[test_key] != haystack[test_key])):
                        trigger_match = False
                        break
                if trigger_match:
                    matched_keys.append(trigger_key)
            for trigger_key in matched_keys:
                # Delete trigger before running, to allow reusing same trigger_key
                trigger = self._triggers[trigger_key]
                trigger_function = trigger.trigger_function
                del self._triggers[trigger_key]
                trigger_function()

    def run_trigger(self, msg, trigger_key):
        trigger = self._triggers[trigger_key]
        trigger.trigger_function()

    def delete_matching_attr(self, msg_name, attributes={}):
        pass


class Trigger(object):

    def __init__(self, attributes={}):
        '''Trigger functions will be called when a message matching all of the
        identified attributes is received the trigger is then deleted.
        insteon_msg_type is a special attribute'''
        self._msg_attributes = attributes
        self._trigger_function = lambda: None

    @property
    def trigger_function(self):
        """Contains a function to be called on a trigger"""
        return self._trigger_function

    @trigger_function.setter
    def trigger_function(self, function):
        self._trigger_function = function

    @property
    def attributes(self):
        return self._msg_attributes
