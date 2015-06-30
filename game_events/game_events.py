import copy
import framework
import logging
import random
import sys
import threading
import time

class game_events ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.2.4"
        self.changelog = {
            '0.2.4' : "Log player and gameserver info every game hour. +player detected. Fixed map beacon not being saved.",
            '0.2.3' : "Added hook for player connection. Added daily vote message.",
            '0.2.2' : "Added hook for triggering on player position change.",
            '0.2.1' : "Refactored time accounting to be more efficient.",
            '0.2.0' : "Killing 100 zombies gives some cash to player.",
            '0.1.1' : "Karma gain now PMs player.",
            '0.1.0' : "Initial version." }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.registered_callbacks = {
            'player_connected'           : [ ],
            'player_detected'            : [ ],
            'player_killed_100_zombies'  : [ ( self.framework.server.give_cash,
                                               { 'amount' : random.randint ( 50, 150 ) } ),
                                             ],
            'player_played_one_hour'     : [ ],
            'player_position_changed'    : [ ( self.check_position_triggers,
                                               { } ) ],
            }

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )        

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def check_position_triggers ( self, player = None ):
        self.framework.get_db_lock ( )
        if not player:
            self.log.error ( "player None" )
        # map borders
        if ( ( abs ( player.pos_x ) > 4400 ) or
             ( abs ( player.pos_y ) > 4400 ) ):
            if player.map_limit_beacon == None:
                self.framework.console.pm ( player,
                                            "You are beyond the 4.4km soft limit. Teleport destination saved." )
                new_beacon =  self.framework.utils.get_coordinates ( player )
                player.map_limit_beacon = copy.copy ( new_beacon )
                self.log.info ( "Setting {}.map_limit_beacon to {}".format ( player.name_sane,
                                                                             new_beacon ) )
            if ( ( abs ( player.pos_x ) > 4500 ) or
                 ( abs ( player.pos_y ) > 4500 ) ):
                msg = '%s is beyond the 4.5km hard limit. Teleporting back to saved position."'
                self.log.info ( msg % ( player.name_sane ) )
                if ( abs ( player.map_limit_beacon [ 0 ] ) > 4500 or
                     abs ( player.map_limit_beacon [ 1 ] ) > 4500 ):
                    self.framework.console.pm ( player, "Your saved position also beyond hard limit; teleporting to starter base." )
                    player.map_limit_beacon = ( 1500, 350, 67 )                    
                self.framework.server.preteleport ( player,
                                                    player.map_limit_beacon )
        else:
            player.map_limit_beacon = None
        self.framework.let_db_lock ( )

        if 'sethome' not in self.framework.mods.keys ( ):
            return
        if not self.framework.mods [ 'sethome' ] [ 'reference' ].enabled:
            return

        self.framework.mods [ 'sethome' ] [ 'reference' ].enforce_home ( player )
        
    def day_changed ( self, previous_day ):
        # do not continue if mod just came up:
        if ( time.time ( ) - self.framework.load_time ) < 60:
            return
        # Which position are we? Save it to pos.txt
        position_file = open ( "pos.txt", "r" )
        position = int (position_file.readline ().strip() )
        self.log.info ( "Rank = {}".format ( position ) )
        self.framework.console.say ( "If you like this server, vote for it on http://7daystodie-servers.com/server/14698. We are currently # {}!".format ( position ) )
    
    def hour_changed ( self, previous_hour ):
        # do not continue if mod just came up:
        if ( time.time ( ) - self.framework.load_time ) < 60:
            return

        day = self.framework.server.game_server.day
        hour = self.framework.server.game_server.hour
        minute = self.framework.server.game_server.minute
        self.log.info ( ">>>>>  day %d, %02dh%02d  <<<<<" % ( day, hour, minute ) )
        for player in self.framework.server.get_online_players ( ):
            self.log.info ( self.framework.server.get_player_summary ( player ) )
        self.log.info ( self.framework.server.get_game_server_summary ( ) )

    def player_changed_name ( self, player ):
        self.log.info ( "Player {} changed name from {}.".format ( player.name_sane,
                                                                   player.attributes [ 'old names' ] ) )
        old_names = ""
        for name in player.attributes [ 'old names' ]:
            if old_names == "":
                old_names += name
            else:
                old_names += ", or " + name
        self.framework.console.say ( "[AAAAAA]ATTENTION[FFFFFF] everyone!!!! {} does not want to be called {}, anymore!".format ( player.name_sane, old_names ) )
        
    def player_connected ( self, player_connection_match_group ):
        self.log.info ( "player_connected" )
        player = self.framework.server.get_player ( player_connection_match_group [ 9 ] )
        if not player:
            self.log.info ( "A player new to the mod connected." )
            return
        for callback in self.registered_callbacks [ 'player_connected' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player' ] = player
            function ( **kwargs )

        self.framework.console.pm ( player, "Welcome back {}!".format ( player.name_sane ) )
        self.log.info ( "{} connected.".format ( player.name_sane ) )

    def player_died ( self, matches ):
        player = self.framework.server.get_player ( matches [ 7 ] )
        if player:
            self.log.info ( "{} died!".format ( player.name_sane ) )
            self.framework.console.say ( "{} brainzzzzzzz good but few".format ( player.name_sane ) )
        
    def player_denied ( self, player_denied_match_group ):
        quoted_player_name = player_denied_match_group [ 1 ]
        sane_player_name = self.framework.server.sanitize ( quoted_player_name [ 1 : -1 ] )
        self.framework.console.say ( "Blocked banned player {} from connecting to our server.".format (
            sane_player_name ) )
        
    def player_detected ( self, player ):
        for callback in self.registered_callbacks [ 'player_detected' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player' ] = player
            function ( **kwargs )

        #self.framework.console.pm ( player, "Welcome back {}!".format ( player.name_sane ) )
        self.log.debug ( "{} detected.".format ( player.name_sane ) )

    def player_disconnected ( self, player_disconnection_match_group ):
        player = self.framework.server.get_player ( player_disconnection_match_group [ 8 ] )
        if not player:
            self.log.error ( "Could not get_player from disconnected player's name {}!".format (
                player_disconnection_match_group [ 8 ] ) )
            return
        player.online = False
        self.log.info ( "{:s} disconnected.".format ( player.name_sane ) )

    def player_kill ( self, matches ):
        murderer = self.framework.server.get_player ( matches [ 7 ] )
        victim   = self.framework.server.get_player ( matches [ 8 ] )
        self.log.info ( "{} killed {}!".format ( murderer.name_sane, victim.name_sane ) )
        
    def player_killed_100_zombies ( self, player ):
        if not isinstance ( player, framework.player_info.player_info_v5 ):
            self.log.warning ( "calling p killd 100 zeds with id" )
            player = self.framework.server.get_player ( player )
            
        for callback in self.registered_callbacks [ 'player_killed_100_zombies' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player' ] = player
            function ( **kwargs )

        self.framework.console.say ( "{} gained cash for killing zombies!".format ( player.name_sane ) )

    def player_left ( self, matches ):
        player = self.framework.server.get_player ( matches [ 0 ] )
        if player:
            player.online = False
            self.log.info ( "{} left the game.".format ( player.name ) )
        
    def player_played_one_hour ( self, player ):
        for callback in self.registered_callbacks [ 'player_played_one_hour' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player' ] = player
            function ( **kwargs )

        self.framework.server.give_karma ( player, 1 )
        self.framework.console.pm ( player, "You gained 1 karma for being online 1h!" )
        
    def player_position_changed ( self, player ):
        for callback in self.registered_callbacks [ 'player_position_changed' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player' ] = player
            function ( **kwargs )

