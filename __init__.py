from .orchestrator     import orchestrator
from .preferences      import preferences
from .server           import server
from .telnet_connect   import telnet_connect

import importlib
import logging
import sys
import threading
import time

__version__ = '0.1.0'

maestro = orchestrator ( )

def config ( preferences_file_name ):
    maestro.config ( preferences_file_name )
    maestro.start ( )

def console ( input_string ):
    maestro.server.console ( input_string )
