import logging
import re
import sys
import telnetlib
import time
import threading

class telnet_connect ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( telnet_connect, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = '0.1.4'
        self.changelog = {
            '0.1.5' : "Refactored telnet parsing using re.",
            '0.1.4' : "Added catching memory information output from server.",
            '0.1.3' : "Catching exception during unicode decode.",
            '0.1.2' : "Added changelog." }

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
        self.log.info ( "Telnet connection closed." )

    def open_connection ( self ):
        self.log.debug ( "%s %s" % ( sys._getframe ( ).f_code.co_name,
                                     sys._getframe ( ).f_code.co_varnames ) )
        
        try:
            self.telnet.open ( self.telnet_ip, self.telnet_port, timeout = 5 )
            self.telnet.read_until ( b"Please enter password:" )
            passwd = self.telnet_password + '\n'
            self.telnet.write ( passwd.encode ( 'utf-8' ) )
        except Exception as e:
            self.log.error ( "Error while opening connection: %s." % str ( e ) )
            if not self.framework.shutdown:
                time.sleep ( self.framework.preferences.loop_wait )
                self.open_connection ( )
                return
        linetest = self.telnet.read_until ( b'Logon successful.' )
        if b'Logon successful.' in linetest:
            self.log.debug ( linetest.decode('ascii') )
            self.connected = True
            self.log.info ( "Telnet connected successfully." )
        else:
            self.log.error ("Logon failed.")

    def run ( self ):
        self.log.debug ( "%s %s" % ( sys._getframe ( ).f_code.co_name,
                                     sys._getframe ( ).f_code.co_varnames ) )
        
        while ( self.shutdown == False ):
            if ( not self.connected ):
                continue
            try:
                line = self.telnet.read_until ( b'\n', 5 )
            except Exception as e:
                self.log.error ( e )
                self.close_connection ( )
                self.open_connection ( )
                continue
            try:
                line_string = line [:-1].decode ( 'utf-8' )
            except UnicodeDecodeError as e:
                self.log.error ( "Error %s while processing line.decode (%s)" %
                                 ( e, line [:-1] ) )
                
            self.log.debug ( line_string )

            # Day 1424, 08:52
            day_matcher = re.compile ( r'Day [0-9]+, [0-9]{2}:[0-9]{2}' )
            day_match = day_matcher.match ( line_string )
            if day_match:
                self.log.debug ( "day output: {:s}".format ( line_string ) )
                self.framework.server.update_gt ( line_string )
                continue

            # 2015-06-25T09:26:33 1046.729 INF Player disconnected: EntityID=-1, PlayerID='76561198201780147', OwnerID='76561198201780147', PlayerName='ak5843171
            dconn_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]+\.[0-9]+ INF Player disconnected: EntityID=.[0-9]*, PlayerID=\'[0-9]+\', OwnerID=\'[0-9]+\', PlayerName=\'(.*)\'' )
            dconn_match = dconn_matcher.search ( line_string )
            if dconn_match:
                self.log.debug ( "dconn_match {:s}".format ( line_string ) )
                player_name = dconn_match.group ( 1 )
                player = self.framework.server.get_player ( player_name )
                if player:
                    self.framework.game_events.player_disconnected ( player )
                continue

            #2015-06-25T10:36:35 5247.946 INF Executing command 'pm 1580623 "[FF0000]st.devil666[FFFFFF] is near ([FF0000]77m[FFFFFF]) your base!"' by Telnet from 143.107.45.13:48590
            pm_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]+\.[0-9]+ INF Executing command \'pm (.+) "(.*)"\' by Telnet from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' )
            pm_match = pm_matcher.search ( line_string )
            if pm_match:
                self.log.debug ( "pm executed: to {:s}, {:s}".format ( pm_match.group ( 1 ),
                                                                       pm_match.group ( 2 ) ) )
                continue
            
            # 2015-06-25T07:59:35 10591.364 INF Executing command '' by Telnet from 143.107.45.13:47641
            cmd_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]+\.[0-9]+ INF Executing command \'([a-zA-Z0-9]+)\' by Telnet from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' )
            cmd_match = cmd_matcher.search ( line_string )
            if cmd_match:
                self.log.debug ( "cmd executed: {:s}".format ( cmd_match.group ( 1 ) ) )
                continue

            mem_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.* INF Time: [0-9]+.[0-9]+m FPS: [0-9]+.[0-9]+ Heap: [0-9]+.[0-9]+MB Max: [0-9]+.[0-9]+MB Chunks: [0-9]+ CGO: [0-9]+ Ply: [0-9]+ Zom: .* Ent: .* Items: [0-9]+' )
            mem_match = mem_matcher.match ( line_string )
            if mem_match:
                self.log.debug ( "mem output: {:s}".format ( line_string ) )
                self.framework.server.update_mem ( line_string )
                continue


            
            #pm_matcher = re.compile ( r'' )
            #if ( " INF Executing command 'pm " in line_string ):
            #    self.log.debug ( "pm " + line_string.split ( "'pm " ) [ 1 ] )
            #    continue
            
            #if (                 " INF [EAC] FreeUser (" in line_string or
            #     " INF Removing observed entity " in line_string ):
            #    continue

            if ( #" INF [EAC] UserStatusHandler callback. Status: Authenticated GUID: " in line_string  or
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
            
            #if ( "Total of " == line_string [ : 9 ] and
            #     " in the game" in line_string ):
            #    continue
            
            if " INF GMSG: " in line_string:
                self.framework.server.parse_gmsg ( line )
                continue

            
            
            if ( 'Message to player "' in line_string and
                 ' sent with sender "' in line_string ):
                continue

            if ( b', [type=EntityZombie' in line or
                 b', [type=EntityHornet' in line ):
                #self.framework.zombie_cleanup.parse_le ( line )
                continue

            if ( b', [type=EntityAnimal' in line or
                 b', [type=EntityCar' in line or
                 b', [type=EntitySupplyCrate' in line or
                 b'(EntityItem)' in line or
                 b'(EntityFallingBlock)' in line ):
                continue
            
            if ( ( b'. id=' in line )  and ( b'remote=True' in line ) ):
                self.log.debug ( "calling parse_id ( '%s' )" % line )
                self.framework.server.parse_id ( line )
                continue
            
            if ( " INF Exited thread TelnetClientSend_" in line_string or
                 " INF Telnet connection closed: " in line_string or
                 " INF Exited thread TelnetClientReceive_" or
                 " INF Telnet connection from: " or
                 " INF Started thread TelnetClientReceive_" or
                 " INF Started thread TelnetClientSend_" ):
                continue

            self.log.warning ( "Unparsed output: {:s}.".format ( line_string ) )

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
