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
        self.__version__ = '0.1.8'
        self.changelog = {
            '0.1.9' : "Added measure of runtime delay.",
            '0.1.8' : "Ignoring header info. Added gt parsing. Made lag estimation more dynamic.",
            '0.1.7' : "Ignoring some output. Parser for chunk save info and for falling blocks.",
            '0.1.6' : "Added partial parse of le. Reverted to non-healing code.",
            '0.1.5' : "Refactored telnet parsing using re.",
            '0.1.4' : "Added catching memory information output from server.",
            '0.1.3' : "Catching exception during unicode decode.",
            '0.1.2' : "Added changelog." }

        self.lag = None
        self.lag_max = { 'lag' : 0,
                         'timestamp' : 0 }
        self.matchers = { }
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
            self.log.info ( "Entering password." )
            self.telnet.read_until ( b"Please enter password:" )
            passwd = self.telnet_password + '\n'
            self.telnet.write ( passwd.encode ( 'utf-8' ) )
        except Exception as e:
            self.log.error ( "Error while opening connection: %s." % str ( e ) )
            if not self.framework.shutdown:
                time.sleep ( self.framework.preferences.loop_wait )
                self.framework.shutdown = True
                return
            
                self.open_connection ( )
                return
        try:
            self.log.info ( "Waiting logon success confirmation." )
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

    def run ( self ):
        self.log.info ( "%s %s" % ( sys._getframe ( ).f_code.co_name,
                                    sys._getframe ( ).f_code.co_varnames ) )
        
        while ( self.shutdown == False ):
            begin = time.time ( )
            self.log.debug ( "telnet while begin" )
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
                line_string = line.decode ( 'utf-8' )
                line_string = line_string.strip ( )

            except Exception as e:
                self.log.error ( "Error %s while processing line.decode ( %s )." %
                                 ( e, line ) )
                
            self.log.debug ( line_string )

            date_match_string = r'([0-9]{4})-([0-9]{2})-([0-9]{2}).+([0-9]{2}):([0-9]{2}):([0-9]{2}) ([0-9]+\.[0-9]+)' # 7 groups
            ip_match_string   = r'([\d]+\.[\d]+\.[\d]+\.[\d]+)' # 1 group

            telnet_output_matches = {
                'chunks saved' : { 'to_match' : r'.* INF Saving (.*) of chunks took (.*)ms',
                                   'to_call' : [ ] },
                'claim finished' : { 'to_match' : r'Total of [\d]+ keystones in the game',
                                     'to_call'  : [ self.framework.server.llp_finished ] },
                'claim player' : { 'to_match' : r'Player "(.*) \(([\d]+)\)" owns [\d]+ keystones \(protected: [\w]+, current hardness multiplier: [\d]+\)',
                                   'to_call'  : [ self.framework.server.llp_claim_player ] },
                'claim stone' : { 'to_match' : r'\(([-+]*[\d]*), ([-+]*[\d]*), ([-+]*[\d]*)\)',
                                  'to_call'  : [ self.framework.server.llp_claim_stone ] },
                'date match' : { 'to_match' : date_match_string,
                                 'to_call'  : [ self.telnet_output_date_wrapper ] },
                'day match' : { 'to_match' : r'Day ([0-9]+), ([0-9]{2}):([0-9]{2})',
                                'to_call'  : [ self.framework.server.update_gt ] },
                'deny match' : { 'to_match' : r'(.*) INF Player (.*) denied: (.*) has been banned until (.*)',
                                 'to_call'  : [ self.framework.game_events.player_denied ] },
                'gt command executed' : { 'to_match' : date_match_string + r' INF Executing command \'gt\' by Telnet from ' + ip_match_string + ':([\d]+)',
                                          'to_call'  : [ self.framework.console.wrapper_gt ] },
                'lp command executed' : { 'to_match' : date_match_string + r' INF Executing command \'lp\' by Telnet from ' + ip_match_string + ':([\d]+)',
                                          'to_call'  : [ self.framework.console.wrapper_lp ] },
                'lp command finished' : { 'to_match' : r'Total of ([\d]+) in the game',
                                          'to_call'  : [ self.framework.console.lp_finished ] },
                'player connection' : { 'to_match' : date_match_string + r' INF Player connected, entityid=(.*), name=(.*), steamid=(.*), ip=(.*)',
                                        'to_call' : [ self.framework.game_events.player_connected ] },
                'player disconnection' : { 'to_match' : date_match_string + r' INF Player disconnected: EntityID=(.*), PlayerID=\'[0-9]+\', OwnerID=\'[0-9]+\', PlayerName=\'(.*)\'',
                                        'to_call' : [ self.framework.game_events.player_disconnected ] },
                'pm command executed' : { 'to_match' : '.* INF Executing command \'pm .* by Telnet from (.*):.*',
                                          'to_call' : [ self.framework.console.wrapper_pm ] },
                }

            if self.matchers == { }:
                for key in telnet_output_matches.keys ( ):
                    self.matchers [ key ] = { 'matcher' : re.compile (
                        telnet_output_matches [ key ] [ 'to_match' ] ),
                                              'callers'  : telnet_output_matches [ key ] [ 'to_call' ] }
                    
            for key in self.matchers.keys ( ):
                match = self.matchers [ key ] [ 'matcher' ].search ( line_string )
                if match:
                    self.log.debug ( "{} groups = {}.".format ( key, match.groups ( ) ) )
                    for caller in self.matchers [ key ] [ 'callers' ]:
                        self.log.debug ( "{} calls {}.".format ( key, caller ) )
                        caller ( match.groups ( ) )
                        self.log.debug ( "{} called {} and finished.".format ( key, caller ) )

            #2015-06-25T10:36:35 5247.946 INF Executing command 'pm 1580623 "[FF0000]st.devil666[FFFFFF] is near ([FF0000]77m[FFFFFF]) your base!"' by Telnet from 143.107.45.13:48590
            pm_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]+\.[0-9]+ INF Executing command \'pm (.+) "(.*)"\' by Telnet from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' )
            pm_match = pm_matcher.search ( line_string )
            if pm_match:
                self.log.debug ( "pm executed: to {:s}, {:s}".format ( pm_match.group ( 1 ),
                                                                       pm_match.group ( 2 ) ) )
                continue
            
            # 2015-06-25T07:59:35 10591.364 INF Executing command '' by Telnet from 143.107.45.13:47641
            cmd_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]+\.[0-9]+ INF Executing command \'([\w]+[\s]*[\w]*)\' by Telnet from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' )
            cmd_match = cmd_matcher.search ( line_string )
            if cmd_match:
                self.log.debug ( "cmd executed: {:s}".format ( cmd_match.group ( 1 ) ) )
                continue

            # 7. id=1629100, st.devil666, pos=(1969.3, 57.1, 1230.7), rot=(5.6, -54.8, 0.0), remote=True, health=68, deaths=2, zombies=21, players=0, score=16, level=1, steamid=76561198136543707, ip=91.105.156.207, ping=90\r\n
            id_matcher = re.compile ( r'[\d]+\. id=([\d]+), (.*), pos=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), rot=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), remote=([\w]+), health=([\d]+), deaths=([\d]+), zombies=([\d]+), players=([\d]+), score=([\d]+), level=(1), steamid=([\d]+), ip=([\d]+\.[\d]+\.[\d]+\.[\d]+), ping=([\d]+)' )
            id_match = id_matcher.search ( line_string )
            if id_match:
                self.log.debug ( "id: {:s}".format ( line_string ) )
                self.log.debug ( "id_match = {:s}".format ( str ( id_match ) ) )
                self.framework.server.update_id ( id_match.groups ( ) )
                continue

            item_matcher = re.compile ( r'[\d]+\. id=([\d]+), Item_[\d]+ \(EntityItem\), pos=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), rot=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), lifetime=(.*), remote=([\w]+), dead=([\w]+),.*' )
            item_match = item_matcher.match ( line_string )
            if item_match:
                self.log.debug ( "item_match" )
                #self.framework.server.update_item ( item_match.groups ( ) )
                continue
            
            falling_block_matcher = re.compile ( r'[\d]+\. id=([\d]+), FallingBlock_[\d]+ \(EntityFallingBlock\), pos=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), rot=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), lifetime=(.*), remote=([\w]+), dead=([\w]+),.*' )
            falling_block_match = falling_block_matcher.match ( line_string )
            if falling_block_match:
                self.log.debug ( "falling_block_match" )
                #self.framework.server.update_item ( item_match.groups ( ) )
                continue
            
            # 15. id=1746939, [type=EntityZombieCrawl, name=zombiecrawler, id=1746939], pos=(-349.1, 64.1, 426.4), rot=(0.0, 300.0, 0.0), lifetime=float.Max, remote=False, dead=False, health=100
            le_matcher = re.compile ( r'[\d]+\. id=([\d]+), (.*), pos=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), rot=\((.[\d]*\.[\d]), (.[\d]*\.[\d]), (.[\d]*\.[\d])\), lifetime=(.*), remote=([\w]+), dead=([\w]+), health=([\d]+).*' )
            le_match = le_matcher.match ( line_string )
            if le_match:
                self.log.debug ( "le_match" )
                self.framework.server.update_le ( le_match.groups ( ) )
                continue
            
            mem_matcher = re.compile ( r'[0-9]{4}-[0-9]{2}-[0-9]{2}.* INF Time: [0-9]+.[0-9]+m FPS: [0-9]+.[0-9]+ Heap: [0-9]+.[0-9]+MB Max: [0-9]+.[0-9]+MB Chunks: [0-9]+ CGO: [0-9]+ Ply: [0-9]+ Zom: .* Ent: .* Items: [0-9]+' )
            mem_match = mem_matcher.match ( line_string )
            if mem_match:
                self.log.debug ( "mem output: {:s}".format ( line_string ) )
                self.framework.server.update_mem ( line_string )
                continue

            sent_matcher = re.compile ( r'Message to player ".*" sent with sender "Server"' )
            sent_match = sent_matcher.match ( line_string )
            if sent_match:
                continue

            middle = time.time ( )
            idle = middle - begin
            if idle > 0.1:
                self.log.debug ( "telnet while runtime = {:.2f}".format ( middle - begin ) )
            
            # Strings to ignore:            
            if ( " INF [EAC] UserStatusHandler callback. Status: Authenticated GUID: " in line_string  or
                 " INF [EAC] FreeUser (" in line_string or
                 " INF [EAC] UserStatus" in line_string or
                 " INF Kicking player" in line_string or
                 " ERR DisconnectClient: Player " in line_string or
                 "Playername or entity/steamid id not found." in line_string or
                 " fell off the world, id=" in line_string or
                 "disconnected after " in line_string or
                 " INF Executing command " in line_string or
                 " INF AIDirector: scout" in line_string or
                 "INF AIDirector" in line_string or
                 " INF Player set to offline" in line_string or
                 " INF Start a new wave" in line_string or
                 " INF Spawned [type=" in line_string or
                 " INF [NET] PlayerDisconnect" in line_string or
                 " INF [Steamworks.NET]" in line_string or
                 " ping too high " in line_string or
                 " INF Telnet connection " in line_string or
                 "SocketException: An existing connection was forcibly closed by the remote host." in line_string or
                 " ERR Could not save file " in line_string or
                 " ERR Error in TelnetClientSend_ " in line_string or
                 " INF Exited thread " in line_string or
                 " INF Created new play" in line_string or
                 " INF Started thread " in line_string or
                 ' INF Executing command say "' in line_string or
                 " An established connection was aborted by the software in your host" in line_string or
                 " INF Spawning Wandering Horde" in line_string or
                 " INF Spawning Night Horde for day " in line_string or
                 " INF Spawning this wave" in line_string or
                 " ERR Buff attach(particleeffects/p_onfire, @impact) action wants to be attached to an impact point but none were provided!" in line_string or
                 "IOException: Sharing violation on path " in line_string or
                 " INF Adding observed entity: " in line_string  or
                 " INF Removing observed entity" in line_string  or
                 " INF Created player with id=" in line_string  or
                 " INF RequestToSpawnPlayer: " in line_string  or
                 " INF [Steamworks.NET] Authentication callback. ID: " in line_string  or
                 " INF RequestToEnterGame: " in line_string  or
                 " INF Allowing player with id " in line_string  or
                 " Playername or entity/steamid id not found." in line_string or
                 " INF Spawned [type=" in line_string or
                 " INF [EAC] Registering user: id=" in line_string  or
                 " ERR [EAC] Log: Unknown use" in line_string or
                 " INF Player set to online: " in line_string or
                 "Playername or entity ID not found." == line_string or
                 " INF [Steamworks.NET] Authenticating player: " in line_string  or
                 " INF [Steamworks.NET] Auth.AuthenticateUser()" in line_string  or
                 " INF Token length: " in line_string  or
                 " INF PlayerLogin: " in line_string  or
                 "*** Connected with 7DTD server" in line_string or
                 "*** Server version: Alpha 11.6 (b5) Compatibility Version: Alpha 11.6" in line_string or 
                 "*** Dedicated server only build" in line_string or
                 "Server IP:   " in line_string or
                 "Server port: " in line_string or
                 "Max players: " in line_string or
                 "Game mode:   " in line_string or
                 "World:       " in line_string or
                 "Game name:   " in line_string or
                 "Difficulty:  " in line_string or
                 "Press 'help' to get a list of all commands. Press 'exit' to end session." in line_string or
                 "Enabling all loglevels on this connection." in line_string or
                 " INF [NET] PlayerConnected EntityID=-1, PlayerID='', OwnerID='', PlayerName=''" in line_string ):
                continue
            
            if " INF GMSG: " in line_string:
                self.framework.server.parse_gmsg ( line )
                continue

            if line_string.strip ( ) == "":
                continue
            
            self.log.debug ( "Unparsed output: '{:s}'.".format ( line_string.strip ( ) ) )
            self.log.debug ( "telnet while end" )

        self.log.info ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
        self.shutdown = True

        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def telnet_output_date_wrapper ( self, date_matcher_groups ):
        self.log.debug ( date_matcher_groups )
        year = date_matcher_groups [ 0 ]
        month = date_matcher_groups [ 1 ]
        day = date_matcher_groups [ 2 ]
        hour = date_matcher_groups [ 3 ]
        minute = date_matcher_groups [ 4 ]
        second = date_matcher_groups [ 5 ]
        server_time = time.strptime ( "{} {} {} {} {} {}".format (
            year, month, day, hour, minute, second ),
                                      "%Y %m %d %H %M %S" )
        now = time.time ( )
        lag = time.mktime ( server_time ) - now
        if self.lag is None:
            self.lag = lag
        lag_increase = self.lag - lag
        self.lag = lag
        if abs ( lag_increase ) > 0.1:
            self.log.debug ( "lag_change = {:.1f}".format ( lag_increase ) )

        old_max_timestamp = self.lag_max [ 'timestamp' ]
        if now != self.lag_max [ 'timestamp' ]:
            self.lag_max [ 'lag' ] *= 0.95
            self.lag_max [ 'timestamp' ] = now
            
        if self.lag_max [ 'lag' ] < lag_increase:
            self.lag_max [ 'lag' ] = lag_increase
            self.lag_max [ 'timestamp' ] = now

        if now - old_max_timestamp > 1:
            self.log.info ( "lag: {:.1f}s".format ( self.lag_max [ 'lag' ] ) )
        
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
