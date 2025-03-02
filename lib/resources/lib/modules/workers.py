# -*- coding: utf-8 -*-
'''
 ***********************************************************
 * The Crew Add-on
 *
 * rewritten by cm 2024/12/20
 *
 * @file workers.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2024, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import threading
class Thread(threading.Thread):
    def __init__(self, target_func, *func_args) -> None:
        super().__init__(target=target_func, args=func_args)
