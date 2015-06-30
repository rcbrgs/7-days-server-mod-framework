import logging
import re
import sys
import telnetlib
import time
import threading

class telnet_client ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.1.0'
        self.changelog = {
            '0.1.0' : "Initial commit." }

        self.daemon = True

        self.matchers = { }
        self.shutdown = False
        self.connected = False
        self.framework = framework
                
        self.telnet_ip       = self.framework.preferences.telnet_ip
        self.telnet_password = self.framework.preferences.telnet_password
        self.telnet_port     = self.framework.preferences.telnet_port
       
        self.telnet = telnetlib.Telnet ( timeout = 10 )

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        while ( self.shutdown == False ):
            if ( not self.connected ):
                time.sleep ( self.framework.preferences.loop_wait )
                continue
            try:
                line = self.telnet.read_until ( b'\n', 5 )
                self.log.debug ( "Got line '{}'.".format ( line ) )
            except Exception as e:
                self.log.error ( e )
                self.close_connection ( )
                self.open_connection ( )
                continue
            try:
                line_string = ""
                if line:
                    line_string = line.decode ( 'utf-8' )
                    line_string = line_string.strip ( )
            except Exception as e:
                self.log.error ( "Error %s while processing line.decode (%s)" %
                                 ( e, line ) )
                
            self.log.debug ( line_string )

            self.framework.parser.enqueue ( line_string )

    def stop ( self ):
        self.shutdown = True

    def close_connection ( self ):
        self.connected = False
        self.telnet.close ( )
        self.log.info ( "Telnet connection closed." )

    def open_connection ( self ):
        try:
            self.telnet.open ( self.telnet_ip, self.telnet_port, timeout = 5 )
            self.telnet.read_until ( b"Please enter password:" )
            passwd = self.telnet_password + '\n'
            self.telnet.write ( passwd.encode ( 'utf-8' ) )
        except Exception as e:
            self.log.error ( "Error while opening connection: %s." % str ( e ) )
            self.framework.shutdown = True
            return
        
        try:
            linetest = self.telnet.read_until ( b'Logon successful.' )
        except Exception as e:
            self.log.error ( "linetest = telnet.read_until exception: {}.".format ( e ) )
            
        if b'Logon successful.' in linetest:
            self.log.debug ( linetest.decode('ascii') )
            self.connected = True
            self.log.info ( "Telnet connected successfully." )
            self.write ( "loglevel ALL false\n".encode ( 'utf-8') )
        else:
            self.log.error ("Logon failed.")
            self.framework.shutdown = True

    def write ( self, msg ):
        if ( self.telnet.get_socket ( ) == 0 ):
            self.open_connection ( )
        try:
            self.telnet.write ( msg )
            self.log.debug ( "Wrote '{}'.".format ( msg ) )
        except AttributeError as e:
            self.log.error ( e )
            self.framework.stop ( )
            
        except BrokenPipeError as e:
            self.log.error ( e )
            self.framework.stop ( )
