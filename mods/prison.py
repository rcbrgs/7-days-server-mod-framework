import framework
import logging
import pickle
import pygeoip
import sys
import threading
import time

class prison ( threading.Thread ):
    def __init__ ( self, framework):
        super ( prison, self ).__init__ ( )
        self.log = framework.log
        self.log_level = logging.INFO
        self.daemon = True        
        self.__version__ = '0.4.0'
        self.changelog = {
            '0.4.0' : "Automatically ban players from griefer countries, instead of putting in jail.",
            '0.3.8' : "Show error and ignore if ip in home range.",
            '0.3.7' : "Fixed prison not using right field to calculate release time.",
            '0.3.6' : "Fixed chomping on /free.",
            '0.3.5' : "Fixed impriosn chomping last letter of message.",
            '0.3.4' : "Fixed commands comping last letter of the command string.",
            '0.3.3' : "Made prison release code more robust; did not find the bug with previous version, though.",
            '0.3.2' : "Added preteleporters, enabled explain command.",
            '0.3.1' : "Fixed explanation system for prison.",
            '0.3.0' : "Added explanations to playerkills.",
            '0.2.2' : "Added changelog." }
        self.framework = framework
        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]
        self.shutdown = False
        
        self.commands = { 
            "explain"  : ( self.command_explain, " /explain 'username' <something> will add something as a playerkill explanation to the user (Server only)." ),
            "free"     : ( self.command_free,     " /free <playername> frees a prisoner (Server only)." ),
            "imprison" : ( self.command_imprison, " /imprison <playername> adds a player to jail (Server only)." ),
            "prison"   : ( self.command_prison,   " /prison teleports you to prison." ) 
            }

        self.prison_center = ( -96, -919, 81 )
        self.prison_radius = 100
        self.geoip = pygeoip.GeoIP ( self.framework.preferences.geoip_file, pygeoip.MEMORY_CACHE )

        self.detainees = [ ]
        self.invaders = { }
        self.prisoners_file = self.framework.preferences.mods [ 'prison' ] [ 'prisoners_file' ]

        file_found = True
        try:
            pickle_file = open ( self.prisoners_file, 'rb' )
        except FileNotFoundError as e:
            self.log.error ( e )
            self.log.error ( "Creating new prisoners file." )
            file_found = False

        if ( file_found ):
            self.named_prisoners = pickle.load ( pickle_file )
        else:
            self.named_prisoners = [ ]                                     

    def __del__ ( self ):
        self.shutdown = True
        self.stop ( )
            
    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        # this function will be called as a thread from the framework.

        # to call the base framework functions, use the self.framework object.
        # Example: to give player that has id 123 one jar of alcohol:
        # self.framework.server.give_player_stuff ( 123, "grainAlcohol", 1 )

        # To access the current player data, use the players_info dict
        # from framework. Example: to print each players health:
        # for key in self.framework.server.players_info ( keys ):
        #print ( "player %s has %d health." % ( self.framework.server.players_info [ key ].name,
        #                                       self.framework.server.players_info [ key ].health )

        # place your mod code inside the while loop, between the START MOD and END MOD comments.
        # this ensures that your code is run the right number of times.

        while ( self.shutdown == False ):
            self.log.setLevel ( self.log_level )
            self.log.debug ( "prison while" )
            
            # STARTMOD
            if not self.enabled:
                time.sleep ( self.framework.preferences.loop_wait )
                continue
                            
            online_players = self.framework.server.get_online_players ( )
            self.framework.get_db_lock ( )
            self.detainees = [ ]
            try:
                for player in online_players:
                    self.log.debug ( "Checking %s" % player.name_sane )
                    if ( player.steamid in self.named_prisoners ):
                        self.detainees.append ( player.steamid )
                        #self.detain ( player.steamid )
                        continue
                    self.log.debug ( "not named" )
                    country = self.geoip.country_code_by_addr ( player.ip ) # is this in double?
                    if country == '':
                        self.log.error ( "{} has ip in home range: {}!".format ( player.name_sane, player.ip ) )
                    elif ( country in self.framework.preferences.forbidden_countries ):
                        self.log.debug ( "Player %s is a country prisoner from %s." %
                                         ( player.name_sane, country ) )
                        self.detainees.append ( player.steamid )
                        self.framework.console.send ( "ban add {} 1 week".format ( player.steamid ) )
                        self.framework.console.say ( "Banning player {} for 1 week. Country code: {}.".format ( player.name_sane, country ) )
                        continue
                    continue # this will bypass all prison code, except country bans.
                    self.log.debug ( "not forbidden" )
                    num_pkills = player.players
                    if isinstance ( num_pkills, int ):
                        if ( num_pkills > 0 ):
                            self.log.debug ( "prisoner? %s" % player.name_sane )
                            if isinstance ( player.player_kills_explanations, list ):
                                self.log.debug ( "explanations '{}' is list of len {}".format (
                                    player.player_kills_explanations,
                                    len ( player.player_kills_explanations ) ) )
                                if ( len ( player.player_kills_explanations ) == num_pkills ):
                                    continue
                                self.log.debug ( "%s has %d pkills and %d explanations!" %
                                                 ( player.name_sane,
                                                   num_pkills,
                                                   len ( player.player_kills_explanations ) ) )
                                #self.detainees.append ( player.steamid )
                            else:
                                self.log.debug ( "{} has {} pkills and no explanations!".format (
                                    player.name_sane, player.players ) )
                            self.detainees.append ( player.steamid )
                            #self.detain ( player.steamid )
                            continue
                    self.log.debug ( "not pkills" )

                    invaders_list = list ( self.invaders.keys ( ) )
                    if player.steamid in invaders_list:
                        if 'timestamp_release' in self.invaders [ player.steamid ].keys ( ):
                            if self.invaders [ player.steamid ] [ 'timestamp_release' ] < time.time ( ):
                                self.framework.console.say ( "{} is free to leave the prison.".format ( player.name_sane ) )
                                del ( self.invaders [ player.steamid ] )
                                continue
                        else:
                            self.detainees.append ( player.steamid )
                    
                for key in self.detainees:
                    self.enforce_prison ( self.framework.server.get_player ( key ) )
                    
                self.framework.let_db_lock ( )
                                
            except RuntimeError as e:
                self.log.error ( "Error during prison check: %s." % str ( e ) )
                continue
            
            # ENDMOD                             

            # this mod is somewhat heavy so lets not run it often
            time.sleep ( self.framework.preferences.loop_wait * 10 )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def command_explain ( self, origin, message ):
        if origin != "Server":
            self.framework.console.say ( 'Only the Server can issue that command.' )
            return

        arguments = message [ 6 : ] 
        self.log.debug ( "arguments == '%s'" % arguments )

        splitted_args = arguments.split ( "'" )
        if len ( splitted_args ) != 3:
            self.log.info ( "Syntax: /explain 'player' reason" )
        
        prisoner = self.framework.server.get_player ( splitted_args [ 1 ] )
        if prisoner == None:
            self.framework.console.say ( "No player by that name!" )
            return
        
        explanations = prisoner.player_kills_explanations
        if not isinstance ( explanations, list ):
            prisoner.player_kills_explanations = [ ]
        prisoner.player_kills_explanations.append ( splitted_args [ 2 ] )

    def command_free ( self, origin, message ):
        if origin != "Server":
            self.framework.console.say ( 'Only the Server can issue that command.' )
            return

        arguments = message [ 6 : ] 
        self.log.debug ( "arguments == '%s'" % arguments )

        prisoner = self.framework.server.get_player ( arguments )
        if prisoner == None:
            self.framework.console.say ( "No player by that name!" )
            return

        if prisoner.playerid not in self.named_prisoners:
            self.framework.console.say ( "Player is not imprisoned!" )
            return

        self.named_prisoners.remove ( prisoner.playerid )
        self.log.info ( "self.named_prisoners = %s" % str ( self.named_prisoners ) )
        self.save_prisoners ( )
        self.framework.console.say ( "Prisoner %s is now free!!" % prisoner.name_sane )

    def command_imprison ( self, origin, message ):
        if origin != "Server":
            self.framework.console.say ( 'Only the Server can issue that command.' )
            return

        self.log.debug ( "message [ 10 : ] == '%s'" % message [ 10 : ] )
        prisoner = self.framework.server.get_player ( message [ 10 : ] )

        if prisoner == None:
            self.framework.console.say ( "No player by that name!" )
            return

        if prisoner.playerid in self.named_prisoners:
            self.framework.console.say ( "Player is already imprisoned!" )
            return

        self.named_prisoners.append ( prisoner.steamid )
        self.framework.console.say ( "Player %s is now imprisoned!!" % prisoner.name_sane )

    def command_prison ( self, origin, message ):
        player = self.framework.server.get_player ( origin )
        if not player:
            return
        self.log.info ( "%s visiting prison." % player.name_sane )
        self.framework.server.preteleport ( player, ( self.prison_center [ 0 ],
                                                      self.prison_center [ 1 ],
                                                      self.prison_center [ 2 ] ) )
        
        
    def enforce_prison ( self, player ):
        if player.steamid not in self.detainees:
            self.detainees.append ( player.steamid )
        distance = self.framework.utils.calculate_distance ( ( player.pos_x, player.pos_y ),
                                                             ( self.prison_center [ 0 ],
                                                               self.prison_center [ 1 ] ) )
        if distance > self.prison_radius:
            self.framework.console.say ( "Prisoner %s is escaping! Teleporting back." %
                                         ( player.name_sane  ) )
            self.log.info  ( "Prisoner %s is escaping! Teleporting back (%f)." %
                              ( player.name_sane, distance ) )
            self.framework.server.preteleport ( player, self.prison_center )

    def save_prisoners ( self ):
        self.log.info ( "Saving prisoners file." )
        pickle_file = open ( self.prisoners_file, 'wb' )
        pickle.dump ( self.named_prisoners, pickle_file, pickle.HIGHEST_PROTOCOL )
        
    def stop ( self ):
        self.save_prisoners ( )
        self.shutdown = True
