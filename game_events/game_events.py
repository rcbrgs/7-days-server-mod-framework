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
        self.log = logging.getLogger ( __name__ )
        self.__version__ = "0.2.11"
        self.changelog = {
            '0.2.11' : "1% chance felling a tree will trigger a hornet mini horde.",
            '0.2.10' : "Skeleton event for tree felling.",
            '0.2.9'  : "More taunts. Added event for increase shop stock.",
            '0.2.8'  : "Added processing for player creation event. More taunts",
            '0.2.7'  : "Increased prize for votes.",
            '0.2.6'  : "More taunts.",
            '0.2.5'  : "Use __name__ logger. More player taunts upon death.",
            '0.2.4'  : "Log player and gameserver info every game hour. +player detected. Fixed map beacon not being saved." ,
            '0.2.3'  : "Added hook for player connection. Added daily vote message.",
            '0.2.2'  : "Added hook for triggering on player position change.",
            '0.2.1'  : "Refactored time accounting to be more efficient.",
            '0.2.0'  : "Killing 100 zombies gives some cash to player.",
            '0.1.1'  : "Karma gain now PMs player.",
            '0.1.0'  : "Initial version." }
        
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
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )        

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
        #position_file = open ( "pos.txt", "r" )
        position = self.framework.rank.current_rank
        if position != -1:
            self.framework.console.say ( "Please vote for our server on http://7daystodie-servers.com/server/14698. We are currently # {} on the rank! Also, you gain 100$+1k per vote.".format ( position ) )

        if 'shop' in list ( self.framework.mods.keys ( ) ):
            self.framework.mods [ 'shop' ] [ 'reference' ].increase_stock ( )
    
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

    def player_created ( self, matches ):
        playerid = int ( matches [ 7 ] )
        self.log.debug ( "Player with playerid = {} created.".format ( playerid ) )
        #player = self.framework.server.get_player ( playerid )
        #if player:
        #    self.log.info ( "Player name is {}, position is ({}, {}, {}).".format (
        #        player.name, player.pos_x, player.pos_y, player.pos_z ) )
        #else:
        #    self.log.info ( "Player is not in db yet." )
        
    def player_died ( self, matches ):
        player_died_messages = [
            ( "{} is quite the tree-hugger!" ),
            ( "Again, {}!?" ),
            ( "Another {}-kill and without spending a single arrow." ),
            ( "Don't feel bad, {}. Even the zombies died once." ),
            ( "Ewwww {}, you taste awful! What have you been eating?!" ),
            ( "Hahaha I knew that broken leg was gonna do you in, {}!" ),
            ( "Hmmm. I think I can make a base out of {}'s gore blocks." ),
            ( "I want brains, and after eating {}'s, I'm still hungry!" ),
            ( "If you will keep dying that fast, I will start respawning you as a rabbit, {}." ),
            ( "Lemme guess, {}: you learned how to play with Lulu?" ),
            ( "Lol {}, are you role-playing a zombie?" ),
            ( "Player stew: one water, one potato and one {}." ),
            ( "Quick everyone! {}'s backpack has two augers!!" ),
            ( "That's not how a log spike is supposed to work, {}." ),
            ( "Told you, {}, those are not teddy bears." ),
            ( "Wow, {} tastes just like chicken!" ),
            ( "{}, you are supposed to stay [123456]behind[FFFFFF] the tree when it falls." ),
            ( "You expect a prize if you read all taunts, {}?" ),
            ]
        player = self.framework.server.get_player ( matches [ 7 ] )
        if player:
            self.log.info ( "{} died!".format ( player.name_sane ) )
            message_number = random.randint ( 0, len ( player_died_messages ) - 1 )
            self.framework.console.say ( player_died_messages [ message_number ].format ( player.name_sane ) )
        
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

        money_before = player.cash
        for callback in self.registered_callbacks [ 'player_killed_100_zombies' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player' ] = player
            function ( **kwargs )

        self.framework.console.pm ( player, "You gained {} cash for killing 100 zombies!".format ( player.cash -\
                                                                                                   money_before ) )

    def player_left ( self, matches ):
        player = self.framework.server.get_player ( matches [ 7 ] )
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

    def tree_felled ( self, matches ):
        self.log.info ( "Tree was felled at ( {}, {} ).".format ( matches [ 0 ], matches [ 3 ] ) )
        if random.randint ( 1, 100 ) == 1:
            self.log.info ( "Small swarm event triggered!" )
            nearest_player = self.framework.server.find_nearest_player_to_position ( ( float ( matches [ 0 ] ),
                                                                                   float ( matches [ 3 ] ) ) )
            self.log.info ( "Nearest {:.1f}m player is {}.".format (
                nearest_player [ 1 ],
                self.framework.server.get_player ( nearest_player [ 0 ] ) ) )
            self.framework.server.little_swarm ( self.framework.server.get_player ( nearest_player [ 0 ] ), 1 )

