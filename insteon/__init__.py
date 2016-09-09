# -*- coding:utf-8 -*-
from .core import Insteon_Core

__all__ = ['Insteon']

core = Insteon_Core()
core.start_rest_server()

while 1:
    core.loop_once()
