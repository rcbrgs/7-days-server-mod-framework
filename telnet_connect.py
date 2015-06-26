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
        self.__version__ = '0.1.6'
        self.changelog = {
            '0.1.7' : "Ignoring some output. Parser for chunk save info.",
            '0.1.6' : "Added partial parse of le. Reverted to non-healing code.",
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
                self.framework.shutdown = True
                return
            
                self.open_connection ( )
                return
        linetest = self.telnet.read_until ( b'Logon successful.' )
        if b'Logon successful.' in linetest:
            self.log.debug ( linetest.decode('ascii') )
            self.connected = True
            self.log.info ( "Telnet connected successfully." )
            self.write ( "loglevel ALL true\n".encode ( 'utf-8') )
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

            date_prefix = r'[0-9]{4}-[0-9]{2}-[0-9]{2}.[0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]+\.[0-9]+ '
            chunk_matcher = re.compile ( date_prefix + r'INF Saving ([\d]+) of chunks took ([\d])ms.' )
            chunk_match = chunk_matcher.search ( line_string )
            if chunk_match:
                self.log.info ( "Chunk save took {}ms.".format (
                    chunk_match.group ( 1 ) ) )
                continue
            
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
            
            total_matcher = re.compile ( r'Total of [\d]+ in the game' )
            total_match = total_matcher.match ( line_string )
            if total_match:
                continue

            
            # 2015-06-25T13:41:05 1361.451 INF Spawned [type=En.ityZombieCop, name=fatzombiecop, id=1747605] at (1431.5, 66.7, 264.5) Day=1429 TotalInWave=5 CurrentWave=1

            # 2015-06-25T15:43:32 8708.114 INF Kicking player: .ing
            
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
                 " ERR Error in TelnetClientSend_ " in line_string or
                 " INF Exited thread " in line_string or
                 " INF Created new play" in line_string or
                 " INF Started thread " in line_string or
                 ' INF Executing command say "' in line_string or
                 " An established connection was aborted by the software in your host" in line_string or
                 " INF Spawning Wandering Horde" in line_string or
                 " INF Spawning Night Horde for day " in line_string or
                 " INF Spawning this wave" in line_string or
                 " INF Player set to online: " in line_string  or
                 " INF Player connected, entityid=" in line_string  or
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
                 " INF [Steamworks.NET] Authenticating player: " in line_string  or
                 " INF [Steamworks.NET] Auth.AuthenticateUser()" in line_string  or
                 " INF Token length: " in line_string  or
                 " INF PlayerLogin: " in line_string  or
                 " INF [NET] PlayerConnected EntityID=-1, PlayerID='', OwnerID='', PlayerName=''" in line_string ):
                continue
            
            if " INF GMSG: " in line_string:
                self.framework.server.parse_gmsg ( line )
                continue

            if line_string.strip ( ) == "":
                continue
            
            self.log.warning ( "Unparsed output: {:s}.".format ( line_string.strip ( ) ) )

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
