import framework
import importlib
import logging
import sys
import threading
import time

class orchestrator ( threading.Thread ):
    def __init__ ( self ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.daemon = True
        self.__version__ = '0.1.1'

    def config ( self, preferences_file_name ):
        self.silence = False
        self.shutdown = False
        self.preferences = framework.preferences ( preferences_file_name )

        framework.set_log_file ( self.preferences.log_file )

        self.log.info ( "**************************   Starting framework   ***************************" )
        
        self.preferences.output ( )
        
        self.telnet = framework.telnet_connect ( framework = self )
        self.telnet.open_connection ( )

        self.mods = [ ]
        self.server = framework.server ( framework = self )
        self.server.start ( )

        self.telnet.start ( )

        self.mods = [ ]

        for mod in self.preferences.mods.keys ( ):
            module_name = self.preferences.mods [ mod ] [ 'module' ]
            self.load_mod ( module_name )
        
        for mod in self.mods:
            mod.start ( )

    def load_mod ( self, module_name ):
        full_module_name = module_name + "." + module_name
        
        if ( full_module_name in self.mods ):
            self.log.info ( "mod %s already in self.mods." % full_module_name )
            return
        
        self.log.debug ( "Attempting to load module %s." % full_module_name )
        try:
            mod_module = importlib.import_module ( full_module_name )
            mod_module = importlib.reload ( mod_module )
        except Exception as e:
            self.log.error ( "Ignoring unloadable module: %s." % str ( e ) )
            return
        self.log.debug ( "mod_module = %s" % str ( mod_module ) )
        mod_class = getattr ( mod_module, module_name )
        mod_instance = mod_class ( framework = self )
        self.log.info ( "Mod %s loaded." % module_name )
        self.mods.append ( mod_instance )
        return mod_instance

    def run ( self ):            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        self.server.offline_players ( )
        count = 1

        try:
            while self.shutdown == False:
                self.log.debug ( "Tick" )
                
                for mod in self.mods:
                    if mod.is_alive ( ) == False:
                        self.log.warning ( "mod %s is dead, restarting." % str ( mod ) )
                        module_name = mod.__class__.__name__
                        mod.shutdown = True
                        mod.join ( )
                        self.mods.remove ( mod )
                        mod_instance = self.load_mod ( module_name )
                        mod_instance.start ( )
                        
                        while not mod_instance.is_alive ( ):
                            self.log.warning ( "Sleeping 1 second to wait mod to run." )
                            time.sleep ( 1 )

                self.log.debug ( "Before gt" )
                self.server.console ( "gt" )
                self.log.debug ( "After gt" )
                
                if count % 10 == 0:
                    self.server.offline_players ( )
                    #time.sleep ( self.preferences.loop_wait + 1 )
                
                self.server.console ( "lp" )
            
                time.sleep ( self.preferences.loop_wait )
                count += 1
        except Exception as e:
            self.log.critical ( "Shutting down mod framework due to unhandled exception: %s." % str ( e ) )
            self.shutdown = True

        for mod in self.mods:
            self.log.info ( "mod %s stop" % str ( mod ) )
            mod.stop ( )
            self.log.info ( "mod %s join" % str ( mod ) )
            if mod.is_alive ( ):
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
