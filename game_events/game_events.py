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
        self.__version__ = "0.3.10"
        self.changelog = {
            '0.3.10' : "Fixed death-by-tree picking message at random after picking right one.",
            '0.3.9'  : "Fixed syntax for tree fell event.",
            '0.3.8'  : "Added inheritance tax.",
            '0.3.7'  : "Using smarter method to give taunt when tree-killed.",
            '0.3.6'  : "Use preferences' rank url and message instead of hardcoded values.",
            '0.3.5'  : "Refactor for gt in world_state.",
            '0.3.4'  : "100 kills prize is at least 100 now.",
            '0.3.3'  : "Refactoring 100 kills prize to get it to randomize.",
            '0.3.2'  : "More taunts.",
            '0.3.1'  : "Added events for when player becomes citizen and senator.",
            '0.3.0'  : "Disabled map limitation.",
            '0.2.19' : "Typo in one of the taunts.",
            '0.2.18' : "Making hornet event a little bit more frequent.",
            '0.2.17' : "Calling random.seed before every randint to get different values.",
            '0.2.16' : "Added randomness to cash prize for zeds.",
            '0.2.15' : "Updated message about prize for voting.",
            '0.2.14' : "Taunt",
            '0.2.13' : "Tweaked nest event, fixed coordinates of tree felled.",
            '0.2.12' : "More taunts.",
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
            'player_killed_100_zombies'  : [ ],
            'player_played_one_hour'     : [ ],
            'player_position_changed'    : [ ( self.check_position_triggers,
                                               { } ) ],
            }
        self.tree_kills = { }

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )        

    def stop ( self ):
        self.shutdown = True

    def check_position_triggers ( self, player = None ):
        #self.framework.get_db_lock ( )
        if not player:
            self.log.error ( "player None" )
        # map borders
        #if ( ( abs ( player.pos_x ) > 4400 ) or
        #     ( abs ( player.pos_y ) > 4400 ) ):
        #    if player.map_limit_beacon == None:
        #        self.framework.console.pm ( player,
        #                                    "You are beyond the 4.4km soft limit. Teleport destination saved." )
        #        new_beacon =  self.framework.utils.get_coordinates ( player )
        #        player.map_limit_beacon = copy.copy ( new_beacon )
        #        self.log.info ( "Setting {}.map_limit_beacon to {}".format ( player.name_sane,
        #                                                                     new_beacon ) )
        #    if ( ( abs ( player.pos_x ) > 4500 ) or
        #         ( abs ( player.pos_y ) > 4500 ) ):
        #        msg = '%s is beyond the 4.5km hard limit. Teleporting back to saved position."'
        #        self.log.info ( msg % ( player.name_sane ) )
        #        if ( abs ( player.map_limit_beacon [ 0 ] ) > 4500 or
        #             abs ( player.map_limit_beacon [ 1 ] ) > 4500 ):
        #            self.framework.console.pm ( player, "Your saved position also beyond hard limit; teleporting to starter base." )
        #            player.map_limit_beacon = ( 1500, 350, 67 )                    
        #        self.framework.server.preteleport ( player,
        #                                            player.map_limit_beacon )
        #else:
        #    player.map_limit_beacon = None
        #self.framework.let_db_lock ( )

        if 'sethome' not in self.framework.mods.keys ( ):
            return
        if not self.framework.mods [ 'sethome' ] [ 'reference' ].enabled:
            return

        self.framework.mods [ 'sethome' ] [ 'reference' ].enforce_home ( player )
        
    def day_changed ( self, previous_day ):
        self.log.info ( "day_changed call" )
        # do not continue if mod just came up:
        if ( time.time ( ) - self.framework.load_time ) < 60:
            return
        position = self.framework.rank.current_rank
        self.log.info ( "position = {}".format ( position ) )
        if position != -1:
            self.framework.console.say ( self.framework.preferences.rank_message )
            self.framework.console.say ( self.framework.preferences.rank_url )

        self.log.info ( "Calling shop.increase_stock ( )" )
        if 'shop' in list ( self.framework.mods.keys ( ) ):
            self.framework.mods [ 'shop' ] [ 'reference' ].increase_stock ( )
    
    def hour_changed ( self, previous_hour ):
        # do not continue if mod just came up:
        if ( time.time ( ) - self.framework.load_time ) < 60:
            return

        day = self.framework.world_state.game_server.day
        hour = self.framework.world_state.game_server.hour
        minute = self.framework.world_state.game_server.minute
        self.log.info ( ">>>>>  day %d, %02dh%02d  <<<<<" % ( day, hour, minute ) )
        for player in self.framework.server.get_online_players ( ):
            self.log.info ( self.framework.server.get_player_summary ( player ) )
        self.log.info ( self.framework.world_state.get_game_server_summary ( ) )

    def player_can_propose ( self, player ):
        self.framework.console.say ( "The community looks up to {} for guidance! {} can now propose referendums.".format ( player.name_sane, player.name_sane ) )
        
    def player_can_vote ( self, player ):
        self.framework.console.say ( "The community recognizes {} as one of its voting citizens.".format (
            player.name_sane ) )
        
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
            ( "It was an uneven match, {}. That tree has more kills than you ever will." ),
            #( "{} is quite the tree-hugger!" ),
            ( "{}, the price of femur is really good right now, you don't mind do you?" ),
            ( "{} was hunted down by a vicious sand block." ),
            ( "Again, {}!?" ),
            ( "Another {}-kill and without spending a single arrow." ),
            ( "Don't feel bad, {}. Even the zombies died once." ),
            ( "Ewwww {}, you taste awful! What have you been eating?!" ),
            ( "FATALITY! Server wins! {} loses." ),
            ( "Hahaha I knew that broken leg was gonna do you in, {}!" ),
            ( "Hmmm. I think I can make a base out of {}'s gore blocks." ),
            ( "I want brains, and after eating {}'s, I'm still hungry!" ),
            ( "If you will keep dying that fast, I will start respawning you as a rabbit, {}." ),
            #( "Lemme guess, {}: you learned how to play with Lulu?" ),
            ( "Let's all hope {} lost his backpack to a bug!" ),
            ( "Lol {}, are you role-playing a zombie?" ),
            ( "Muwahaha! The evil lag monster strikes {} again!" ),
            ( "Player stew: one water, one potato and one {}." ),
            #( "Quick everyone! {}'s backpack has two augers!!" ),
            ( "That's not how a log spike is supposed to work, {}." ),
            ( "Told you, {}, those are not teddy bears." ),
            ( "Wow, {} tastes just like chicken!" ),
            #( "{}, you are supposed to stay [523456]behind[FFFFFF] the tree when it falls." ),
            ( "You expect a prize if you read all taunts, {}?" ),
            ( "You shouldn't have eaten so much fast food, {}!" ),
            ]
        player = self.framework.server.get_player ( matches [ 7 ] )
        if player:
            message_number = None
            for key in self.tree_kills.keys ( ):
                for position in player.positions [ : -10 ]:
                    distance = self.framework.utils.calculate_distance ( ( player.pos_x, player.pos_y ),
                                                                         self.tree_kills [ key ] )
                    if distance < 5:
                        message_number = 0
                        break
            self.log.info ( "{} died!".format ( player.name_sane ) )
            if message_number == None:
                message_number = random.randint ( 1, len ( player_died_messages ) - 1 )
            self.framework.console.say ( player_died_messages [ message_number ].format ( player.name_sane ) )
        before_cash = player.cash
        player.cash = round ( 0.9 * player.cash )
        self.framework.console.pm ( player, "You payed {}$ as inheritance tax.".format ( 
                before_cash - player.cash ) )
        
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
        player = self.framework.server.get_player ( int ( player_disconnection_match_group [ 7 ] ) )
        if not player:
            self.log.error ( "Could not get_player from disconnected player's '{}' steamid {}!".format (
                player_disconnection_match_group [ 8 ],
                player_disconnection_match_group [ 7 ] ) )
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

        money_before = player.cash
        random.seed ( time.time ( ) )
        self.framework.server.give_cash ( player, random.randint ( 100, 150 ) )
        self.framework.console.say ( "{} gained {} cash for killing 100 zombies!".format ( player.name_sane,
                                                                                           player.cash -\
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
        self.log.info ( "Tree was felled at ( {}, {} ).".format ( matches [ 0 ], matches [ 2 ] ) )
        now = time.time ( )
        self.tree_kills [ now ] = ( float ( matches [ 0 ] ), float ( matches [ 2 ] ) )
        deletables = [ ]
        for key in self.tree_kills.keys ( ):
            if now - key > 30:
                deletables.add ( key )
        for key in deletables:
            del self.tree_kills [ key ]
        chance_event = random.randint ( 1, 100 )
        self.log.info ( "chance_event = {}".format ( chance_event ) )
        if chance_event < 5:
            self.log.info ( "Small swarm event triggered!" )
            nearest_player = self.framework.server.find_nearest_player_to_position ( ( float ( matches [ 0 ] ),
                                                                                   float ( matches [ 2 ] ) ) )
            self.log.info ( "Nearest {:.1f}m player is {}.".format (
                nearest_player [ 1 ],
                self.framework.server.get_player ( nearest_player [ 0 ] ).name_sane ) )
            self.framework.server.little_swarm ( self.framework.server.get_player ( nearest_player [ 0 ] ), 1 )

