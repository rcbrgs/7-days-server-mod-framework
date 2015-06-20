import logging
import sys
import telnetlib
import time
import threading

class telnet_connect ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( telnet_connect, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
        self.shutdown = False
        self.connected = False
        self.framework = framework
                
        self.telnet_ip = self.framework.preferences.telnet_ip
        self.telnet_password = self.framework.preferences.telnet_password
        self.telnet_port = self.framework.preferences.telnet_port
       
        self.telnet = telnetlib.Telnet ( timeout = 10 )
        
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

        self.daemon = True

    def __del__ ( self ):
        self.stop ( )

    def close_connection ( self ):
        self.log.info ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        self.connected = False
        self.telnet.close ( )

    def open_connection ( self ):
        self.log.info ( "%s %s" % ( sys._getframe ( ).f_code.co_name,
                                    sys._getframe ( ).f_code.co_varnames ) )
        
        try:
            self.telnet.open ( self.telnet_ip, self.telnet_port, timeout = 5 )
            self.telnet.read_until ( b"Please enter password:" )
            passwd = self.telnet_password + '\n'
            self.telnet.write ( passwd.encode ( 'utf-8' ) )
        except:
            e = sys.exc_info ( ) [ 0 ]
            self.log.error ( e )
            self.framework.shutdown = True
            sys.exit ( 1 )
        linetest = self.telnet.read_until ( b'Logon successful.' )
        if b'Logon successful.' in linetest:
            self.log.debug ( linetest.decode('ascii') )
            self.connected = True
        else:
            self.log.error ("Logon failed.")

    def run ( self ):
        self.log.info ( "%s %s" % ( sys._getframe ( ).f_code.co_name,
                                    sys._getframe ( ).f_code.co_varnames ) )
        
        while ( self.shutdown == False ):
            if ( not self.connected ):
                continue
            try:
                line = self.telnet.read_until ( b'\n', 5 )
            except:
                e = sys.exc_info()[0]
                self.log.error ( e )
                self.close_connection ( )
                self.open_connection ( )
                continue
            line_string = line [:-1].decode ( 'utf-8' )
            self.log.debug ( line_string )

            if ( " INF Executing command 'gt' by Telnet from " in line_string or
                 " INF Executing command 'le' by Telnet from " in line_string or
                 " INF Executing command 'lp' by Telnet from " in line_string or
                 " INF Executing command 'saveworld' by Telnet from " in line_string or
                 " INF Executing command 'say " in line_string ):
                continue

            if ( ( " INF Player " in line_string and
                   " disconnected after " in line_string and
                   "minutes" in line_string ) or
                 " INF Player disconnected: EntityID=" in line_string ):
                self.framework.server.offline_player ( line_string )
                continue
            if ( " INF Player set to offline: " in line_string or
                 " INF [EAC] FreeUser (" in line_string or
                 " INF Removing observed entity " in line_string ):
                continue

            if ( " INF [EAC] UserStatusHandler callback. Status: Authenticated GUID: " in line_string  or
                 " INF Player set to online: " in line_string  or
                 " INF Player connected, entityid=" in line_string  or
                 " INF Adding observed entity: " in line_string  or
                 " INF Created player with id=" in line_string  or
                 " INF RequestToSpawnPlayer: " in line_string  or
                 " INF [Steamworks.NET] Authentication callback. ID: " in line_string  or
                 " INF RequestToEnterGame: " in line_string  or
                 " INF Allowing player with id " in line_string  or
                 " INF [EAC] Registering user: id=" in line_string  or
                 " INF [Steamworks.NET] Authenticating player: " in line_string  or
                 " INF [Steamworks.NET] Auth.AuthenticateUser()" in line_string  or
                 " INF Token length: " in line_string  or
                 " INF PlayerLogin: " in line_string  or
                 " INF [NET] PlayerConnected EntityID=-1, PlayerID='', OwnerID='', PlayerName=''" in line_string ):
                continue
            
            if ( " INF Time: " in line_string and
                 " Heap: " in line_string ):
                continue
            
            if ( "Total of " == line_string [ : 9 ] and
                 " in the game" in line_string ):
                continue
            
            if " INF GMSG: " in line_string:
                self.framework.server.parse_gmsg ( line )
                continue

            if ( " INF Executing command 'pm " in line_string ):
                self.log.debug ( "pm " + line_string.split ( "'pm " ) [ 1 ] )
                continue
            
            if ( 'Message to player "' in line_string and
                 ' sent with sender "' in line_string ):
                continue

            if ( b', [type=EntityZombie' in line or
                 b', [type=EntityHornet' in line ):
                self.framework.zombie_cleanup.parse_le ( line )
                continue

            if ( b', [type=EntityAnimal' in line or
                 b', [type=EntityCar' in line or
                 b', [type=EntitySupplyCrate' in line or
                 b'(EntityItem)' in line or
                 b'(EntityFallingBlock)' in line ):
                continue
            
            if ( ( b'. id=' in line )  and ( b'remote=True' in line ) ):
                self.framework.server.parse_id ( line )
                continue
            
            if ( b"Day " in line ):
                self.framework.server.parse_get_time ( line )
                continue

            if ( " INF Exited thread TelnetClientSend_" in line_string or
                 " INF Telnet connection closed: " in line_string or
                 " INF Exited thread TelnetClientReceive_" or
                 " INF Telnet connection from: " or
                 " INF Started thread TelnetClientReceive_" or
                 " INF Started thread TelnetClientSend_" ):
                continue

            self.log.info ( line_string )

        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
        self.shutdown = True

        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
    def write ( self, msg ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
        if ( self.telnet.get_socket ( ) == 0 ):
            self.open_connection ( )
        try:
            self.telnet.write ( msg )
        except AttributeError as e:
            self.log.error ( e )
            #self.close_connection ( )
            #self.open_connection ( )
            self.framework.stop ( )
            
        except BrokenPipeError as e:
            self.log.error ( e )
            #self.close_connection ( )
            #self.open_connection ( )
            self.framework.stop ( )

        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )
