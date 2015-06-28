import framework
import logging
import sys
import threading
import time

class void_fall_detector ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.1.1"
        self.changelog = {
            '0.1.2' : "Diminished speed threshold and number of measurements to detect fall.",
            '0.1.1' : "Made detector try a second time if player is marked offline." }
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]

        # To have a new command for players to use, it must be placed in the dict below.
        # The commented example adds the command "/suicide" and have the mod run the function "kill_player ( )".
        # All player chat commands receive two strings as arguments. The first contains the player name (unsanitized) and the second contains the string typed by the player (also unsanitized).
        self.commands = {
            # 'suicide' : ( self.kill_player, " /suicide will kill your character." )
        }

    def __del__ ( self ):
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

        online_players_heights = { }
        
        while ( self.shutdown == False ):           
            #time.sleep ( self.framework.preferences.loop_wait )
            custom_wait = 0.1
            time.sleep ( custom_wait )
            if not self.enabled:
                continue

            # STARTMOD

            speed = 10
            height_measurements = 2

            next_online_players_heights = { }

            self.log.debug ( "self.framework.server.get_online_players ( ) = %s" % str ( self.framework.server.get_online_players ( ) ) )
            for player in self.framework.server.get_online_players ( ):
                self.log.debug ( "player = %s" % str ( player.name_sane ) )
                if player.steamid in online_players_heights.keys ( ):
                    if len ( online_players_heights [ player.steamid ] [ 'height' ] ) == height_measurements:
                        online_players_heights [ player.steamid ] [ 'height' ] = online_players_heights [ player.steamid ] [ 'height' ] [ 1 : -1 ]
                        online_players_heights [ player.steamid ] [ 'x' ] = online_players_heights [ player.steamid ] [ 'x' ] [ 1 : -1 ]
                        online_players_heights [ player.steamid ] [ 'y' ] = online_players_heights [ player.steamid ] [ 'y' ] [ 1 : -1 ]

                    online_players_heights [ player.steamid ] [ 'x' ].append ( round ( player.pos_x ) )
                    online_players_heights [ player.steamid ] [ 'y' ].append ( round ( player.pos_y ) )
                    online_players_heights [ player.steamid ] [ 'height' ].append ( player.pos_z )

                    if len ( online_players_heights [ player.steamid ] [ 'height' ] ) == height_measurements:
                        self.log.debug ( "%s heights = %s." % ( player.name_sane, online_players_heights [ player.steamid ] [ 'height' ] ) )
                        if not ( online_players_heights [ player.steamid ] [ 'x' ] [ 0 ] == online_players_heights [ player.steamid ] [ 'x' ] [ 1 ] ):
                            continue

                        if not ( online_players_heights [ player.steamid ] [ 'y' ] [ 0 ] == online_players_heights [ player.steamid ] [ 'y' ] [ 1 ] ):
                            continue
                        self.log.debug ( "%s heights = %s." % ( player.name_sane, online_players_heights [ player.steamid ] [ 'height' ] ) )
                        if ( online_players_heights [ player.steamid ] [ 'height' ] [ 0 ] > online_players_heights [ player.steamid ] [ 'height' ] [ 1 ] + speed * custom_wait ):
                            self.log.info ( "%s heights = %s." % ( player.name_sane, online_players_heights [ player.steamid ] [ 'height' ] ) )
                            self.framework.console.say ( "Player %s has been falling the last %d seconds." % ( player.name_sane,
                                                                                                              height_measurements * custom_wait ) )
                            if 'last teleport height' not in online_players_heights [ player.steamid ].keys ( ):
                                online_players_heights [ player.steamid ] [ 'last teleport height' ] = player.pos_z
                            destiny_height = max ( ( online_players_heights [ player.steamid ] [ 'last teleport height' ],
                                                     max ( online_players_heights [ player.steamid ] [ 'height' ] ),
                                                     player.pos_z ) ) + self.framework.preferences.teleport_lag_cushion
                            online_players_heights [ player.steamid ] [ 'last teleport height' ] = destiny_height
                            self.framework.console.say ( "Trying to teleport %s to current position at height %.1f." % ( player.name_sane, destiny_height ) )
                            self.framework.server.teleport ( player, ( player.pos_x, player.pos_y, destiny_height ) )
                            
                else:
                    online_players_heights [ player.steamid ] = { 'x' : [ player.pos_x ],
                                                                   'y' : [ player.pos_y ],
                                                                   'height' : [ player.pos_z ] }

            try:
                new_online_players_heights = { }
                for player.steamid in online_players_heights.keys ( ):
                    player = self.framework.server.get_player ( player.steamid )
                    if player.online:
                        new_online_players_heights [ player.steamid ] = online_players_heights [ player.steamid ]
                    else:
                        time.sleep ( self.framework.preferences.loop_wait + 1 )
                        if player.online:
                            new_online_players_heights [ player.steamid ] = online_players_heights [ player.steamid ]
                online_players_heights = new_online_players_heights
            except RuntimeError as e:
                self.log.error ( "Handling %s." % str ( e ) )
                continue
            
            # ENDMOD                             

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
