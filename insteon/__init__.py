# -*- coding:utf-8 -*-
from .core import Insteon_Core
# import threading
# from .config_server import start, stop

__all__ = ['Insteon']

# def core_loop():
#     core = Insteon_Core()
#     core.loop_once()
#     server = start(core)
#     while threading.main_thread().is_alive():
#         core.loop_once()
#     stop(server)
#
# threading.Thread(target=core_loop).start()
