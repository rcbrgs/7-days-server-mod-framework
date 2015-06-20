from .preferences      import preferences
from .server           import server
from .telnet_connect   import telnet_connect

import importlib
import logging
import sys
import threading
import time

class orchestrator ( threading.Thread ):
    def __init__ ( self ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.daemon = True

        self.silence = False

    def config ( self, preferences_file_name ):
        self.shutdown = False
        self.preferences = preferences ( preferences_file_name )
       
        self.log_handler = logging.FileHandler ( self.preferences.log_file )
        self.log_handler.setLevel ( logging.DEBUG )
        self.log_formatter = logging.Formatter ( fmt = '%(asctime)s %(name)s %(levelname)s %(message)s',
                                                 datefmt = '%Y-%m-%d %H:%M:%S' )
        self.log_handler.setFormatter ( self.log_formatter )
        self.log.addHandler ( self.log_handler )

        self.log.info ( "**************************   Starting framework   ***************************" )
        
        self.preferences.output ( )
        
        self.telnet = telnet_connect ( framework = self )
        self.telnet.open_connection ( )

        self.mods = [ ]
        self.server = server ( framework = self )

        self.telnet.start ( )

        self.mods = [ ]

        for mod in self.preferences.mods.keys ( ):
            module_name = self.preferences.mods [ mod ] [ 'module' ]
            self.log.info ( "Attempting to load module %s." % module_name )
            mod_module = importlib.import_module ( module_name )
            self.log.info ( "mod_module = %s" % str ( mod_module ) )
            mod_class = getattr ( mod_module, module_name )
            mod_instance = mod_class ( framework = self )
            self.mods.append ( mod_instance )
        
        for mod in self.mods:
            mod.start ( )

    def run ( self ):            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        self.server.offline_players ( )
        count = 1

        try:
            while self.shutdown == False:

                for mod in self.mods:
                    if mod.is_alive ( ) == False:
                        self.log.warning ( "mod %s is dead, restarting framework." % str ( mod ) )
                        self.shutdown = True
                    
                self.server.console ( "gt" )
                if count % 10 == 0:
                    self.server.offline_players ( )
                    time.sleep ( self.preferences.loop_wait + 1 )
                
                self.server.console ( "lp" )
            
                time.sleep ( self.preferences.loop_wait )
                count += 1
        except:
            e = sys.exc_info ( ) [ 0 ]
            self.log.info ( e )
            self.log.info ( "Shutting down mod framework due to exception." )
            self.shutdown = True

        for mod in self.mods:
            self.log.info ( "mod %s stop" % str ( mod ) )
            mod.stop ( )
            self.log.info ( "mod %s join" % str ( mod ) )
            mod.join ( )

        self.telnet.stop ( )
        self.telnet.join ( )
        self.telnet.close_connection ( )

        self.log.info ( "**************************   Stopping framework   ***************************" )
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.log.info ( "<framework>.stop" )
        self.shutdown = True

    def __del__ ( self ):
        self.log.info ( "<framework>.__del__" )
        self.stop ( )

maestro = orchestrator ( )

def config ( preferences_file_name ):
    maestro.config ( preferences_file_name )
    maestro.start ( )

def console ( input_string ):
    maestro.server.console ( input_string )
