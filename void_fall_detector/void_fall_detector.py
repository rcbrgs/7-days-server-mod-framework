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
        self.framework.server.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
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

            # STARTMOD

            speed = 1

            next_online_players_heights = { }

            self.log.debug ( "self.framework.server.get_online_players ( ) = %s" % str ( self.framework.server.get_online_players ( ) ) )
            for playerid in self.framework.server.get_online_players ( ):
                self.log.debug ( "playerid = %s" % str ( playerid ) )
                player = self.framework.server.get_player ( playerid )
                if player.playerid in online_players_heights.keys ( ):
                    if len ( online_players_heights [ player.playerid ] [ 'height' ] ) == 5:
                        online_players_heights [ playerid ] [ 'height' ] = online_players_heights [ playerid ] [ 'height' ] [ 1 : -1 ]
                        online_players_heights [ playerid ] [ 'x' ] = online_players_heights [ playerid ] [ 'x' ] [ 1 : -1 ]
                        online_players_heights [ playerid ] [ 'y' ] = online_players_heights [ playerid ] [ 'y' ] [ 1 : -1 ]

                    online_players_heights [ playerid ] [ 'x' ].append ( round ( player.pos_x ) )
                    online_players_heights [ playerid ] [ 'y' ].append ( round ( player.pos_y ) )
                    online_players_heights [ playerid ] [ 'height' ].append ( player.pos_z )

                    if len ( online_players_heights [ player.playerid ] [ 'height' ] ) == 5:
                        self.log.debug ( "%s heights = %s." % ( player.name_sane, online_players_heights [ playerid ] [ 'height' ] ) )
                        if not ( online_players_heights [ player.playerid ] [ 'x' ] [ 0 ] == online_players_heights [ player.playerid ] [ 'x' ] [ 1 ] and
                                 online_players_heights [ player.playerid ] [ 'x' ] [ 1 ] == online_players_heights [ player.playerid ] [ 'x' ] [ 2 ] and
                                 online_players_heights [ player.playerid ] [ 'x' ] [ 2 ] == online_players_heights [ player.playerid ] [ 'x' ] [ 3 ] and
                                 online_players_heights [ player.playerid ] [ 'x' ] [ 3 ] == online_players_heights [ player.playerid ] [ 'x' ] [ 4 ] ):
                            continue

                        if not ( online_players_heights [ player.playerid ] [ 'y' ] [ 0 ] == online_players_heights [ player.playerid ] [ 'y' ] [ 1 ] and
                                 online_players_heights [ player.playerid ] [ 'y' ] [ 1 ] == online_players_heights [ player.playerid ] [ 'y' ] [ 2 ] and
                                 online_players_heights [ player.playerid ] [ 'y' ] [ 2 ] == online_players_heights [ player.playerid ] [ 'y' ] [ 3 ] and
                                 online_players_heights [ player.playerid ] [ 'y' ] [ 3 ] == online_players_heights [ player.playerid ] [ 'y' ] [ 4 ] ):
                            continue

                        if ( online_players_heights [ player.playerid ] [ 'height' ] [ 0 ] > online_players_heights [ player.playerid ] [ 'height' ] [ 1 ] + speed * self.framework.preferences.loop_wait and
                             online_players_heights [ player.playerid ] [ 'height' ] [ 1 ] > online_players_heights [ player.playerid ] [ 'height' ] [ 2 ] + speed * self.framework.preferences.loop_wait and
                             online_players_heights [ player.playerid ] [ 'height' ] [ 2 ] > online_players_heights [ player.playerid ] [ 'height' ] [ 3 ] + speed * self.framework.preferences.loop_wait and
                             online_players_heights [ player.playerid ] [ 'height' ] [ 3 ] > online_players_heights [ player.playerid ] [ 'height' ] [ 4 ] + speed * self.framework.preferences.loop_wait ):
                            self.log.info ( "%s heights = %s." % ( player.name_sane, online_players_heights [ playerid ] [ 'height' ] ) )
                            self.framework.server.say ( "Player %s has been falling the last %d seconds." % ( player.name_sane,
                                                                                                              5 * self.framework.preferences.loop_wait ) )
                            if 'last teleport height' not in online_players_heights [ player.playerid ].keys ( ):
                                online_players_heights [ player.playerid ] [ 'last teleport height' ] = player.pos_z
                            destiny_height = max ( ( online_players_heights [ player.playerid ] [ 'last teleport height' ],
                                                     max ( online_players_heights [ player.playerid ] [ 'height' ] ),
                                                     player.pos_z ) ) + self.framework.preferences.teleport_lag_cushion
                            online_players_heights [ player.playerid ] [ 'last teleport height' ] = destiny_height
                            self.framework.server.say ( "Trying to teleport %s to current position at height %.1f." % ( player.name_sane, destiny_height ) )
                            self.framework.server.teleport ( player, ( player.pos_x, player.pos_y, destiny_height ) )
                            
                else:
                    online_players_heights [ player.playerid ] = { 'x' : [ player.pos_x ],
                                                                   'y' : [ player.pos_y ],
                                                                   'height' : [ player.pos_z ] }

            try:
                new_online_players_heights = { }
                for playerid in online_players_heights.keys ( ):
                    player = self.framework.server.get_player ( playerid )
                    if player.online:
                        new_online_players_heights [ player.playerid ] = online_players_heights [ player.playerid ]
                    else:
                        time.sleep ( self.framework.preferences.loop_wait + 1 )
                        if player.online:
                            new_online_players_heights [ player.playerid ] = online_players_heights [ player.playerid ]
                online_players_heights = new_online_players_heights
            except RuntimeError as e:
                self.log.error ( "Handling %s." % str ( e ) )
                continue
            
            # ENDMOD                             
            
            time.sleep ( self.framework.preferences.loop_wait )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
