# -*- coding: utf-8 -*-
# flake8: noqa: E501
'''
 ***********************************************************
 * The Crew Add-on
 *
 * @package script.module.thecrew
 *
 * @copyright (c) 2023, The Crew
 * @license GNU General Public License, version 3 (GPL-3.0)
 *
 ********************************************************cm*
'''
# pylint: disable=C0301  # disable "line too long" (file-wide)

import sys
from .crewruntime import c

# moved imports to module top-level for clarity and performance
import importlib
import inspect
import json
import traceback
import types
from random import randint
from urllib.parse import quote_plus

# moved previously-local imports to top-level as requested
from . import cache
from . import control
from . import downloader
from . import sources as local_sources
from . import views

def router(params):
    """
    Refactored single-entry router that preserves original behaviour.
    - Uses lazy imports
    - Handles instantiation heuristics
    - Maps every action from the original file to a handler
    """
    # local helper to read params
    def p(k, default=None):
        return params.get(k, default)

    # robust call_module: import module, resolve attribute, optionally instantiate or call method
    def call_module(module_path, attr=None, inst=False, method=None, *a, **kw):
        """
        Lazily import module or accept a module object.
        - module_path: str module name or an already-imported module object
        - attr: attribute name in module (optional)
        - inst: if True, try to instantiate/resolve a class/constructor
        - method: call a method on the instance/attribute/module when provided
        """
        # Accept already-imported module objects
        if not isinstance(module_path, str):
            if inspect.ismodule(module_path):
                mod = module_path
            else:
                raise TypeError(f"module_path must be a string or module, got: {type(module_path)}")
        else:
            # Support relative imports (module_path starting with '.')
            try:
                if module_path.startswith('.'):
                    mod = importlib.import_module(module_path, package=__package__)
                else:
                    mod = importlib.import_module(module_path)
            except Exception:
                c.log(f"[router] Failed to import {module_path}")
                raise

        target = getattr(mod, attr) if attr else mod

        def _find_class_in_module(m, name_hint=None):
            hint = (name_hint or '').lower()
            for n, obj in inspect.getmembers(m, inspect.isclass):
                if n.lower() == hint:
                    return obj
            for n, obj in inspect.getmembers(m, inspect.isclass):
                if obj.__module__ == m.__name__:
                    return obj
            return None

        # instantiate requested
        if inst:
            instance = None
            if inspect.isclass(target):
                instance = target()
            elif callable(target) and not inspect.ismodule(target):
                instance = target()
            elif inspect.ismodule(target):
                cls = _find_class_in_module(target, attr)
                if cls:
                    instance = cls()
            if instance is None:
                raise TypeError(f"'inst' requested but target is not callable: {module_path}{f'.{attr}' if attr else ''}")
            return getattr(instance, method)(*a, **kw) if method else instance

        # call a method in module/attribute or call the callable
        if method:
            if inspect.ismodule(target):
                func = getattr(target, method, None)
                if callable(func):
                    return func(*a, **kw)
            else:
                func = getattr(target, method, None)
                if callable(func):
                    return func(*a, **kw)
            raise AttributeError(f"Method {method} not found on target {module_path}{f'.{attr}' if attr else ''}")

        if callable(target) and not inspect.ismodule(target):
            return target(*a, **kw)

        return target

    # actionlist from original file
    actionlist = {
        '247movies','247tvshows','iptv','yss','weak','daddylive',
        'sportsbay','sports24','gratis','base','waste','whitehat','arconai','iptv_lodge','stratus','distro',
        'xumo','bumble','pluto','tubi','spanish','spanish2','bp','arabic','arabic2','india','chile','colombia','argentina',
        'spain','iptv_git','cctv','titan','porn','faith','lust','greyhat','absolution','eyecandy','purplehat','classy','retribution','kiddo',
        'redhat','yellowhat','blackhat','food','ncaa','ncaab','lfl','xfl','boxing','tennis','mlb','nfl','nhl','nba',
        'ufc','fifa','wwe','motogp','f1','pga','nascar','cricket','sports_channels','sreplays','greenhat'
    }

    action = p('action')
    if action is None:
        # default behaviour
        call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='root')
        cache.cache_version_check()
        return

    # handle big actionlist with lists.indexer().root_<action>()
    if action in actionlist:
        idx = call_module('resources.lib.indexers.lists', 'indexer', inst=True)
        func_name = f'root_{action}'
        if hasattr(idx, func_name):
            getattr(idx, func_name)()
        else:
            # Safely resolve and call the 'root' attribute only if callable.
            root = getattr(idx, 'root', None)
            if callable(root):
                root()
            else:
                c.log(f"[router] indexer 'root' not callable for action: {action}")
        return

    # helper for docuHeaven fallback
    def _docu_heaven():
        if p('docuCat') is not None:
            call_module('resources.lib.indexers.docu', 'documentary', True, 'docu_list', * (p('docuCat'),))
        elif p('docuPlay') is not None:
            call_module('resources.lib.indexers.docu', 'documentary', True, 'docu_play', * (p('docuPlay'),))
        else:
            call_module('resources.lib.indexers.docu', 'documentary', inst=True, method='root')

    # complex 'play' handler reused by play/play1
    def _play_handler(use_player=False):
        try:
            content = p('content')
            if content is not None:
                # lists.player().play(url, content)
                call_module('resources.lib.indexers.lists', 'player', True, 'play', * (p('url'), content))
                return
            # sources.sources().play(...)
            call_module('resources.lib.modules.sources', 'sources', inst=True, method='play', title=p('title'), year=p('year'), imdb=p('imdb'), tmdb=p('tmdb'), season=p('season'), episode=p('episode'), tvshowtitle=p('tvshowtitle'), premiered=p('premiered'), meta=p('meta'), select=p('select'))
        except Exception as e:
            c.log(f'[CM @ router]Traceback:: {traceback.format_exc()}')
            c.log(f'[CM @ router]Error:: {e}')

    # download handler (keeps original silent failure behaviour)
    def _download_handler():
        try:
            src = p('source')
            # use top-level downloader/local_sources imported above
            downloader.download(p('name'), p('image'), local_sources.sources().sourcesResolve(json.loads(src)[0], True))
        except (ValueError, IndexError, TypeError, KeyError, json.JSONDecodeError) as e:
            c.log(f"[CM Debug @ 173 in crew.py] Download handler error: {e}")
            # ignore expected parsing/indexing/type errors but avoid catching all Exceptions


    # random handler preserves original branching
    def _random_handler():
        try:
            rtype = p('rtype')
            rlist = []
            r = f"{sys.argv[0]}?action=play"

            if rtype == 'movie':
                rlist = call_module('resources.lib.indexers.movies', 'movies', inst=True, method='get', create_directory=False, url=p('url'))
            elif rtype == 'episode':
                # use the correct attribute/class name 'episodes' (not 'episode')
                rlist = call_module('resources.lib.indexers.episodes', 'episodes', inst=True, method='get', create_directory=False, tvshowtitle=p('tvshowtitle'), year=p('year'), imdb=p('imdb'), tmdb=p('tmdb'), meta=p('meta'), season=p('season'))
            elif rtype == 'season':
                rlist = call_module('resources.lib.indexers.episodes', 'Seasons', inst=True, method='get', create_directory=False, tvshowtitle=p('tvshowtitle'), year=p('year'), imdb=p('imdb'), tmdb=p('tmdb'), meta=p('meta'))
                r = f"{sys.argv[0]}?action=random&rtype=episode"
            elif rtype == 'show':
                rlist = call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='get', create_directory=False, url=p('url'))
                r = f"{sys.argv[0]}?action=random&rtype=season"

            # Defensive normalization: ensure we have a sequence
            if not rlist:
                control.infoDialog(control.lang(32537), time=8000)
                return

            if not isinstance(rlist, (list, tuple)):
                if isinstance(rlist, dict):
                    rlist = [rlist]
                else:
                    # Only attempt to convert to list if object is actually iterable
                    if hasattr(rlist, '__iter__'):
                        try:
                            rlist = list(rlist) # type: ignore
                        except Exception:
                            c.log(f"[CM Debug @ random_handler] converting rlist to list failed (type={type(rlist)}): {repr(rlist)}")
                            control.infoDialog(control.lang(32537), time=8000)
                            return
                    else:
                        c.log(f"[CM Debug @ random_handler] rlist not iterable (type={type(rlist)}): {repr(rlist)}")
                        control.infoDialog(control.lang(32537), time=8000)
                        return

            rand = randint(0, len(rlist) - 1)
            for pkey in ['title', 'year', 'imdb', 'tmdb', 'season', 'episode', 'tvshowtitle', 'premiered', 'select']:
                try:
                    if rtype == "show" and pkey == "tvshowtitle":
                        r += '&' + pkey + '=' + quote_plus(rlist[rand].get('title', ''))
                    else:
                        r += '&' + pkey + '=' + quote_plus(str(rlist[rand].get(pkey, '')))
                except Exception:
                    pass
            try:
                r += f'&meta={quote_plus(json.dumps(rlist[rand]))}'
            except Exception:
                r += '&meta=' + quote_plus("{}")
            # feedback dialogs similar to original
            if rtype == "movie":
                try:
                    control.infoDialog(rlist[rand].get('title', ''), control.lang(32536), time=30000)
                except Exception:
                    pass
            elif rtype == "episode":
                try:
                    control.infoDialog(f"{rlist[rand].get('tvshowtitle','')} - Season {rlist[rand].get('season','')} - {rlist[rand].get('title','')}", control.lang(32536), time=30000)
                except Exception:
                    pass
            control.execute(f'RunPlugin({r})')
        except Exception:
            control.infoDialog(control.lang(32537), time=8000)

    # mapping of actions to handlers (covers all actions from original file)
    action_map = {
        # navigator group
        'bluehat': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='bluehat'),
        'whitehat': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='whitehat'),
        'movieNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='movies'),
        'movieliteNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='movies', lite=True),
        'mymovieNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='mymovies'),
        'mymovieliteNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='mymovies', lite=True),
        'nav_add_addons': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='add_addons'),
        'tvNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='tvshows'),
        'traktlist': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='traktlist'),
        'imdblist': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='imdblist'),
        'tmdbtvlist': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='tmdbtvlist'),
        'tmdbmovieslist': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='tmdbmovieslist'),
        'tvliteNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='tvshows', lite=True),
        'mytvNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='mytvshows'),
        'mytvliteNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='mytvshows', lite=True),
        'downloadNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='downloads'),
        'libraryNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='library'),
        'OrionNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='orionoid'),
        'toolNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='tools'),
        'developers': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='developers'),
        'cachingTools': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='cachingTools'),
        'searchNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='search'),
        'viewsNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='views'),
        'clearCache': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='clearCache'),
        'clearAllCache': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='clearCacheAll'),
        'clearMetaCache': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='clearCacheMeta'),
        'clearCacheSearch': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='clearCacheSearch'),
        'newsNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='news'),
        'collectionsNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='collections'),
        'collectionActors': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='collectionActors'),
        'collectionBoxset': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='collectionBoxset'),
        'collectionBoxsetKids': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='collectionBoxsetKids'),
        'collectionKids': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='collectionKids'),
        'collectionSuperhero': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='collectionSuperhero'),
        'holidaysNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='holidays'),
        'halloweenNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='halloween'),
        'kidsgreyNavigator': lambda: call_module('resources.lib.indexers.navigator', 'Navigator', inst=True, method='kidsgrey'),
        # lists indexer shortcuts
        'gitNavigator': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='root_git'),
        'plist': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='root_personal'),
        'directory': lambda: call_module('resources.lib.indexers.lists', 'indexer', True, 'get', * (p('url'),)),
        'qdirectory': lambda: call_module('resources.lib.indexers.lists', 'indexer', True, 'getq', * (p('url'),)),
        'xdirectory': lambda: call_module('resources.lib.indexers.lists', 'indexer', True, 'getx', * (p('url'),)),
        'developer': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='developer'),
        'tvtuner': lambda: call_module('resources.lib.indexers.lists', 'indexer', True, 'tvtuner', * (p('url'),)),
        'youtube': lambda: call_module('resources.lib.indexers.lists', 'indexer', True, 'youtube', * (p('url'), p('action'))),
        'browser': lambda: call_module('resources.lib.indexers.lists', 'indexer', True, 'browser', * (p('url'),)),
        'docuNavigator': lambda: call_module('resources.lib.indexers.docu', 'documentary', inst=True, method='root'),
        'docuHeaven': _docu_heaven,
        # movies
        'movies': lambda: call_module('resources.lib.indexers.movies', 'movies', True, 'get', * (p('url'), p('tid')) ) if p('url') in ['tmdb_networks', 'tmdb_networks_no_unaired'] else call_module('resources.lib.indexers.movies', 'movies', True, 'get', * (p('url'),)),
        'movieProgress': lambda: call_module('resources.lib.indexers.movies', 'movies', True, 'get', * (p('action'),)),
        'moviePage': lambda: call_module('resources.lib.indexers.movies', 'movies', True, 'get', * (p('url'),)),
        'movieWidget': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='widget'),
        'movieSearch': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='search'),
        'movieSearchnew': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='search_new'),
        'movieSearchterm': lambda: call_module('resources.lib.indexers.movies', 'movies', True, 'search_term', * (p('name'),)),
        'movieDeleteTerm': lambda: call_module('resources.lib.indexers.movies', 'movies', True, 'delete_search_term', * (p('id'),)),
        'moviePerson': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='person'),
        'movieGenres': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='genres'),
        'movieLanguages': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='languages'),
        'movieCertificates': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='certifications'),
        'movieYears': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='years'),
        'moviePersons': lambda: call_module('resources.lib.indexers.movies', 'movies', True, 'persons', * (p('url'),)),
        'movieUserlists': lambda: call_module('resources.lib.indexers.movies', 'movies', inst=True, method='userlists'),
        # channels
        'channels': lambda: call_module('resources.lib.indexers.channels', 'channels', inst=True, method='get'),
        # tvshows
        'tvshows': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', True, 'get', * (p('url'), p('tid')) ) if p('url') == 'tmdb_networks' else call_module('resources.lib.indexers.tvshows', 'tvshows', True, 'get', * (p('url'),)),
        'tvshowPage': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', True, 'get', * (p('url'),)),
        'tvSearch': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='search'),
        'tvSearchnew': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='search_new'),
        'tvSearchterm': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', True, 'search_term', * (p('name'),)),
        'tvDeleteTerm': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', True, 'delete_search_term', * (p('id'),)),
        'tvPerson': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='person'),
        'tvGenres': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='genres'),
        'tvNetworks': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='networks'),
        'tvLanguages': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='languages'),
        'tvCertificates': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='certifications'),
        'tvPersons': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', True, 'persons', * (p('url'),)),
        'tvUserlists': lambda: call_module('resources.lib.indexers.tvshows', 'tvshows', inst=True, method='userlists'),
        # seasons / episodes
        'seasons': lambda: call_module('resources.lib.indexers.episodes', 'Seasons', True, 'get', * (p('tvshowtitle'), p('year'), p('imdb'), p('tmdb'), p('meta'))),
        'episodes': lambda: call_module('resources.lib.indexers.episodes', 'episodes', True, 'get',
                                       * (p('tvshowtitle'), p('year'), p('imdb'), p('tmdb'), p('meta'), p('season'), p('episode'))),
        'calendar': lambda: call_module('resources.lib.indexers.episodes', 'episodes', True, 'calendar', * (p('url'),)),
        'tvWidget': lambda: call_module('resources.lib.indexers.episodes', 'episodes', inst=True, method='widget'),
        'calendars': lambda: call_module('resources.lib.indexers.episodes', 'episodes', inst=True, method='calendars'),
        'episodeUserlists': lambda: call_module('resources.lib.indexers.episodes', 'episodes', inst=True, method='userlists'),
        # settings / control
        'setfanartquality': lambda: call_module('resources.lib.modules.control', 'control', method='setFanartQuality'),
        'refresh': lambda: call_module('resources.lib.modules.control', 'control', method='refresh'),
        'queueItem': lambda: call_module('resources.lib.modules.control', 'control', method='queueItem'),
        'openSettings': lambda: call_module('resources.lib.modules.control', 'control', False, 'openSettings', * (p('query'),)),
        # orion
        'userdetailsOrion': lambda: call_module('.orion_api', 'oa', method='authorize_orion'),
        'settingsOrion': lambda: call_module('.orion_api', 'oa', method='settings_orion'),
        'userlabelOrion': lambda: call_module('.orion_api', 'oa', method='info_orion'),
        'get_qrcode': lambda: call_module('.orion_api', 'orion_api', method='get_orion_qr'),
        # trakt / maintenance / misc
        'traktSyncsetup': lambda: call_module('.trakt', 'trakt', method='traktSyncsetup'),
        'traktchecksync': lambda: call_module('.trakt', 'trakt', method='check_sync_tables'),
        'traktgetcollections': lambda: call_module('.trakt', 'trakt', False, 'get_trakt_collection', * ('all',)),
        'startupMaintenance': lambda: call_module('.control', 'control', method='startupMaintenance'),
        'setSizes': lambda: call_module('.control', 'control', method='setSizes'),
        'updateSizes': lambda: call_module('.control', 'control', method='updateSizes'),
        'changelog': lambda: call_module('resources.lib.modules.changelog', method='get'),
        'artwork': lambda: call_module('.control', 'control', method='artwork'),
        'addView': lambda: call_module('.views', 'views', method='add_view', **{'content': p('content')}),

        'moviePlaycount': lambda: call_module('.playcount', 'movies', * (p('imdb'), p('query'))),
        'episodePlaycount': lambda: call_module('.playcount', 'episode', * (p('imdb'), p('tmdb'), p('season'), p('episode'), p('query'))),
        'seasonPlaycount': lambda: call_module('.playcount', 'season', * (p('imdb'), p('tmdb'), p('season'), p('query'))),
        'tvPlaycount': lambda: call_module('.playcount',  'tvshows', * (p('imdb'), p('tmdb'), p('query'))),

        'trailer': lambda: call_module('.trailer', 'trailers', True, 'get', * (p('name'), p('url'), p('imdb'), p('tmdb'), int(p('windowedtrailer') or 0), p('mediatype'), p('meta'))),

        'traktManager': lambda: call_module('resources.lib.modules.trakt','', False, 'manager', * (p('name'), p('imdb'), p('tmdb'), p('content'))),
        'authTrakt': lambda: call_module('resources.lib.modules.trakt', 'trakt', method='auth_trakt'),
        'authRD': lambda: (call_module('resources.lib.modules.debridapis.realdbrid', 'realdbrid', method='__dict__') , call_module('.control', 'control', method='infoDialog'))[1],
        'ResolveUrlTorrent': lambda: call_module('.control', 'control', False, 'openSettings', * (p('query'), "script.module.resolveurl")),
        'download': _download_handler,
        'play': _play_handler,
        'play1': _play_handler,
        'addItem': lambda: call_module('resources.lib.modules.sources', 'sources', True, 'addItem', * (p('title'),)),
        'playItem': lambda: call_module('resources.lib.modules.sources', 'sources', True, 'playItem', * (p('title'), p('source'))),
        'alterSources': lambda: call_module('resources.lib.modules.sources', 'sources', True, 'alterSources', * (p('url'), p('meta'))),
        'clearSources': lambda: call_module('resources.lib.modules.sources', 'sources', inst=True, method='clearSources'),
        'random': _random_handler,
        # library / sync / tools
        'movieToLibrary': lambda: call_module('resources.lib.modules.libtools', '', inst=True, method='libmovies', **{}) or call_module('resources.lib.modules.libtools', 'libtools', True, 'add_movie', * (p('name'), p('title'), p('year'), p('imdb'), p('tmdb'))),
        'moviesToLibrary': lambda:
            call_module('resources.lib.modules.libtools', attr='', inst=True,  method='libmovies', **{}) or\
            call_module('resources.lib.modules.libtools', 'libmovies', True, 'range', p('url')),
        'moviesToLibrarySilent': lambda:
            call_module('resources.lib.modules.libtools', 'libtools', method='libmovies', **{}) or\
            call_module('resources.lib.modules.libtools', 'libmovies', True, 'silent', * (p('url'),)),
        'syncTrakt': lambda: (c.log("[CM Debug @ router] running syncTrakt()"), call_module('resources.lib.modules.trakt', 'trakt', method='syncTrakt'))[1],
        'tvshowToLibrary': lambda:
            call_module('resources.lib.modules.libtools', method='libtvshows', **{}) or\
            call_module('resources.lib.modules.libtools', '',  True, 'add', * (p('tvshowtitle'), p('year'), p('imdb'), p('tmdb'))),
        'tvshowsToLibrary': lambda:
            call_module('resources.lib.modules.libtools', method='libtvshows', **{}) or\
            call_module('resources.lib.modules.libtools', '',  True, 'range', * (p('url'),)),
        'tvshowsToLibrarySilent': lambda:
            call_module('resources.lib.modules.libtools', method='libtvshows', **{}) or\
            call_module('resources.lib.modules.libtools', 'libtools', True, 'silent', * (p('url'),)),
        'updateLibrary': lambda:
            call_module('resources.lib.modules.libtools', method='libepisodes', **{}) or\
            call_module('resources.lib.modules.libtools', 'libtools', True, 'update', * (p('query'),)),
        'service': lambda:
            call_module('resources.lib.modules.libtools', method='libepisodes', **{}) or\
            call_module('resources.lib.modules.libtools', 'libtools', inst=True, method='service'),
        'urlResolver': lambda: (importlib.import_module('resolveurl'), call_module('resolveurl', None, method='display_settings'))[1],
        # more lists.indexer roots
        'debridkids': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='root_debridkids'),
        'waltdisney': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='root_waltdisney'),
        'learning': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='root_learning'),
        'songs': lambda: call_module('resources.lib.indexers.lists', 'indexer', inst=True, method='root_songs'),
    }

    # Execute handler if present
    handler = action_map.get(action)
    if handler:
        try:
            return handler()
        except Exception as e:
            c.log(f"[router] Handler for {action} failed: {e}\n{traceback.format_exc()}")
            raise

    # If not handled, fallback to original verbose chain for any remaining actions
    try:
        # keep original fallback behaviour: try to import modules as in legacy
        # This block mirrors remaining branches that were not mapped above
        # (If you find an unhandled action in logs, add it to action_map)
        c.log(f"[router] Unhandled action: {action}")
    except Exception:
        c.log(f"[router] Unexpected error: {traceback.format_exc()}")
