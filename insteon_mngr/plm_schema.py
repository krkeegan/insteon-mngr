'''
This schema defines all of the possible messages which can be received or
sent to the PLM.  The format of the schema is as follows, items in <>
must be defined

{
    '<the plm byte prefix without 0x02>' : {
        'rcvd_len' : tuple - first value is standard message length,
                             second value is extended message length
        'name' : string - string suitable for use as a variable
        'ack_act' : function (obj, msg)
                        obj = is the plm object that received the message
                        msg = the message object
                        This function is the received action that should be
                        performed on the arrival of a message
        'nack_act' : function (obj, msg)
                        obj = is the plm object that received the message
                        msg = the message object
                        This function is the nack action that should be
                        performed on the arrival of a nack response
        'bad_cmd_act' : function (obj, msg)
                        obj = is the plm object that received the message
                        msg = the message object
                        This function is the action that should be performed on
                        the arrival of a bad_cmd response
        'recv_act' : function (obj, msg)
                        obj = is the plm object that received the message
                        msg = the message object
                        This function is the action that should be performed on
                        the arrival of a msg without an ACK,NACK, or Bad_Cmd
        'recv_byte_pos' : {
            '<name>' : <int> - the name is a standardized description of the
                           byte. The int, is the position of the byte within
                           the bytearray
        }
    }
}

'''
PLM_SCHEMA = {
    0x50: {
        'rcvd_len': (11,),
        'send_len': (0,),
        'name': 'insteon_received',
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_insteon_msg(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'from_addr_hi': 2,
            'from_addr_mid': 3,
            'from_addr_low': 4,
            'to_addr_hi': 5,
            'to_addr_mid': 6,
            'to_addr_low': 7,
            'msg_flags': 8,
            'cmd_1': 9,
            'cmd_2': 10
        }
    },
    0x51: {
        'rcvd_len': (25,),
        'send_len': (0,),
        'name': 'insteon_ext_received',
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_insteon_msg(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'from_addr_hi': 2,
            'from_addr_mid': 3,
            'from_addr_low': 4,
            'to_addr_hi': 5,
            'to_addr_mid': 6,
            'to_addr_low': 7,
            'msg_flags': 8,
            'cmd_1': 9,
            'cmd_2': 10,
            'usr_1': 11,
            'usr_2': 12,
            'usr_3': 13,
            'usr_4': 14,
            'usr_5': 15,
            'usr_6': 16,
            'usr_7': 17,
            'usr_8': 18,
            'usr_9': 19,
            'usr_10': 20,
            'usr_11': 21,
            'usr_12': 22,
            'usr_13': 23,
            'usr_14': 24,
        }
    },
    0x52: {
        'rcvd_len': (4,),
        'send_len': (0,),
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_x10(msg),
        'name': 'x10_received',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'raw_x10': 2,
            'x10_flags': 3,
        }
    },
    0x53: {
        'rcvd_len': (10,),
        'send_len': (0,),
        'name': 'all_link_complete',
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_all_link_complete(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'link_code': 2,
            'group': 3,
            'from_addr_hi': 4,
            'from_addr_mid': 5,
            'from_addr_low': 6,
            'dev_cat': 7,
            'sub_cat': 8,
            'firmware': 9,
        }
    },
    0x54: {
        'rcvd_len': (3,),
        'send_len': (0,),
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_btn_event(msg),
        'name': 'plm_button_event',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'btn_event': 2,
        }
    },
    0x55: {
        'rcvd_len': (2,),
        'send_len': (0,),
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_plm_reset(msg),
        'name': 'user_plm_reset',
        'recv_byte_pos': {
            'plm_cmd': 1,
            # No other recv_byte_pos
        }
    },
    0x56: {
        'rcvd_len': (6,),
        'send_len': (0,),
        'name': 'all_link_clean_failed',
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_all_link_clean_failed(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'group': 2,
            'fail_addr_hi': 3,
            'fail_addr_mid': 4,
            'fail_addr_low': 5,
        }
    },
    0x57: {
        'rcvd_len': (10,),
        'send_len': (0,),
        'recv_act': lambda obj, msg: obj._rcvd_handler._rcvd_aldb_record(msg),
        'name': 'all_link_record',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'link_flags': 2,
            'group': 3,
            'dev_addr_hi': 4,
            'dev_addr_mid': 5,
            'dev_addr_low': 6,
            'data_1': 7,
            'data_2': 8,
            'data_3': 9,
        }
    },
    0x58: {
        'rcvd_len': (3,),
        'send_len': (0,),
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_all_link_clean_status(msg),
        'name': 'all_link_clean_status',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        }
    },
    0x59: {
        'rcvd_len': (12,),   # This appears in 2242-222 documentation, no details
        'send_len': (0,),   # as to how it works, or what it is
        'name': 'record_found',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'high_byte': 2,
            'low_byte': 3,
            'link_flags': 4,
            'group': 5,
            'dev_addr_hi': 6,
            'dev_addr_mid': 7,
            'dev_addr_low': 8,
            'data_1': 9,
            'data_2': 10,
            'data_3': 11
        },
        'send_byte_pos': {
        }
    },
    0x60: {
        'rcvd_len': (9,),
        'send_len': (2,),
        'name': 'plm_info',
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_plm_info(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_addr_hi': 2,
            'plm_addr_mid': 3,
            'plm_addr_low': 4,
            'dev_cat': 5,
            'sub_cat': 6,
            'firmware': 7,
            'plm_resp': 8
        },
        'send_byte_pos': {
            'plm_cmd': 1,
        }
    },
    0x61: {
        'rcvd_len': (6,),
        'send_len': (5,),
        'name': 'all_link_send',
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_prelim_plm_ack(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'group': 2,
            'cmd_1': 3,
            'cmd_2': 4,
            'plm_resp': 5
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'group': 2,
            'cmd_1': 3,
            'cmd_2': 4,
        }
    },
    0x62: {
        'rcvd_len': (9, 23),
        'send_len': (8, 22),
        'name': 'insteon_send',
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_plm_ack(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'to_addr_hi': 2,
            'to_addr_mid': 3,
            'to_addr_low': 4,
            'msg_flags': 5,
            'cmd_1': 6,
            'cmd_2': 7,
            'plm_resp': 8,
            'usr_1': 8,
            'usr_2': 9,
            'usr_3': 10,
            'usr_4': 11,
            'usr_5': 12,
            'usr_6': 13,
            'usr_7': 14,
            'usr_8': 15,
            'usr_9': 16,
            'usr_10': 17,
            'usr_11': 18,
            'usr_12': 19,
            'usr_13': 20,
            'usr_14': 21,
            'plm_resp_e': 22,
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'to_addr_hi': 2,
            'to_addr_mid': 3,
            'to_addr_low': 4,
            'msg_flags': 5,
            'cmd_1': 6,
            'cmd_2': 7,
            'usr_1': 8,
            'usr_2': 9,
            'usr_3': 10,
            'usr_4': 11,
            'usr_5': 12,
            'usr_6': 13,
            'usr_7': 14,
            'usr_8': 15,
            'usr_9': 16,
            'usr_10': 17,
            'usr_11': 18,
            'usr_12': 19,
            'usr_13': 20,
            'usr_14': 21,
        },
    },
    0x63: {
        'rcvd_len': (5,),
        'send_len': (4,),
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_plm_x10_ack(msg),
        'name': 'x10_send',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'raw_x10': 2,
            'x10_flags': 3,
            'plm_resp': 4,
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'raw_x10': 2,
            'x10_flags': 3,
        }
    },
    0x64: {
        'rcvd_len': (5,),
        'send_len': (4,),
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_all_link_start(msg),
        'name': 'all_link_start',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'link_code': 2,
            'group': 3,
            'plm_resp': 4
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'link_code': 2,  # 0x00 Responder,
                             # 0x01 Controller,
                             # 0x03 Dynamic,
                             # 0xFF Delete
            'group': 3
        }
    },
    0x65: {
        'rcvd_len': (3,),
        'name': 'all_link_cancel',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        }
    },
    0x66: {
        'rcvd_len': (6,),
        'name': 'set_host_device_cat',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'dev_cat': 2,
            'sub_cat': 3,
            'firmware': 4,
            'plm_resp': 5
        }
    },
    0x67: {
        'rcvd_len': (3,),
        'name': 'plm_reset',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        }
    },
    0x68: {
        'rcvd_len': (4,),
        'name': 'set_insteon_ack_cmd2',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'cmd_2': 2,
            'plm_resp': 3,
        }
    },
    0x69: {
        'rcvd_len': (3,),
        'send_len': (2,),
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_prelim_plm_ack(msg),
        'nack_act': lambda obj, msg: obj._rcvd_handler._rcvd_end_of_aldb(msg),
        'name': 'all_link_first_rec',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        },
        'send_byte_pos': {
            'plm_cmd': 1,
        }
    },
    0x6A: {
        'rcvd_len': (3,),
        'send_len': (2,),
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_prelim_plm_ack(msg),
        'nack_act': lambda obj, msg: obj._rcvd_handler._rcvd_end_of_aldb(msg),
        'name': 'all_link_next_rec',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        },
        'send_byte_pos': {
            'plm_cmd': 1,
        }
    },
    0x6B: {
        'rcvd_len': (4,),
        'name': 'plm_set_config',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'conf_flags': 2,
            'plm_resp': 3
        }
    },
    0x6C: {
        'rcvd_len': (3,),
        'name': 'get_sender_all_link_rec',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        }
    },
    0x6D: {
        'rcvd_len': (3,),
        'name': 'plm_led_on',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        }
    },
    0x6E: {
        'rcvd_len': (3,),
        'name': 'plm_led_off',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2,
        }
    },
    0x6F: {
        'rcvd_len': (12,),
        'send_len': (11,),
        'name': 'all_link_manage_rec',
        'ack_act': lambda obj, msg: obj._rcvd_handler._rcvd_all_link_manage_ack(msg),
        'nack_act': lambda obj, msg: obj._rcvd_handler._rcvd_all_link_manage_nack(msg),
        'recv_byte_pos': {
            'plm_cmd': 1,
            'ctrl_code': 2,
            'link_flags': 3,
            'group': 4,
            'dev_addr_hi': 5,
            'dev_addr_mid': 6,
            'dev_addr_low': 7,
            'data_1': 8,
            'data_2': 9,
            'data_3': 10,
            'plm_resp': 11
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'ctrl_code': 2,
            # 0x00 Find first
            # 0x01 Find next
            # 0x20 Modify (matches on cont/resp, group,dev_id; not d1-3)
            # NAK if not match
            # 0x40 Add controller, (matching cont/resp, group,dev_id
            # must not exist)
            # 0x41 Add responder, (matching cont/resp, group,dev_id
            # must not exist)
            # 0x80 Delete (matches on cont/resp, group,dev_id; not d1-3)
            # NAK if no match
            'link_flags': 3,
            'group': 4,
            'dev_addr_hi': 5,
            'dev_addr_mid': 6,
            'dev_addr_low': 7,
            'data_1': 8,
            'data_2': 9,
            'data_3': 10
        }
    },
    0x70: {
        'rcvd_len': (4,),
        'name': 'insteon_nak',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'cmd_1': 2,
            'cmd_2': 3,
            'plm_resp': 4,
        }
    },
    0x71: {
        'rcvd_len': (4,),
        'name': 'insteon_ack',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'cmd_2': 2,
            'plm_resp': 3,
        }
    },
    0x72: {
        'rcvd_len': (5,),
        'name': 'rf_sleep',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'cmd_1': 2,
            'cmd_2': 3,
            'plm_resp': 4,
        }
    },
    0x73: {
        'rcvd_len': (6,),
        'send_len': (2,),
        'name': 'plm_get_config',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'conf_flags': 2,
            'spare_1': 3,
            'spare_2': 4,
            'plm_resp': 5
        },
        'send_byte_pos': {
            'plm_cmd': 1,
        }
    },
    0x74: {                         # 0x74-0x78 are found in the 2242-222
        'rcvd_len': (3,),           # developers guide
        'send_len': (2,),
        'name': 'cancel_cleanup',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2
        },
        'send_byte_pos': {
            'plm_cmd': 1
        }
    },
    0x75: {
        'rcvd_len': (4,),
        'send_len': (5,),
        'name': 'read_8_bytes',
        'recv_byte_pos': {    # a subsequent 0x59 msg will arrive after this
            'plm_cmd': 1,
            'high_byte': 2,
            'low_byte': 3,
            'plm_resp': 4
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'high_byte': 2,
            'low_byte': 3,
        }
    },
    0x76: {
        'rcvd_len': (13,),
        'send_len': (12,),
        'name': 'write_8_bytes',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'high_byte': 2,
            'low_byte': 3,
            'link_flags': 4,
            'group': 5,
            'dev_addr_hi': 6,
            'dev_addr_mid': 7,
            'dev_addr_low': 8,
            'data_1': 9,
            'data_2': 10,
            'data_3': 11,
            'plm_resp': 12
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'high_byte': 2,
            'low_byte': 3,
            'link_flags': 4,
            'group': 5,
            'dev_addr_hi': 6,
            'dev_addr_mid': 7,
            'dev_addr_low': 8,
            'data_1': 9,
            'data_2': 10,
            'data_3': 11,
        }
    },
    0x77: {
        'rcvd_len': (4,),
        'send_len': (3,),
        'name': 'beep',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'plm_resp': 2
        },
        'send_byte_pos': {
            'plm_cmd': 1
        }
    },
    0x78: {
        'rcvd_len': (4,),
        'send_len': (3,),
        'name': 'set_status',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'status': 2,
            'plm_resp': 3
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'satus': 2
        }
    },
    0x79: {                     # 0x79-0x7C were added from the 2242-222
        'rcvd_len': (6,),       # developers guide.  They are listed as RF Modem
        'send_len': (5,),       # only commands
        'name': 'set_link_data_next_link',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'data_1': 2,
            'data_2': 3,
            'data_3': 4,
            'plm_resp': 5
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'data_1': 2,
            'data_2': 3,
            'data_3': 4
        }
    },
    0x7A: {
        'rcvd_len': (4,),
        'send_len': (3,),
        'name': 'set_retries_new_links',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'retries': 2,
            'plm_resp': 3
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'retries': 2,
        }
    },
    0x7B: {
        'rcvd_len': (4,),
        'send_len': (3,),
        'name': 'set_rf_freq_offset',
        'recv_byte_pos': {
            'plm_cmd': 1,
            'offset': 2,
            'plm_resp': 3
        },
        'send_byte_pos': {
            'plm_cmd': 1, # Increase from least offset 0x00 up to most 0x7F
            'offset': 2,  # Decrease from least offset 0xFF down to 0x8F
        }
    },
    0x7C: {
        'rcvd_len': (4,),    # It is unclear from the documentation how many
        'send_len': (3,),    # bytes the ack is, listed as XXXXXXXXXXXXXXXX
        'name': 'set_ack_for_templinc',  # So maybe 8 bytes?? Maybe 1??
        'recv_byte_pos': {
            'plm_cmd': 1,
            'ack': 2,
            'plm_resp': 3
        },
        'send_byte_pos': {
            'plm_cmd': 1,
            'ack': 2,
        }
    },
    0x7F: {
        'rcvd_len': (4,),
        'name': 'unknown',  # This command is seen in the incomiming buffer
        'recv_byte_pos': {  # of the 2242-222 every few minutes.  I assume
            'plm_cmd': 1,   # it is some sort of keep-alive initiated by
            'unk_1': 2,     # the hub itself or the rest API??  It is not
            'plm_resp': 3   # documented anywhere I can find
        }
    }
}
