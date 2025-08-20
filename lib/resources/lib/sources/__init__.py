# -*- coding: utf-8 -*-

'''
********************************************************cm*
* The Crewy Add-on
*
* @file __init__.py
* @package script.module.thecrew
*
* @copyright (c) 2025, The Crew
* @license GNU General Public License, version 3 (GPL-3.0)
*
********************************************************cm*
'''

import pkgutil
import os.path

from ..modules.crewruntime import c

__all__ = [x[1] for x in os.walk(os.path.dirname(__file__))][0]


def sources():
    try:
        sourceDict = []
        for i in __all__:
            for loader, module_name, is_pkg in pkgutil.walk_packages([os.path.join(os.path.dirname(__file__), i)]):
                if is_pkg:
                    continue

                try:
                    module = loader.find_spec(module_name).loader.load_module(module_name)
                    sourceDict.append((module_name, module.source()))
                except AttributeError:
                    module = loader.find_spec(module_name).loader.load_module(module_name)
                except (ImportError, AttributeError) as e:
                    c.log(f'Could not load "{module_name}": {e}', 1)
                    pass

        return sourceDict
    except (ImportError, ModuleNotFoundError) as e:
        c.log(f'Could not load sources: {e}', 1)
        return []


def getAllHosters():
    def _sources(sourceFolder, appendList):
        sourceFolderLocation = os.path.join(os.path.dirname(__file__), sourceFolder)
        sourceSubFolders = [x[1] for x in os.walk(sourceFolderLocation)][0]
        for i in sourceSubFolders:
            for loader, module_name, is_pkg in pkgutil.walk_packages([os.path.join(sourceFolderLocation, i)]):
                if is_pkg:
                    continue
                try:
                    mn = str(module_name).split('_')[0]
                except:
                    mn = str(module_name)
                appendList.append(mn)
    sourceSubFolders = [x[1] for x in os.walk(os.path.dirname(__file__))][0]
    appendList = []
    for item in sourceSubFolders:
        if item != 'modules':
            _sources(item, appendList)
    return list(set(appendList))
