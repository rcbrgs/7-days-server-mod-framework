import logging
import math
import sys
import threading
import time

class portal ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( "framework.{}".format ( __name__ ) )
        #self.log = logging.getLogger ( __name__ )
        self.__version__ = "0.3.3"
        self.changelog = {
            '0.3.3'  : "Fixed logger.",
            '0.3.2'  : "Fixed check on current portal amount.",
            '0.3.1'  : "Fixed costs and limit being treated as strings.",
            '0.3.0'  : "Added cash_cost, karma_cost, friends_enabled and limit parameters. Recoded to use these new parameters.",
            '0.2.6'  : "Fixed syntax error in go portal to non existing portal",
            '0.2.5'  : "Fixed syntax error when moving portal.",
            '0.2.4'  : "Portal db select updated to new db system.",
            '0.2.3'  : "Fixed set friend logic.",
            '0.2.2'  : "Refactored to use queued select.",
            '0.2.1'  : "Fixed logic for listing friends.",
            '0.2.0'  : "/set friend with no argument will output list of friends.",
            }
        self.framework = framework
        self.shutdown = False
        self.daemon = True

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]
        self.commands = { 'go'         : ( self.command_go,
                                           " /go <destiny> will teleport you to your destiny (a portal or a friend). Costs 1 karma." ),
                          'set friend' : ( self.command_set_friend,
                                           " /set friend <player> marks (or removes) that player as your friend." ),
                          'set portal' : ( self.command_set_portal,
                                           " /set portal <name> will (un)mark your current spot as a portal. Costs 1 karma." ) }

        self.cash_cost = float ( self.framework.preferences.mods [ self.__class__.__name__ ] [ 'cash_cost' ] )
        self.friends_enabled = bool ( self.framework.preferences.mods [ self.__class__.__name__ ] [ 'friends_enabled' ] )
        self.karma_cost = float (  self.framework.preferences.mods [ self.__class__.__name__ ] [ 'karma_cost' ] )
        self.limit = int ( self.framework.preferences.mods [ self.__class__.__name__ ] [ 'limit' ] )
        
    def __del__ ( self ):
        self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                     self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        while not self.shutdown:
            time.sleep ( self.framework.preferences.loop_wait )
            if not self.enabled:
                continue

            # STARTMOD

            # ENDMOD                             

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def command_go ( self, origin, message ):
        player = self.framework.server.get_player ( origin )
        if not player:
            self.log.warning ( "Invalid player for command_go." )
            return

        # Check player has enough karma
        if player.karma < self.karma_cost:
            self.framework.console.pm ( player, "You need {} karma to teleport!".format ( self.karma_cost ) )
            return
        
        # Check player has enough cash
        if player.cash < self.cash_cost:
            self.framework.console.pm ( player, "You need {} cash to teleport!".format ( self.cash_cost ) )
            return

        if player.steamid in self.framework.mods [ 'prison' ] [ 'reference' ].detainees:
            self.framework.console.say ( "Denying request of prisoner %s to /go somewhere." % 
                                         player.name_sane )
            return

        destiny = message [ len ( "/go " ) : ]
        if destiny == '':
            records = [ ]
            self.framework.database.select_record ( "portals", { 'steamid' : player.steamid },
                                                    records )
            self.framework.utils.wait_not_empty ( records )
            for entry in records:
                try:
                    possible_destinations += ", {}".format ( entry [ 'name' ] )
                except UnboundLocalError:
                    possible_destinations = "{}".format ( entry [ 'name' ] )
            self.framework.console.pm ( player, "You could go to: {}".format ( possible_destinations ) )
            return
        self.log.info ( "No portal with identifier '{}'.".format ( destiny ) )
        destiny_player = self.framework.server.get_player ( destiny )
        if destiny_player:
            if not self.friends_enabled:
                self.framework.server.pm ( player, "The teleport-to-friend function is disabled!" )
                return
            friendship_records = [ ]
            self.framework.database.select_record ( "friends", { "steamid" : destiny_player.steamid,
                                                                 "friend"  : player.steamid }, 
                                                    friendship_records )
            self.framework.utils.wait_not_empty ( friendship_records )
            self.log.info ( "friendship_records = '{}'.".format ( friendship_records ) )
            friendship = None
            if friendship_records:
                friendship = friendship_records [ 0 ]

            if not friendship:
                self.framework.console.pm ( player, "%s must first invite you!" % ( destiny_player.name_sane ) )
                return
            
            if destiny_player.online:
                self.framework.server.preteleport ( player, ( destiny_player.pos_x, 
                                                              destiny_player.pos_y, 
                                                              destiny_player.pos_z ) )
                self.framework.server.give_karma ( player, self.karma_cost )
                self.framework.console.pm ( player, "You spent {} karma to go to {:s}.".format (
                        self.karma_cost, destiny_player.name_sane ) )
            return

        portal_record = [ ]
        self.framework.database.select_record ( "portals", { 'steamid' : player.steamid,
                                                             'name' : destiny },
                                                portal_record )
        self.framework.utils.wait_not_empty ( portal_record )
        portal_record = portal_record [ 0 ]
        if not portal_record:
            self.framework.console.pm ( player, "You have no portal with name '{}'.".format ( destiny ) )
            return
        self.framework.server.preteleport ( player, ( portal_record [ 'position_x' ],
                                                      portal_record [ 'position_y' ],
                                                      portal_record [ 'position_z' ] ) )
        player.cash -= self.cash_cost
        player.karma -= self.karma_cost
        self.framework.console.pm ( player, "You spent {}$+{}k to teleport to '{}'.".format ( self.cash_cost, self.karma_cost, destiny ) )

    def command_set_friend ( self, msg_origin, msg_contents ):
        player = self.framework.server.get_player ( msg_origin )
        if not player:
            self.log.warning ( "Invalid player for command_set_friend." )
            return

        if not self.friends_enabled:
            self.framework.server.pm ( player, "Portal friendships are disabled!" )
            return

        if player.karma < 1:
            self.framework.console.pm ( player, "You need 1 karma to invite!" )
            return
        invitee_string = msg_contents [ len ( "/set friend " ) : ]
        if invitee_string == "":
            self.report_friends ( player )
            return
        invitee = self.framework.server.get_player ( msg_contents [ len ( "/set friend " ) : ] )
        if not invitee:
            self.framework.console.pm ( player, "I do not know any player named '{}'.".format ( 
                    msg_contents [ len ( "/set friend " ) : ] ) )
            return
        friendship = [ ]
        self.framework.database.select_record ( "friends", { 'steamid' : player.steamid,
                                                             'friend'  : invitee.steamid },
                                                friendship )
        self.framework.utils.wait_not_empty ( friendship )
        if friendship [ 0 ] != None:
            self.framework.database.delete_record ( "friends", { 'steamid' : player.steamid,
                                                                 'friend' : invitee.steamid } )
            self.framework.console.pm ( player, "{} is no longer one of your friends.".format ( invitee.name_sane ) )
            self.framework.console.pm ( invitee, "You are no longer a friend of {}.".format ( player.name_sane ) )
        else:
            self.framework.database.insert_record ( "friends", { 'steamid' : player.steamid,
                                                                 'friend' : invitee.steamid } )
            self.framework.console.pm ( player, "{} is now one of your friends.".format ( invitee.name_sane ) )
            self.framework.console.pm ( invitee, "You are now a friend of {}.".format ( player.name_sane ) )
        self.framework.world_state.update_friendships ( )

    def command_set_portal ( self, msg_origin, msg_contents ):
        player = self.framework.server.get_player ( msg_origin )
        if not player:
            self.log.warning ( "Invalid player for command set portal." )
            return
        if player.cash < self.cash_cost:
            self.framework.console.pm ( player, "You need 1 karma to set a portal!" )
            return
        if player.karma < self.karma_cost:
            self.framework.console.pm ( player, "You need 1 karma to set a portal!" )
            return
        pos = self.framework.utils.get_coordinates ( player ) 
        name = msg_contents [ len ( "/set portal " ) : ]
        if name == "":
            self.framework.console.pm ( player, "You need to give a name to your portal!" )
            return
        portal_record = [ ]
        self.framework.database.select_record ( "portals", { 'steamid' : player.steamid,
                                                             'name' : name },
                                                portal_record )
        self.framework.utils.wait_not_empty ( portal_record )
        portal_record = portal_record [ 0 ]
        if portal_record:
            self.framework.database.delete_record ( "portals", { 'steamid' : player.steamid,
                                                                 'name' : name } )
            if ( portal_record [ 'position_x' ] == pos [ 0 ] and
                 portal_record [ 'position_y' ] == pos [ 1 ] and
                 portal_record [ 'position_z' ] == pos [ 2 ] ):
                self.framework.console.pm ( player, "You spent {}$+{}k to remove portal '{}'.".format (
                    self.cash_cost, self.karma_cost, name ) )
                player.cash -= self.cash_cost
                player.karma -= self.karma_cost
                return
            else:
                self.framework.database.insert_record ( "portals", { 'steamid' : player.steamid,
                                                                     'name' : name,
                                                                     'position_x' : round ( pos [ 0 ] ),
                                                                     'position_y' : round ( pos [ 1 ] ),
                                                                     'position_z' : round ( pos [ 2 ] ) } )
                self.framework.console.pm ( 
                    player, 
                    "You spent {}$+{}k to move a portal named '{}' to your position.".format (
                        self.cash_cost, self.karma_cost, name ) )
                player.cash -= self.cash_cost
                player.karma -= self.karma_cost
                return

        num_portals_record = [ ]
        self.framework.database.select_record ( "portals", { "steamid" : player.steamid }, num_portals_record )
        self.framework.utils.wait_not_empty ( num_portals_record )
        num_portals = len ( num_portals_record )
        self.log.info ( "{} has {} portals on database ( num_portal_record = {} ).".format ( player.name_sane, num_portals, num_portals_record ) )
        if num_portals >= self.limit:
            self.framework.console.pm ( player, "Portal creation [DD5555]aborted[FFFFFF]. You have reached the limit for portals. Either move your portal (creating a new one with the same name as an existing one) or delete one ('recreating' the portal deletes it)." )
            return

        self.framework.database.insert_record ( "portals", { 'steamid' : player.steamid,
                                                             'name' : name,
                                                             'position_x' : round ( pos [ 0 ] ),
                                                             'position_y' : round ( pos [ 1 ] ),
                                                             'position_z' : round ( pos [ 2 ] ) } )
        self.framework.console.pm ( player, 
                                    "You spent {}$+{}k to set a portal named '{}' at your position.".format (
                self.cash_cost, self.karma_cost, name ) )
        player.cash -= self.cash_cost
        player.karma -= self.karma_cost

    def report_friends ( self, player ):
        reported_friends = [ ]
        self.framework.database.select_record ( "friends", { 'steamid' : player.steamid },
                                                reported_friends )
        self.framework.utils.wait_not_empty ( reported_friends )
        if not reported_friends:
            msg = "You have no friends :("
        else:
            for friendship in reported_friends:
                friend = self.framework.server.get_player ( int ( friendship [ 'friend' ] ) )
                try:
                    msg += ", {}".format ( friend.name_sane )
                except UnboundLocalError:
                    msg = "Your friends are: {}".format ( friend.name_sane )
            msg += "."
        self.framework.console.pm ( player, msg )
        
             
                                                                          
