from .console          import ( queued_console )
from .entity_info      import entity_info
from .game_events      import game_events
from .orchestrator     import orchestrator
from .parser           import ( parser )
from .player_info      import player_info
from .polis            import polis
from .preferences      import preferences
from .rank             import rank
from .server           import server
from .telnet_client.telnet_client    import telnet_client
from .utils                          import utils
from .void_fall_detector             import void_fall_detector
from .world_state                    import world_state

import importlib
import logging
import sys
import threading
import time

__version__ = '0.2.1'
changelog = {
    '0.2.1' : "Added entity_info module.",
    }

log = logging.getLogger ( __name__ )
log.setLevel ( logging.INFO )

maestro = orchestrator ( )

def config ( preferences_file_name ):
    maestro.config ( preferences_file_name )
    maestro.start ( )

def set_log_file ( log_file_name ):
    log_handler = logging.FileHandler ( log_file_name )
    log_handler.setLevel ( logging.DEBUG )
    log_formatter = logging.Formatter ( fmt = '%(asctime)s %(name)s %(levelname)s %(message)s',
                                        datefmt = '%Y-%m-%d %H:%M:%S' )
    log_handler.setFormatter ( log_formatter )
    log.addHandler ( log_handler )

import atexit

def stop ( ):
    log.info ( "Closing everything for shutdown." )
    maestro.stop ( )
    maestro.join ( )

atexit.register ( stop )
