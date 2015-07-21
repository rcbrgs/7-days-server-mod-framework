import framework.parser as parser
import logging
import re
import socket
import sys
import telnetlib
import time
import threading

class telnet_client ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.2.10'
        self.changelog = {
            '0.2.10' : "Added telnet connection close detection exception on chomp.",
            '0.2.9' : "Detecting game server closing connection earlier.",
            '0.2.8' : "Using telnetlib.expect errors to detect chomp timeout reliably.",
            '0.2.7' : "Added matcher for total of in game because of too many chomp timeouts.",
            '0.2.6' : "Refactored chomp to use regex to try to get rid of gt timeouts.",
            '0.2.5' : "Improved treating 0 socket write exception.",
            '0.2.4' : "Silenced spammy loggings.",
            '0.2.3' : "Fixed logging time outs incorrectly.",
            '0.2.2' : "More logging on chomp() to understand issue.",
            '0.2.1' : "Refactored to isolate some pieces and better control shutdown behaviour.",
            '0.2.0' : "Added status() to better monitor telnet behaviour.",
            '0.1.4' : "Making framework shutdown on write exception.",
            '0.1.3' : "Making shutdown on write exception.",
            '0.1.2' : "Catching error before exception for esthetic reason.",
            '0.1.1' : "Fixed telnet client leaving open threads on server.",
            '0.1.0' : "Initial commit." }
        self.daemon = True
        self.framework = framework

        self.output_matchers = [ re.compile ( b'^.*\n' ),
                                 re.compile ( b'^Day [\d]+, [\d]{2}:[\d]{2} ' ),
                                 re.compile ( b'Total of [\d]+ in the game' ),
                                 ]
        self.matchers = { }
        self.shutdown = False
        self.parsers = [ parser ( framework ) ]
        self.parsers [ 0 ].start ( )
        self.parsers_pointer = 0
        self.telnet_ip       = self.framework.preferences.telnet_ip
        self.telnet_password = self.framework.preferences.telnet_password
        self.telnet_port     = self.framework.preferences.telnet_port
        self.timestamp_input = None
        self.timestamp_input_previous = None
        self.log.info ( "creating telnetlib object" )
        self.telnet = telnetlib.Telnet ( timeout = 10 )

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        while not self.shutdown:
            if not self.check_connection ( ):
                self.log.error ( "run: check_connection is False, shutting down." )
                self.stop ( )
                continue

            line = self.chomp ( )
            self.log.debug ( "Got line '{}'.".format ( line ) )
            try:
                line_string = ""
                if line:
                    line_string = line.decode ( 'utf-8' )
                    line_string = line_string.strip ( )
            except Exception as e:
                self.log.error ( "Error %s while processing line.decode (%s)" %
                                 ( e, line ) )
            self.log.debug ( line_string )
            self.send_to_parser ( line_string )

    def stop ( self ):
        if self.check_connection:
            self.log.info ( "check_connection == True, trying to shutdown." )
            self.shutdown = True
            self.close_connection ( )

    def add_parser ( self ):
        self.parsers.append ( parser ( self.framework ) )

    def check_connection ( self ):
        """
        Should return True if everything is fine with the connection.
        Do not rely on metadata for this; this function is supposed to be reliable, and the metadata set according to its results.
        """
        return isinstance ( self.telnet.get_socket ( ), socket.socket )

    def chomp ( self ):
        self.log.debug ( "chomp() started" )
        try:
            result = self.telnet.expect ( self.output_matchers, 5 )
            if len ( result ) == 3:
                line = result [ 2 ]
                if result [ 0 ] == -1:
                    if result [ 2 ] != b'':
                        self.log.info ( "expect timed out on '{}'.".format ( result [ 2 ] ) )
                elif result [ 0 ] != 0:
                    self.log.debug ( "output_matcher [ {} ] hit".format ( result [ 0 ] ) )
        except Exception as e:
            if not self.check_connection ( ):
                self.log.warning ( "chomp had an exception, because the connection is off." )
                return
            if e == "[Errno 104] Connection reset by peer":
                self.log.warning ( "chomp: game server closed the connection." )
                self.framework.shutdown = True
                return
            if e == "telnet connection closed"
                self.log.warning ( "chomp: game server closed the connection." )
                self.framework.shutdown = True
                return
            self.log.error ( "Exception in chomp: {}".format ( e ) )
            self.log.error ( "type ( self.telnet ) == {}".format ( type ( self.telnet ) ) )
            self.log.error ( "isinstance ( self.telnet.get_socket ( ), socket.socket ) = {}".format (
                    self.check_connection ( ) ) )
            #self.log.error ( "type ( line ) == {}".format ( type ( line ) ) )
            self.framework.shutdown = True
            return
        self.log.debug ( "chomp: no exception" )
        
        if line:
            self.log.debug ( "chomp: line not null/none: '{}'".format ( line ) )
            self.timestamp_input_previous = self.timestamp_input
            self.timestamp_input = time.time ( )

        self.log.debug ( "chomp() returning" )
        return line
    
    def close_connection ( self ):
        self.write ( "exit\n".encode ( 'utf-8' ) )
        self.telnet.close ( )
        self.log.info ( "Telnet connection closed." )

    def open_connection ( self ):
        if self.check_connection ( ):
            self.log.warning ( "Attempted to re-open connection, ignoring call." )
            return
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
            self.framework.shutdown = True
            return
            
        if b'Logon successful.' in linetest:
            self.log.debug ( linetest.decode('ascii') )
            self.log.info ( "Telnet connected successfully." )
            self.write ( "loglevel ALL false\n".encode ( 'utf-8') )
        else:
            self.log.error ("Logon failed.")
            self.framework.shutdown = True
            return

    def send_to_parser ( self, line ):
        self.parsers [ self.parsers_pointer ].enqueue ( line )
        self.parsers_pointer = ( self.parsers_pointer + 1 ) % len ( self.parsers )

    def status ( self ):
        if self.timestamp_input_previous:
            interval = self.timestamp_input - self.timestamp_input_previous
            self.log.info ( "interval = {:.1f}s.".format ( interval ) )
        
    def write ( self, msg ):
        if ( self.telnet.get_socket ( ) == 0 ):
            if not self.shutdown:
                self.log.error ( "Can't get_socket()!" )
                self.framework.shutdown = True
            self.log.warning ( "Socket 0 for msg '{}'.".format ( msg ) )
            return
        try:
            self.telnet.write ( msg )
            self.log.debug ( "Wrote '{}'.".format ( msg ) )
        except AttributeError as e:
            self.log.error ( "During telnet write: {}". format ( e ) )
            #self.framework.stop ( )
            return
            
        except BrokenPipeError as e:
            self.log.warning ( "BrokenPipeError '{}'".format ( e ) )
            self.framework.shutdown = True
            return
