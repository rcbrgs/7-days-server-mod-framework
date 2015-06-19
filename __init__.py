#from .communism        import communism
#from .place_protection import place_protection
from .preferences      import preferences
#from .prison           import prison
from .server           import server
from .telnet_connect   import telnet_connect
#from .translator       import translator
#from .treasure_hunt    import treasure_hunt
#from .zombie_cleanup   import zombie_cleanup

import atexit
import logging
import random
import sys
import threading
import time

class orchestrator ( threading.Thread ):
    def __init__ ( self ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )

        self.daemon = True

    def config ( self, preferences_file_name ):
        self.shutdown = False
        self.preferences = preferences ( preferences_file_name )
       
        #self.log_handler = logging.StreamHandler ( )
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

        # mods:
        #self.communism        = communism        ( framework = self )
        #self.place_protection = place_protection ( framework = self )
        #self.prison           = prison           ( framework = self )
        #self.translator       = translator       ( framework = self )
        #self.treasure_hunt    = treasure_hunt    ( framework = self )
        #self.zombie_cleanup   = zombie_cleanup   ( framework = self )

        self.mods = [ #self.communism,
                      #self.place_protection,
                      #self.prison,
                      #self.translator,
                      #self.treasure_hunt,
                      #self.zombie_cleanup ]
        ]

        #####################################################
        # Template for adding new mods:                     #
        # Copy the line below and change the variable name. #       
        # self.template = template ( framework = self )     #
        # Then copy the template.py file to a file named    #
        # as the variable you just created, and edit it.    #
        #####################################################
        
        # self.template = template ( framework = self )

        for mod in self.mods:
            mod.start ( )

    def run ( self ):
        while self.shutdown == False:
            time.sleep ( 1 )
        return
            
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
