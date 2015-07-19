import framework
import logging
import math
import random
import sys
import threading
import time

class fear ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.1.15"
        self.changelog = {
            '0.1.15' : "Fixed exception when no entities around.",
            '0.1.14' : "Tweaked timings to get more balanced effect.",
            '0.1.13' : "Bump down fear upon triggered event.",
            '0.1.12' : "Adjusted event to be more often and have more effect.",
            '0.1.11' : "Added help_items.",
            '0.1.10' : "Final touches on warnings.",
            '0.1.9' : "Tweaked logs and warnings.",
            '0.1.8' : "Fixed math.floor instead of floor.",
            '0.1.7' : "Refactored to use non recursive get_nearest_zombie.",
            '0.1.6' : "Added fear / courage messages.",
            '0.1.5' : "Fixes to inertia.",
            '0.1.4' : "Added inertia to fear accumulation.",
            '0.1.3' : "Less logging.",
            '0.1.2' : "Fixed logging not shown beacuse syntax used is for another type of mod.",
            '0.1.1' : "Fear must be divided by factor before trigger comparison.",
            '0.1.0' : "Initial version." }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.mod_preferences = self.framework.preferences.mods [ self.__class__.__name__ ]
        self.enabled = self.mod_preferences [ 'enabled' ]

        # To have a new command for players to use, it must be placed in the dict below.
        # The commented example adds the command "/suicide" and have the mod run the function "kill_player ( )".
        # All player chat commands receive two strings as arguments. The first contains the player name (unsanitized) and the second contains the string typed by the player (also unsanitized).
        self.commands = {
            # 'suicide' : ( self.kill_player, " /suicide will kill your character." )
        }
        self.help_items = {
            "fear" : "Fear is a measure of how much you avoid zombies. As it increases, your chances of a zombie appearing by your side increase."
            }

    def __del__ ( self ):
        self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )
            if not self.enabled:
                continue

            # STARTMOD

            # get list of online players
            online_players = self.framework.server.get_online_players ( )
            # for each player, get zombie distances, until sure which "zone" player is
            for player in online_players:
                now = time.time ( )
                distance, entity_id, entity_type = self.framework.server.get_nearest_zombie ( player )
                if not distance:
                    distance = 100 * float ( self.mod_preferences [ 'distance_maximum' ] )
                # save each players' zone info
                zone = 'neutral'
                if distance > float ( self.mod_preferences [ 'distance_maximum' ] ):
                    zone = 'fear'
                if distance < float ( self.mod_preferences [ 'distance_minimum' ] ):
                    zone = 'courage'
                # update accumulators
                current_info = self.framework.database.select_record ( "fear", { "steamid" : player.steamid } )
                self.log.debug ( "current_info = {}".format ( current_info ) )
                if not current_info:
                    info = {
                        "steamid"                : player.steamid,
                        "fear"                   : 0,
                        "latest_check_timestamp" : 0,
                        "latest_fear_timestamp"  : 0,
                        "latest_fear_warning"    : 0,
                        "latest_state"           : zone,
                        "latest_state_timestamp" : now
                        }
                    self.framework.database.insert_record ( "fear", info )
                    continue
                self.log.debug ( "current_info = {}.".format ( current_info ) )
                new_fear = current_info [ 'fear' ]
                new_fear_timestamp = current_info [ 'latest_fear_timestamp' ]
                if not new_fear_timestamp:
                    new_fear_timestamp = 0
                old_state = current_info [ 'latest_state' ]
                if old_state == zone:
                    old_timestamp = float ( current_info [ 'latest_state_timestamp' ] )
                    if now - new_fear_timestamp > 60 * float ( self.mod_preferences [ 'factor' ] ):
                        self.log.debug ( "accumulating {}".format ( zone ) )
                        interval = now - old_timestamp 
                        if interval < 10:
                            if zone == "fear":
                                new_fear += interval
                            if zone == "courage":
                                new_fear -= interval
                elif zone == "fear":
                    self.log.info ( "setting new fear timestamp" )
                    new_fear_timestamp = now

                new_fear = max ( 0, new_fear )
                old_check = 0
                if current_info [ 'latest_check_timestamp' ]:
                    old_check = float ( current_info [ 'latest_check_timestamp' ] )
                new_check = old_check

                self.log.info ( "{} is {:.1f}m away from {} ({}, {:.1f}).".format ( 
                        player.name_sane, distance, entity_type, zone, new_fear ) )

                # check for event triggers
                # spawn zed?
                trigger = False
                if now - old_check > 60:
                    new_check = now
                    if new_fear > 540 + 60 * float ( self.mod_preferences [ 'factor' ] ):
                        # trigger a random event
                        trigger = self.trigger_random_event ( player, new_fear )
                if trigger:
                    new_fear -= new_fear % 60
                    
                # warn about fear?
                old_fear_warning = current_info [ 'latest_fear_warning' ]
                if not old_fear_warning:
                    old_fear_warning = 0
                new_fear_warning = old_fear_warning
                fear_warning = math.floor ( new_fear / ( 480 + 60 * float ( self.mod_preferences [ 'factor' ] ) ) )
                if fear_warning > old_fear_warning:
                    if new_fear > fear_warning + 0.1:
                        new_fear_warning = fear_warning
                        if new_fear_warning == 1:
                            self.framework.console.say ( 
                                "{} fear is now so intense it might attracts zombies.".format ( 
                                    player.name_sane ) )
                        else:
                            self.framework.console.say ( "{} smells of fear even more than before.".format ( 
                                    player.name_sane ) )

                if fear_warning < old_fear_warning:
                    if new_fear > fear_warning - 0.1:
                        new_fear_warning = fear_warning
                        if new_fear_warning == 0:
                            self.framework.console.say ( 
                                "{} courage is now so intense no zombies are attracted.".format ( 
                                    player.name_sane ) )
                        else:
                            self.framework.console.say ( "{} smells of fear a little less than before.".format ( 
                                    player.name_sane ) )


                new_info = {
                    "steamid"                : player.steamid,
                    "fear"                   : new_fear,
                    "latest_check_timestamp" : new_check,
                    "latest_fear_timestamp"  : new_fear_timestamp,
                    "latest_fear_warning"    : new_fear_warning,
                    "latest_state"           : zone,
                    "latest_state_timestamp" : now
                    }
                self.framework.database.update_record ( "fear", new_info )
            
            # ENDMOD                             
            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def trigger_random_event ( self, player, fear ):
        random.seed ( time.time ( ) )
        dice = random.randint ( 0, 100 )
        fear_factor = fear / ( 60 * float ( self.mod_preferences [ 'factor' ] ) )
        if fear_factor > dice:
            self.log.info ( "trigger_random_event: fear_factor {} > dice {}.".format ( fear_factor, dice ) )
            self.framework.console.say ( "{} craps in own pants out of fear, attracting zombies!".format ( player.name_sane ) )
            #self.framework.console.se ( player, 'animalRabbit', 2 )
            self.framework.console.se ( player, 'zombiecrawler', 2 )
            return True
        return False
