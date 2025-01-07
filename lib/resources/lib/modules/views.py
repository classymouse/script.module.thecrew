# -*- coding: utf-8 -*-

'''
 ***********************************************************
 * The Crew Add-on
 *
 *
 * @file views.py
 * @package script.module.thecrew
 *
 * @copyright (c) 2024, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''

import sqlite3 as database

from . import control
from .crewruntime import c


def add_view(content):
    try:
        skin = control.skin
        view_id = str(control.getCurrentViewId())
        record = (skin, content, view_id)
        control.makeFile(control.dataPath)
        with database.connect(control.viewsFile) as dbcon:
            dbcur = dbcon.cursor()
            dbcur.execute("""
                CREATE TABLE IF NOT EXISTS views (
                    skin TEXT,
                    view_type TEXT,
                    view_id TEXT,
                    UNIQUE(skin, view_type)
                );
            """)
            dbcur.execute("DELETE FROM views WHERE skin = ? AND view_type = ?", (skin, content))
            dbcur.execute("INSERT INTO views VALUES (?, ?, ?)", record)

        view_name = control.infoLabel('Container.Viewmode')
        skin_name = control.addon(skin).getAddonInfo('name')
        skin_icon = control.addon(skin).getAddonInfo('icon')

        control.infoDialog(view_name, heading=skin_name, sound=True, icon=skin_icon)
    except Exception as e:
        c.log(str(e))




def set_view(content, view_dict=None):
    """Set the view type for the given content type.

    Args:
        content (str): The type of content to set the view for.
        view_dict (dict, optional): A dictionary mapping skin names to view
            IDs. Defaults to None.

    Returns:
        bool: Whether the view was successfully set.
    """
    if control.condVisibility(f'Container.Content({content})'):
        try:
            skin = control.skin
            record = (skin, content)
            with database.connect(control.viewsFile) as dbconn:
                dbcur = dbconn.cursor()
                dbcur.execute('SELECT * FROM views WHERE skin = ? AND view_type = ?', record)
                view = dbcur.fetchone()[2]
                if view is None:
                    raise ValueError("View not found")
                return control.execute(f'Container.SetViewMode({view})')
        except KeyError:
            try:
                return control.execute(f'Container.SetViewMode({view_dict[skin]})')
            except KeyError:
                return
    control.sleep(100)
