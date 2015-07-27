import inspect
import logging
import time

class lock ( object ):
    def __init__ ( self ):
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.1.0'
        self.changelog = {
            '0.1.0'  : "Added changelog, logging."
            }
        
        self.callee  = None
        self.timeout = 10

    def get ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        begin = time.time ( )
        while ( self.callee != None and
                self.callee != callee ):
            if time.time ( ) - begin > self.timeout:
                break
            time.sleep ( 0.1 )
        self.callee = callee
        self.log.debug ( "callee set to {}.".format ( self.callee ) )

    def let ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        if self.callee != callee:
            self.log.warning ( "let called from non-callee!" )
            return
        callee = None
        self.log.debug ( "callee set to None." )
