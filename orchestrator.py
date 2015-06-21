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
            full_module_name = module_name + "." + module_name
            self.log.debug ( "Attempting to load module %s." % full_module_name )
            try:
                mod_module = importlib.import_module ( full_module_name )
            except Exception as e:
                self.log.error ( e )
                continue
            self.log.debug ( "mod_module = %s" % str ( mod_module ) )
            mod_class = getattr ( mod_module, module_name )
            mod_instance = mod_class ( framework = self )
            self.log.info ( "Mod %s loaded." % module_name )
            self.mods.append ( mod_instance )
        
        for mod in self.mods:
            mod.start ( )

    def run ( self ):            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        self.server.offline_players ( )
        count = 1

        try:
            while self.shutdown == False:
                self.log.debug ( "Tick" )
                
                for mod in self.mods:
                    if mod.is_alive ( ) == False:
                        self.log.warning ( "mod %s is dead, restarting framework." % str ( mod ) )
                        self.shutdown = True

                self.log.debug ( "Before gt" )
                self.server.console ( "gt" )
                self.log.debug ( "After gt" )
                
                #if count % 10 == 0:
                    #self.server.offline_players ( )
                    #time.sleep ( self.preferences.loop_wait + 1 )
                
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
