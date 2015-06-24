import framework
import logging
import sys
import threading
import time

class console ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.1.0"
        self.changelog = {
            '0.1.0' : "Initial version." }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def input ( self, msg ):
        self.framework.server.console ( msg )
        
    def pm ( self, player_id, msg ):
        self.framework.server.pm ( player_id, msg )

    def say ( self, msg ):
        self.framework.server.say ( msg )
