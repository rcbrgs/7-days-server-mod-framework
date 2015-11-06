import framework
import logging
import math
import sys
import threading
import time

class sethome ( threading.Thread ):
    def __init__ ( self, framework_instance ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( "framework.{}".format ( __name__ ) )
        self.log_level = logging.INFO
        self.__version__ = "0.3.9"
        self.changelog = {
            '0.3.9'  : "Repetitive invasions now result in X minutes of ban for X invasions beyond 5.",
            '0.3.8'  : "Avoid multiple warning player when multiple claims from same player are near.",
            '0.3.7'  : "Removed political message from imprisonment event.",
            '0.3.6'  : "Added pro-democracy chat when repeated invasions occur.",
            '0.3.5'  : "Fixed new syntax for radius preference.",
            '0.3.4'  : "Using better logging system.",
            '0.3.3'  : "Silencing default logs.",
            '0.3.2'  : "Refactored db call for claimstone effect.",
            '0.3.1'  : "Refactored for queued select record.",
            '0.3.0'  : "Disabled functionality that is now provided through mod portal.",
            }
        
        self.framework = framework_instance
        self.shutdown = False
        self.daemon = True

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]
        self.commands = { 
            }
        
    def __del__ ( self ):
        self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
            
        count = 0
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )

            if not self.enabled:
                continue

            self.log.setLevel ( self.log_level )

            # STARTMOD

            if count % 50 == 0:
                self.framework.world_state.update_friendships ( )

            try:
                self.enforce_claimstone_area ( )
            except Exception as e:
                self.log.error ( self.framework.utils.output_exception ( e ) )

            count += 1
            
            # ENDMOD                             

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def enforce_claimstone_area ( self ):
        self.log.debug ( "enforce_claimstone_area" )
        
        claimstones = self.framework.world_state.get_claimstones ( )
        self.framework.world_state.let_claimstones ( )

        online_players = self.framework.server.get_online_players ( )
        for player in online_players:
            effect = False
            warn = False
            dirty = False
            self.log.debug ( "enforce_claimstone_area, player {}".format ( player.name_sane ) )            
            for claimstone_player in claimstones.keys ( ):
                if claimstone_player == player.steamid:
                    self.log.debug ( "Own claimstone" )
                    continue
                self.log.debug ( "claim is from another player" )

                for claimstone in claimstones [ claimstone_player ]:
                    self.log.debug ( "checking a claim from player {}".format ( claimstone_player ) )
                    effect, warn = self.enforce_claimstone_effect ( claimstone_player, claimstone, player )
                    if ( effect or warn ):
                        dirty = True
                        self.log.debug ( "dirty True" )
                    if effect:
                        self.log.debug ( "effect True" )
                        self.claimstone_enforce_trigger_prison ( player,
                                                                 self.framework.server.get_player (
                                                                     claimstone_player ) )
                        break
                    if isinstance ( player.home_invasion_beacon, dict ):
                        self.log.debug ( "there is a dict beacon" )
                        if ( not warn and
                             claimstone in player.home_invasion_beacon.keys ( ) ):
                            self.log.info ( "del claim {} from {} beacons".format ( claimstone,
                                                                                    player.name_sane ) )
                            del ( player.home_invasion_beacon [ claimstone ] )
                if effect:
                    break        
            if not dirty:
                self.log.debug ( "Nothing to do." )
                if player.home_invasion_beacon != { }:
                    self.log.info ( "Resetting {}'s beacons.".format ( player.name_sane ) )
                    player.home_invasion_beacon = { }
                    
    def enforce_claimstone_effect ( self, claimstone_key, claimstone, player ):
        self.log.debug ( "enforce claimstone {} to {}".format (
            self.framework.server.get_player ( claimstone_key ).name_sane, player.name_sane ) )
        claim_length = 15.0
        distance = self.framework.utils.calculate_distance (
            self.framework.utils.get_coordinates ( player ), claimstone )
        if distance < 100:
            self.log.debug ( "distance = {}".format ( distance ) )
            if self.check_claim_is_from_friend ( player, claimstone_key ):
                return False, False
        if ( distance < claim_length ):
            self.log.info ( "{} is to be teleported away from {}".format ( player.name_sane,
                                                                           claimstone ) )
            self.claimstone_enforce_teleport ( player, claimstone_key, claimstone )
            return True, True
        if ( distance < float ( self.framework.preferences.mods [ 'sethome' ] [ 'home_radius' ] ) ):
            self.log.debug ( "warn" )
            self.claimstone_enforce_warning ( player, claimstone_key, claimstone )
            self.log.debug ( "{} near ({:.0f}) {}'s claim.".format (
                player.name_sane, distance, self.framework.server.get_player ( claimstone_key ) ) )
            return False, True
        return False, False

    def check_claim_is_from_friend ( self, player, claimstone_player ):
        #record = [ ]
        #self.framework.database.select_record ( "friends", { 'steamid' : claimstone_player,
        #                                                     'friend'  : player.steamid },
        #                                        record )
        #self.log.info ( "waiting db to check claim is from friend" )
        #self.framework.utils.wait_not_empty ( record )
        #self.log.info ( "db returned {}".format ( record ) )
        #if record [ 0 ] != None:
        #    self.log.debug ( "Player is friend of claimstone_player." )
        #    return True
        #self.log.info ( "claim is not from a friend" )
        #return False
        if claimstone_player in list ( self.framework.world_state.friendships.keys ( ) ):
            if player.steamid in self.framework.world_state.friendships [ claimstone_player ]:
                return True
        return False
                                    
    def claimstone_enforce_teleport ( self, player, other_steamid, claim ):
        other = self.framework.server.get_player ( other_steamid )
        if not player.home_invasion_beacon:
            player.home_invasion_beacon = { }
        if claim not in player.home_invasion_beacon.keys ( ):
            player.home_invasion_beacon [ claim ] = self.framework.mods [ 'chat_commands' ] [ 'reference' ].starterbase
        if not isinstance ( player.latest_teleport, dict ):
            player.latest_teleport = { }
        if 'timestamp' in player.latest_teleport.keys ( ):
            if time.time ( ) - player.latest_teleport [ 'timestamp' ] < 30:
                self.log.info ( "Prevented claimstone tp enforce due to teleport cooldown." )
                return
        message = "{} is teleported by {}'s claimstone! ({:.0f}m)".format (
            player.name_sane, other.name_sane,
            self.framework.utils.calculate_distance ( self.framework.utils.get_coordinates ( player ),
                                                      claim ) )
        
        self.framework.console.say ( message )
        self.log.info ( message )
        self.framework.server.preteleport ( player, player.home_invasion_beacon [ claim ] )

    def claimstone_enforce_trigger_prison ( self, player, victim ):
        if player.home_invasions == None:
            player.home_invasions = { }

        now = time.time ( )
        invasion_timestamps = list ( player.home_invasions.keys ( ) )
        num_invasions_before = len ( list ( player.home_invasions.keys ( ) ) )
        old_invasions = [ ]
        new_invasion = True
        for timestamp in invasion_timestamps:
            if now - timestamp < 60:
                new_invasion = False
            if now - timestamp > 24 * 3600:
                old_invasions.append ( timestamp )    
                        
        if new_invasion:
            player.home_invasions [ now ] = victim.steamid

        for timestamp in old_invasions:
            self.log.info ( "Removing old invasion from {}'s history.".format (
                player.name_sane ) )
            del ( player.home_invasions [ timestamp ] )
            
        num_invasions = 0
        num_invasions = len ( list ( player.home_invasions.keys ( ) ) )

        if num_invasions > num_invasions_before:
            self.framework.console.say ( "{} invaded {} bases in the last real 24h!".format (
                player.name_sane, num_invasions ) )
                
            if num_invasions > 5:
                self.framework.mods [ 'prison' ] [ 'reference' ].invaders [ player.steamid ] = {
                    'timestamp_release' : time.time ( ) + 60 * num_invasions }
                self.framework.console.say ( "{} is to be banned for {} minutes, for repetitive attempted invasions.".format ( player.name_sane, num_invasions ) ) 
                self.framework.console.send ( "ban add {} {} minutes \"{} minutes ban for base invasions.\"".format ( player.steamid, num_invasions, num_invasions ) )
                

    def claimstone_enforce_warning ( self, player, other_steamid, claim ):
        """
        If player is near claim, and has not been warned about the protected player, warn him.
        """
        other = self.framework.server.get_player ( other_steamid )
        distance = self.framework.utils.calculate_distance ( ( player.pos_x, player.pos_y, player.pos_z ),
                                                             ( claim [ 0 ], claim [ 1 ], claim [ 2 ] ) )
        if not isinstance ( player.home_invasion_beacon, dict ):
            player.home_invasion_beacon = { }    

        message = "You are too near {}'s claimstone ({:.0f}m)!".format ( other.name_sane, distance )
        if claim not in player.home_invasion_beacon.keys ( ):
            self.log.info ( "claim {} added to {}'s beacons.".format (
                claim, player.name_sane ) )
            player.home_invasion_beacon [ claim ] = ( player.pos_x, player.pos_y, player.pos_z )

        # avoid warning when player has already been warned about other, closer, claims.
        closer_claim = claim
        closer_distance = distance
        for beacon_key in player.home_invasion_beacon.keys ( ):
            beacon_distance = self.framework.utils.calculate_distance ( 
                ( player.pos_x, player.pos_y, player.pos_z ),
                ( beacon_key ) )
            if closer_distance > beacon_distance:
                closer_distance = beacon_distance
                closer_claim = beacon_key
        if closer_claim != claim:
            self.log.info ( "Not warning {} about another {}'s claim ({:.1f}m).".format (
                    player.name_sane, other.name_sane, distance ) )
            return

        self.framework.console.pm ( player, message, can_fail = True )
