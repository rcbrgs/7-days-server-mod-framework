import framework.player_info as player_info
import logging
import math
import pickle
import pygeoip
import random
import sys
import threading
import time

class server ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( server, self ).__init__ ( )
        self.daemon = True
        self.log = logging.getLogger ( __name__ )
        self.__version__ = '0.1.1'

        self.log.info ( "Server module initializing." )
        self.shutdown = False
        self.framework = framework
        self.preferences = self.framework.preferences
        self.chat = None
        self.chat_log_file = self.preferences.chat_log_file
        self.telnet_connection = self.framework.telnet
        self.player_info_file = self.preferences.player_info_file
        self.geoip = pygeoip.GeoIP ( self.preferences.geoip_file, pygeoip.MEMORY_CACHE )
        
        self.day = None
        self.hour = None
        self.minute = None
        self.time = None

        self.commands = { 'about'       : ( self.command_about,
                                            " /about will tell you where to get this mod." ),
                          'curse'       : ( self.curse_player,
                                            " /curse player_name prints an unfriendly message." ),
                          'me'          : ( self.command_print_player_info,
                                            " /me will print your info." ),
                          'help'        : ( self.command_help,
                                            " /help shows the list of commands." ),
                          'players'     : ( self.print_players_info,
                                            " /players prints players info." ),
                          'rules'       : ( self.command_rules,
                                            " /rules will print server rules." ),
                          'sos'         : ( self.sos,
                                            " /sos will ask players to help you." ),
                          'starterbase' : ( self.output_starter_base,
                                            " /starterbase will output information about starter base." ),
                          'status'      : ( self.mod_status,
                                            " /status lists running mods." ) }
        
        file_found = True
        try:
            pickle_file = open ( self.player_info_file, 'rb' )
        except FileNotFoundError as e:
            self.log.error ( e )
            self.log.info ( "Creating new player info file." )
            file_found = False

        if ( file_found ):
            self.players_info = pickle.load ( pickle_file )
        else:
            self.players_info = { }

    def __del__ ( self ):
        self.log.warning ( "__del__" )
        if self.chat != None:
            self.chat.close ( )
        pickle_file = open ( self.player_info_file, 'wb' )
        pickle.dump ( self.players_info, pickle_file, pickle.HIGHEST_PROTOCOL )

    def calculate_bearings ( self, player_origin, player_helper ):
        origin_x = player_origin.pos_x
        origin_y = player_origin.pos_y
        helper_x = player_helper.pos_x
        helper_y = player_helper.pos_y
        relative_x = origin_x - helper_x
        relative_y = origin_y - helper_y
        distance = math.sqrt ( relative_x ** 2 + relative_y ** 2 )
        acos = math.degrees ( math.acos ( relative_x / distance ) )
        if ( relative_y < 0 ):
            acos += 180
        return ( distance , int ( ( acos - 90 ) % 360 ) )

    def calculate_distance ( self, point_A, point_B ):
        return math.sqrt ( ( point_A [ 0 ] - point_B [ 0 ] ) ** 2 +
                           ( point_A [ 1 ] - point_B [ 1 ] ) ** 2 )

    def command_about ( self, origin, message ):
        self.say ( "This mod was initiated by Schabracke and is developed by rc." )
        self.say ( "http://github.com/rcbrgs/7-days-server-mod-framework." )
    
    def command_help ( self, msg_origin, msg_content ):
        if len ( msg_content ) > len ( "/help" ):
            for key in self.commands.keys ( ):
                if msg_content [ 6 : -1 ] == key:
                    self.say ( self.commands [ key ] [ 1 ] )
                    return
            for mod in self.framework.mods:
                for key in mod.commands.keys ( ):
                    if msg_content [ 6 : -1 ] == key:
                        self.say ( mod.commands [ key ] [ 1 ] )
                        return

        command_list = [ ]
        for key in self.commands.keys ( ):
            command_list.append ( key )
        for mod in self.framework.mods:
            for key in mod.commands.keys ( ):
                command_list.append ( key )

        help_message = "Available commands: "
        for mod_key in sorted ( command_list ):
            help_message += mod_key + " "
        
        self.say ( help_message )
            
    def console ( self, message ):
        self.log.debug ( message )
        if ( message != "gt" and
             message != "lp" ):
            if message [ : 3 ] == "pm ":
                splitted = message.split ( " " )
                try:
                    destiny = self.get_player ( int ( splitted [ 1 ] ) ).name
                except ValueError:
                    self.log.info ( message )
                    return
                loggable = "pm %s" % destiny
                for substring in splitted [ 2 : ]:
                    loggable += " " + substring
                self.log.info ( loggable )
            else:
                self.log.info ( message )
            
        if isinstance ( message, str ) == True:
            inputmsg = message + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = messagge.decode('ascii')
            inputmsg = inputmsg + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
                
        self.telnet_connection.write ( outputmsg )

    def command_rules ( self, origin, message ):
        self.say ( "rules are: 1. [FF0000]PVE[FFFFFF] only." )
        self.say ( "                2. No base raping or looting." )
        self.say ( "                3. Do not build / claim inside cities or POIs." )
        self.say ( "All offenses are punishable by permabans, admins judge fairly." )
        self.say ( "Admins are: [400000]Schabracke[FFFFFF], Launchpad, AzoSento, and [FFAAAA]Sitting Duck[FFFFFF]." )
        self.say ( " /sethome sets a 50m radius where only people you invite can stay." )
        self.say ( "Drop on death: everything. Drop on exit: nothing." )
        self.say ( "Player killers are automatically imprisoned." )
        
    def curse_player ( self, msg_origin, msg_content ):
        target = self.get_player ( msg_content [ 7 : -1 ] )
        if target != None:
            curses = [ "%s can't hit a fat zombie with a blunderbuss.",
                       "%s infected a cheerleader.",
                       "%s, may your path be filled with invisible spikes!",
                       "Can't wait for %s to zombify!",
                       "%s spent 5 SMG clips to kill a zombie crawler.",
                       "That zombie dog is almost as ugly as %s.",
                       "Hard to tell if it's a rabbit or %s screaming.",
                       "Your tea is the weakest, %s!",
                       "I was told %s broke all the crates on the tool shop.",
                       "Break a leg, %s!",
                       "I hope %s loses a claim stone.",
                       "'%s' is just another name for 'zombie dinner'.",
                       "Zombies are looking for brains. Don't worry %s, you're safe!",
                       "Hey %s go away I can't smell my rotten pig with you around.",
                       "You really should find a job %s." ]
            some_msg = curses [ random.randint ( 0, len ( curses ) - 1 ) ]
            self.say ( some_msg % str ( target.name_sane ) )
        else:
            self.say ( "I would never curse such a nice person!" )

    def enforce_home_radii ( self, playerid ):
        player = self.get_player ( playerid )
        for key in self.players_info.keys ( ):
            other = self.get_player ( key )
            if other.playerid != player.playerid:
                if other.home != None:
                    if ( other.home_invitees != None and
                         not player.playerid in other.home_invitees ):
                        distance = self.calculate_distance ( ( player.pos_x, player.pos_y ),
                                                             other.home )
                        if  distance < self.preferences.home_radius * 2:
                            if other.online == True:
                                self.console ( 'pm %s "[FF0000]%s[FFFFFF] is near ([FF0000]%dm[FFFFFF]) your base!"' % ( other.playerid, player.name_sane, int ( distance ) ) )
                            if player.home_invasion_beacon == None:
                                self.console ( 'pm %s "You are too near %s base! Teleport position saved."' % ( player.playerid, other.name_sane ) )
                                player.home_invasion_beacon = ( player.pos_x, player.pos_y, player.pos_z + self.framework.preferences.teleport_lag_cushion )
                                return
                            beacon_distance = self.calculate_distance ( player.home_invasion_beacon,
                                                                        other.home )
                            if distance < self.preferences.home_radius:
                                self.say ( "%s invaded %s's base! [0000FF]Teleporting away...[FFFFFF]" % ( player.name_sane, self.players_info [ key ].name_sane ) )
                                if beacon_distance < self.preferences.home_radius * 1.5:
                                    self.say ( "%s teleport destination is too near %s's base, changing it to starterbase." % ( player.name_sane, other.name_sane ) )
                                    player.home_invasion_beacon = ( 1500, 350, 67 + self.framework.preferences.teleport_lag_cushion )
                                self.teleport ( player, player.home_invasion_beacon )
                                return
                            self.console ( 'pm %s "You are still near ([880000]%dm[FFFFFF]) %s base!"' % ( player.playerid,
                                                                                                           int ( distance ),
                                                                                                           other.name_sane ) )
                            return
        player.home_invasion_beacon = None
                
    def find_nearest_player ( self, playerid ):
        player_distances = { }
        player_inverted_directions = { }
        distances = [ ]
        origin_x = self.players_info [ playerid ].pos_x
        origin_y = self.players_info [ playerid ].pos_y
        for key in self.players_info.keys ( ):
            if key != playerid:
                if self.players_info [ key ].online == True:
                    helper_x = self.players_info [ key ].pos_x
                    helper_y = self.players_info [ key ].pos_y
                    relative_x = origin_x - self.players_info [ key ].pos_x
                    relative_y = origin_y - self.players_info [ key ].pos_y
                    distance = math.sqrt ( relative_x ** 2 + relative_y ** 2 )
                    player_distances [ key ] = distance
                    distances.append ( distance )
                    acos = math.degrees ( math.acos ( relative_x / distance ) )
                    if ( relative_y < 0 ):
                        acos += 180
                    
                    player_inverted_directions [ key ] = int ( ( acos - 90 ) % 360 )
        min_distance = min ( distances )
        for key in player_distances.keys ( ):
            if player_distances [ key ] == min_distance:
                return ( key, min_distance, player_inverted_directions [ key ] )

    def get_online_players ( self ):
        result = [ ]
        for key in self.players_info.keys ( ):
            if self.players_info [ key ].online == True:
                result.append ( key )
        return result
            
    def get_player ( self, player ):
        if isinstance ( player, player_info ):
            return player
        if isinstance ( player, int ):
            if player in self.players_info.keys ( ):
                return self.players_info [ player ]
            else:
                return None
        if not isinstance ( player, str ):
            return None
        possibilities = [ ]
        for key in self.players_info.keys ( ):
            if player == self.players_info [ key ].name:
                return self.players_info [ key ]
            if player.lower ( ) in self.players_info [ key ].name.lower ( ):
                possibilities.append ( key )
        if len ( possibilities ) == 1:
            return self.players_info [ possibilities [ 0 ] ]
        elif len ( possibilities ) > 1:
            self.log.info ( "called from %s" % str ( sys._getframe ( ).f_back.f_code.co_name ) )
            msg = "I can't decide if you mean "
            for entry in possibilities:
                msg += self.players_info [ entry ].name_sane + ", "
            msg = msg [ : -2 ]
            msg += "."
            
            if len ( possibilities ) > 5:
                msg = "I can't decide if you mean "
                for entry in possibilities [ 0 : 2 ]:
                    msg += self.players_info [ entry ].name_sane + ", "
                msg += " or " + str (  len ( possibilities ) - 3 ) + " others."

            self.say ( msg )
            return None
        
        self.log.error ( "No player with identifier %s." % str ( player ) )
        return None
            
    def give_player_stuff ( self,
                            player_input,
                            stuff,
                            quantity ):
        player = self.get_player ( player_input )
        msg = 'give ' + player.name_sane + ' ' + stuff + ' ' + str ( quantity )
        self.console ( msg )

    def greet ( self ):
        self.say ( "%s module %s loaded." % ( self.__class__.__name__,
                                              self.__version__ ) )
        
    def list_players ( self ):
        for key in self.players_info.keys ( ):
            print ( self.players_info [ key ].name )
            
    def list_online_players ( self ):
        for key in self.players_info.keys ( ):
            if self.players_info [ key ].online == True:
                print ( self.players_info [ key ].name )

    def mod_status ( self, msg_origin, msg_content ):
        self.greet ( )
        for mod in self.framework.mods:
            mod.greet ( )

    def offline_player ( self, server_log ):
        self.log.info ( "%s" % server_log )

        player_name = server_log.split ( " INF Player " )
        if len ( player_name ) > 1:
            player_name = player_name [ 1 ].split ( " disconnected after " )
            if len ( player_name ) > 1:
                player_name = player_name [ 0 ]
            else:
                player_name = server_log.split ( "', PlayerName='" )
                if len ( player_name ) > 1:
                    player_name = player_name [ 1 ] [ : -2 ]

        if player_name == "":
            return
        
        self.log.info ( "Trying get_player ( %s )" % str ( player_name ) )
        try:
            player = self.get_player ( player_name )
        except Exception as e:
            self.log.error ( "offline_player ( '%s' ): %s." % ( server_log, str ( e ) ) )
            player = None
            
        if player != None:
            player.online = False
            self.log.info ( "%s.online == %s" % ( player.name_sane, str ( player.online ) ) )
            return
        
    def offline_players ( self ):
        for key in self.players_info.keys ( ):
            self.players_info [ key ].online = False

    def output_starter_base ( self, msg_origin, msg_content ):
        self.say ( "The starterbase is at 1500 E, 350 N. Password is 'noob'." )
        self.say ( "To teleport there, type /gostart." )
        self.say ( "- Replant what you harvest." )
        self.say ( "- Take what you need, and repay with work around the base." )
        #self.say ( "- Stop all fires and be silent during nights." )
        
    def parse_get_time ( self,
                         msg = None ):
        line = msg
        try:
            day    = int ( line.split ( b", " ) [ 0 ].split ( b"Day " ) [ 1 ] )
            hour   = int ( line.split ( b", " ) [ 1 ].split ( b":"    ) [ 0 ] )
            minute = int ( line.split ( b", " ) [ 1 ].split ( b":"    ) [ 1 ] )
            if ( day != self.day or
                 hour != self.hour ):
                self.log.info ( ">>>>>  day %d, %02dh%02d  <<<<<" % ( day, hour, minute ) )
            self.day    = day
            self.hour   = hour
            self.minute = minute
            self.time   = ( self.day, self.hour, self.minute )

        except IndexError as e:
            self.log.error ( e )
            self.log.error ( line )

    def parse_gmsg ( self,
                     msg = None ):
        decoded_msg = msg.decode ( 'utf-8' )
        msg_prefixless = decoded_msg.split ( " INF GMSG: " ) [ 1 ]
        msg_splitted = msg_prefixless.split ( ": " )
        if len ( msg_splitted ) > 1:
            msg_origin = msg_splitted [ 0 ]
            if len ( msg_splitted ) > 2:
                msg_content = ""
                for item in range ( 1, len ( msg_splitted ) - 1 ):
                    msg_content += msg_splitted [ item ] + ": "
                    msg_content += msg_splitted [ -1 ] [ : -1 ]
            else:
                msg_content = msg_splitted [ 1 ] [ : -1 ]
            self.log.info ( "CHAT %s: %s" % ( msg_origin, msg_content ) )
            if len ( msg_content ) > 2:
                if msg_content [ 0 : 1 ] == "/":
                    # chat message started with "/"
                    # so it is possibly a command.
                    for key in self.commands.keys ( ):
                        if msg_content [ 1 : len ( key ) + 1 ] == key:
                            self.commands [ key ] [ 0 ] ( msg_origin, msg_content )
                            return
                    for mod in self.framework.mods:
                        for key in mod.commands.keys ( ):
                            if msg_content [ 1 : len ( key ) + 1 ] == key:
                                mod.commands [ key ] [ 0 ] ( msg_origin, msg_content )
                                return
                    self.say ( "Syntax error: %s." % msg_content [ 1 : -1 ] )
                else:
                    for mod in self.framework.mods:
                        if mod.__class__.__name__ == "translator":
                            mod.translate ( msg_origin, msg_content [ : -1 ] )

    def parse_id ( self,
                   msg = None ):
        #self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
        if b"[type=" in msg:
            return
        current_parse = player_info ( )
        #text = msg.decode ('ascii')
        text = msg.decode ('utf-8')

        try:
            # 3. id=1560, rc, pos=(513.8, 101.1, 0.2), rot=(-2.8, 87.2, 0.0), remote=True, health=100, deaths=0, zombies=4502, players=0, score=4502, level=1, steamid=76561198029613876, ip=85.170.46.222, ping=35
            splitted = text.split ( " id=" )
            playerid = int ( splitted [ 1 ].split ( "," ) [ 0 ] )
            playername = text.split ( str ( playerid ) + ", " ) [ 1 ].split ( ", pos=(" ) [ 0 ]
            splitted = text.split ( playername ) [ 1 ].split ( "=" )
            playerposition_x = float ( splitted [ 1 ].split ( "," ) [ 0 ] [ 1: ] )
            playerposition_z = float ( splitted [ 1 ].split ( "," ) [ 1 ] [ 1: ] )
            playerposition_y = float ( splitted [ 1 ].split ( "," ) [ 2 ] [ : -1 ] )
            #rot_x = float ( splitted [ 3 ].split ( "," ) [ 0 ] [ 1: ] )
            #rot_z = float ( splitted [ 3 ].split ( "," ) [ 1 ] [ 1: ] )
            #rot_y = float ( splitted [ 3 ].split ( "," ) [ 2 ] [ : -1 ] )
            playerhealth = int ( splitted [ 4 ].split ( "," ) [ 0 ] )
            playerdeaths = int ( splitted [ 5 ].split ( "," ) [ 0 ] )
            playerzombies = int ( splitted [ 6 ].split ( "," ) [ 0 ] )
            playerkills = int ( splitted [ 7 ].split ( "," ) [ 0 ] )
            playerscore = int ( splitted [ 8 ].split ( "," ) [ 0 ] )
            playersteamid = int ( splitted [ 10 ].split ( "," ) [ 0 ] )
            player_ip = splitted [ 11 ].split ( "," ) [ 0 ]
            country = self.geoip.country_code_by_addr ( player_ip )
        except:
            self.log.error ( "Error during parse_id." )
            return
        
        self.players_info_update ( level = 1,
                                   name = playername,
                                   online = True,
                                   playerid = playerid,
                                   pos_x = playerposition_x,
                                   pos_y = playerposition_y,
                                   pos_z = playerposition_z,
                                   health = playerhealth,
                                   ip = player_ip,
                                   deaths = int ( playerdeaths ),
                                   zombies = int ( playerzombies ),
                                   players = int ( playerkills ),
                                   score = int ( playerscore ),
                                   steamid = playersteamid )

        pickle_file = open ( self.player_info_file, 'wb' )
        pickle.dump ( self.players_info, pickle_file, pickle.HIGHEST_PROTOCOL )

        #self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
    def players_info_update ( self,
                              level,
                              online,
                              playerid,
                              name,
                              pos_x,
                              pos_y,
                              pos_z,
                              health,
                              ip,
                              deaths,
                              zombies,
                              players,
                              score,
                              steamid ):
        
        if playerid in self.players_info.keys ( ):
            self.players_info [ playerid ].ip = ip
            self.players_info [ playerid ].level = level
            self.players_info [ playerid ].name = name
            self.players_info [ playerid ].name_sane = self.sanitize ( name )
            if self.players_info [ playerid ].online == False:
                self.log.debug ( "%s is online." % name )
            self.players_info [ playerid ].online = online
            self.players_info [ playerid ].pos_x = pos_x
            self.players_info [ playerid ].pos_y = pos_y
            self.players_info [ playerid ].pos_z = pos_z

            self.enforce_home_radii ( playerid )
            
            if ( ( abs ( float ( pos_x ) ) > 4400 ) or
                 ( abs ( float ( pos_y ) ) > 4400 ) ):
                if self.players_info [ playerid ].map_limit_beacon == None:
                    self.console ( 'pm %s "you are beyond the 4.4km soft limit. Teleport destination saved."' % ( playerid ) )
                    self.players_info [ playerid ].map_limit_beacon = ( pos_x, pos_y, pos_z + 1 )
                if ( ( abs ( float ( pos_x ) ) > 4500 ) or
                     ( abs ( float ( pos_y ) ) > 4500 ) ):
                    msg = '%s is beyond the 4.5km hard limit. Teleporting back to saved position."'
                    self.say ( msg % ( self.players_info [ playerid ].name_sane ) )
                    if ( abs ( self.players_info [ playerid ].map_limit_beacon [ 0 ] ) > 4500 or
                         abs ( self.players_info [ playerid ].map_limit_beacon [ 1 ] ) > 4500 ):
                        self.say ( "Saved position also beyond hard limit; teleporting to starter base." )
                        self.players_info [ playerid ].map_limit_beacon = ( 1500, 350, 67 + 1 )                    
                    self.teleport ( name,
                                    self.players_info [ playerid ].map_limit_beacon )
                    return
            else:
                self.players_info [ playerid ].map_limit_beacon = None
            
            #self.players_info [ playerid ].rot = rot
            #self.players_info [ playerid ].remote = remote
            self.players_info [ playerid ].health = health
            self.players_info [ playerid ].ip = ip
            self.players_info [ playerid ].deaths = int ( deaths )
            self.players_info [ playerid ].zombies = int ( zombies )
            if int ( players ) > self.players_info [ playerid ].players:
                self.log.info ( "Player %s has killed another player!" % self.players_info [ playerid ].name_sane )
                self.say ( "%s is imprisoned for killing another player." % self.players_info [ playerid ].name_sane )
                self.players_info [ playerid ].players = int ( players )
                for mod in self.framework.mods:
                    if mod.__class__.__name__ == 'prison':
                        mod.named_prisoners.append ( playerid )
                        mod.save_prisoners ( )
            self.players_info [ playerid ].score = int ( score )
            #self.players_info [ playerid ].level = level
            #self.players_info [ playerid ].ip = ip
            #self.players_info [ playerid ].ping = ping
        else:
            new_player_info = player_info ( health = health,
                                            ip = ip,
                                            name = name,
                                            playerid = playerid,
                                            pos_x = pos_x,
                                            pos_y = pos_y,
                                            pos_z = pos_z,
                                            deaths = deaths,
                                            zombies = int ( zombies ),
                                            players = players,
                                            score = score,
                                            level = level,
                                            steamid = steamid )
            self.players_info [ playerid ] = new_player_info
            self.players_info [ playerid ].name_sane = self.sanitize ( name )
            country = self.geoip.country_code_by_addr ( ip )
            #if country in self.framework.preferences.forbidden_countries:
            #    self.say ( "%s is a new [FF0000]prisoner[FFFFFF], and now has an entry in the Gulag database." % self.sanitize ( name ) )
            #else:
            #    self.say ( "%s is a new player, and now has an entry in player database." % self.sanitize ( name ) )

    def command_print_player_info ( self, player_identifier, message ):
        player = self.get_player ( player_identifier )
        if player == None:
            self.say ( "No such player: %s" % str ( player_identifier ) )
            return
        msg = "%s, " % player.name_sane
        msg += self.geoip.country_code_by_addr ( player.ip )
        if player.home != None:
            msg += ", home at %s" % ( str ( player.home ) )
            if self.calculate_distance ( ( player.pos_x, player.pos_y ),
                                         player.home ) < self.preferences.home_radius:
                msg += ", inside"
            else:
                msg += ", outside"
        msg += ", speaks" 
        for language in player.languages_spoken:
            msg += " " + language
        msg += ', translation to %s' % player.language_preferred
        msg += "."
        self.say ( msg )

    def print_players_info ( self, msg_origin, msg_content ):
        for key in self.players_info.keys ( ):
            if self.players_info [ key ].online:
                self.command_print_player_info ( key, msg_content )

    def random_online_player ( self ):
        possibilities = [ ]
        for key in self.players_info.keys ( ):
            if self.players_info [ key ].online == True:
                possibilities.append ( key )
        if possibilities == [ ]:
            return None
        random_index = random.randint ( 0, len ( possibilities ) - 1 )
        return self.get_player ( possibilities [ random_index ] )                
                
    def run ( self ):
        while self.shutdown == False:
            self.log.debug ( "Tick" )
            time.sleep ( self.framework.preferences.loop_wait )
                
    def sanitize ( self, original ):
        result = original.replace ( '"', '_' )
        result = result.replace ( "'", '_' )
        return result
                
    def say ( self, msg = None ):
        """
        TELNET MESSAGING String-Conversion Check for Ascii/Bytes and Send-Message Function
        Because Casting Byte to Byte will fail.
        """
        if isinstance ( msg, str ) == True:
            inputmsg = 'say "' + msg.replace ( '"', ' ' ) + '"' + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = msg.decode('ascii')
            inputmsg = 'say "' + inputmsg.replace ( '"', ' ' ) + '"' + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        self.log.debug ( outputmsg )
        if not self.framework.silence:
            self.telnet_connection.write ( outputmsg )
        else:    
            self.log.info ( "(silenced) %s" % outputmsg )

    def sos ( self, msg_origin, msg_contents ):
        origin = self.get_player ( msg_origin )
        for key in self.players_info.keys ( ):
            if ( self.players_info [ key ].online == True and
                 key != origin.playerid ):
                helper = self.get_player ( key )
                bearings = self.calculate_bearings ( origin, helper )
                msg = 'pm %s "Go %.1fm in direction %d degrees (N is zero ) to help %s if you can!"'
                self.console ( msg % ( helper.name_sane,
                                       bearings [ 0 ],
                                       bearings [ 1 ],
                                       origin.name_sane ) )

    def show_inventory ( self, player ):
        msg = "showinventory " + str ( player )
        self.console ( msg )
        
    def spawn_player_stuff ( self,
                             playerid,
                             stuff ):
        msg = 'se ' + playerid + ' ' + str ( stuff )
        self.log.debug ( msg )
        self.console ( msg )

    def stop ( self ):
        self.shutdown = True
        
    def teleport ( self, player_info, where_to ):
        player = self.get_player ( player_info )
        if player != None:
            msg = 'teleportplayer ' + str ( player.playerid ) + ' '
        else:
            msg = 'teleportplayer ' + str ( player_info ) + ' '
        if isinstance ( where_to, str ):
            msg += where_to
        elif isinstance ( where_to, tuple ):
            msg += str ( int ( where_to [ 0 ] ) ) + " " + \
                   str ( int ( where_to [ 2 ] ) ) + " " + \
                   str ( int ( where_to [ 1 ] ) )
        self.console ( msg )

    def update_players_pickle ( self ):
        import framework
        new_players_info = { }
        for key in self.players_info.keys ( ):
            player = self.get_player ( key )
            if player != None:
                
                new_player = framework.player_info_v2 ( deaths = player.deaths,
                                              health = player.health,
                                              home = player.home,
                                              ip = player.ip,
                                              level = player.level,
                                              name = player.name,
                                              online = player.online,
                                              playerid = player.playerid,
                                              players = player.players,
                                              pos_x = player.pos_x,
                                              pos_y = player.pos_y,
                                              pos_z = player.pos_z,
                                              score = player.score,
                                              steamid = player.steamid,
                                              zombies = player.zombies )
                new_player.home_invasion_beacon = player.home_invasion_beacon
                new_player.home_invitees = player.home_invitees
                new_player.language_preferred = player.language_preferred
                new_player.languages_spoken = player.languages_spoken
                new_player.map_limit_beacon = player.map_limit_beacon
                new_player.name_sane = self.sanitize ( player.name )
                new_player.attributes = player.attributes
                
                # New attribute:
                new_player.camp = None
                
                new_players_info [ key ] = new_player

        self.log.info ( "Creating new player info file." )
        pickle_file = open ( self.player_info_file, 'wb' )
        pickle.dump ( new_players_info, pickle_file, pickle.HIGHEST_PROTOCOL )
        self.log.info ( "Resetting pointer." )
        self.players_info = new_players_info
