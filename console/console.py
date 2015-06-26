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

        self.pm_executing = False
        self.timestamp_lp = 0
        self.timestamp_pm = 0

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def send ( self, message ):
        self.log.debug ( message )
            
        if isinstance ( message, str ):
            inputmsg = message + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = messagge.decode ( 'ascii' )
            inputmsg = inputmsg + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
                
        self.framework.server.telnet_connection.write ( outputmsg )

    def lp ( self ):
        if ( time.time ( ) - self.timestamp_lp ) < self.framework.preferences.loop_wait:
            self.log.debug ( "lp timestamp too recent. Ignoring call for lp." )
            return
            
        self.timestamp_lp = time.time ( )
        self.send ( "lp" )        
        
    def pm ( self, player, message ):
        limit = 5
        begin = time.time ( )
        while self.pm_executing:
            self.log.info ( "Waiting for PM to execute." )
            time.sleep ( 0.1 )
            if time.time ( ) - begin > limit:
                self.log.warning ( "Unblocking PM by limit exceeded." )
                self.pm_executing = False
                
        pm_string = 'pm {} "{}"'.format ( player.steamid, message )
        self.log.info ( pm_string )
        self.send ( pm_string )
        self.timestamp_pm = time.time ( )
        self.pm_executing = True

    def say ( self, msg ):
        """
        TELNET MESSAGING String-Conversion Check for Ascii/Bytes and Send-Message Function
        Because Casting Byte to Byte will fail.
        """
        if isinstance ( msg, str ):
            inputmsg = 'say "' + msg.replace ( '"', ' ' ) + '"' + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = msg.decode('ascii')
            inputmsg = 'say "' + inputmsg.replace ( '"', ' ' ) + '"' + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        self.log.debug ( outputmsg )
        if not self.framework.silence:
            self.framework.server.telnet_connection.write ( outputmsg )
        else:    
            self.log.info ( "(silenced) %s" % outputmsg )

    def wrapper_lp ( self, lp_matcher_groups ):
        if lp_matcher_groups [ 7 ] == self.framework.preferences.mod_ip:
            self.log.debug ( "lp matched ip" )
            self.timestamp_lp = time.time ( )
        else:
            self.log.debug ( "lp unmatch ip" )

    def wrapper_pm ( self, pm_matcher_groups ):
        interval = time.time ( ) - self.timestamp_pm
        self.log.info ( "ACK ({:.1f}s): pm from Telnet {}".format ( interval, pm_matcher_groups [ 0 ] ) )
        self.pm_executing = False
