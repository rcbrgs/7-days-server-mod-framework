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
        self.log = logging.getLogger ( "framework.{}".format ( __name__ ) )
        self.log_level = logging.INFO
        self.__version__ = "0.2.0"
        self.changelog = {
            '0.2.0' : "SQL db synchronizes every 1 hour.",
            }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.mod_preferences = self.framework.preferences.mods [ self.__class__.__name__ ]
        self.enabled = self.mod_preferences [ 'enabled' ]

        self.commands = {
            }
        self.help_items = {
            "fear" : "Fear is a measure of how much you avoid zombies. As it increases, your chances of a zombie appearing by your side increase."
            }

        self.db = { }
        self.sql_syncronization_timestamp = time.time ( )

    def __del__ ( self ):
        self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):
            self.log.setLevel ( self.log_level )
            time.sleep ( self.framework.preferences.loop_wait )
            if not self.enabled:
                continue

            # STARTMOD
            now = time.time ( )
            if now - self.sql_syncronization_timestamp > 3600:
                self.log.info ( "Syncronizing SQL database." )
                self.syncronize_sql ( )
                self.sql_syncronization_timestamp = now

            # get list of online players
            online_players = self.framework.server.get_online_players ( )
            # for each player, get zombie distances, until sure which "zone" player is
            for player in online_players:
                now = time.time ( )
                self.syncronize_db ( player )
                current_info = self.db [ player.steamid ]
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
                new_fear = current_info [ 'fear' ]
                new_fear_timestamp = current_info [ 'latest_fear_timestamp' ]
                if not new_fear_timestamp:
                    new_fear_timestamp = 0
                old_state = current_info [ 'latest_state' ]
                if old_state == zone:
                    old_timestamp = float ( current_info [ 'latest_state_timestamp' ] )
                    if now - new_fear_timestamp > 60 * float ( self.mod_preferences [ 'factor' ] ):
                        self.log.debug ( "{} accumulating {}.".format ( player.name_sane, zone ) )
                        interval = now - old_timestamp 
                        if interval < 10:
                            if zone == "fear":
                                new_fear += interval
                            if zone == "courage":
                                new_fear -= interval * float ( self.mod_preferences [ 'factor' ] )
                            self.log.debug ( "{} fear changed from {:.1f} to {:.1f}.".format ( 
                                    player.name_sane, current_info [ 'fear' ], new_fear ) )
                        else:
                            self.log.debug ( "{} sentiment interval too long ({:.1f}s), ignoring.".format ( 
                                    player.name_sane, interval ) )
                    else:
                        self.log.debug ( "{} not accumulating sentiment ({:.0f}s since state change).".format ( 
                                player.name_sane, now - new_fear_timestamp ) )
                elif zone == "fear":
                    self.log.info ( "setting new fear timestamp" )
                    new_fear_timestamp = now

                new_fear = max ( 0, new_fear )
                old_check = 0
                if current_info [ 'latest_check_timestamp' ]:
                    old_check = float ( current_info [ 'latest_check_timestamp' ] )
                new_check = old_check

                self.log.debug ( "{} is {:.1f}m away from {} ({}, {:.1f}).".format ( 
                        player.name_sane, distance, entity_type, zone, new_fear ) )

                # check for event triggers
                # spawn zed?
                trigger = False
                if now - old_check > 120:
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
                                "{} fear is now so intense it might attract zombies.".format ( 
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
                self.log.debug ( "{} new_info = {}".format ( player.name_sane, new_info ) )
                self.db [ player.steamid ] = new_info
            
            # ENDMOD                             

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
        while ( self.is_alive ( ) ):
            time.sleep ( 1 )
            self.log.warning ( "Sleeping until self is not alive anymore." )
        self.syncronize_sql ( )

    def list ( self ):
        for steamid in self.db.keys ( ):
            self.log.info ( "{} fear = {}.".format ( 
                    self.framework.server.get_player ( steamid ).name_sane, self.db [ steamid ] [ 'fear' ] ) )

    def syncronize_db ( self, player ):
        if player.steamid in list ( self.db.keys ( ) ):
            return
        select = [ ]
        self.framework.database.select_record ( "fear", { "steamid" : player.steamid }, select )
        self.framework.utils.wait_not_empty ( select )
        self.log.debug ( "select = {}".format ( select ) )
        current_info = select [ 0 ]
        if current_info == None:
            self.log.debug ( "Player {} has not an entry in fear db.".format ( player.name_sane ) )
            info = {
                "steamid"                : player.steamid,
                "fear"                   : 0,
                "latest_check_timestamp" : 0,
                "latest_fear_timestamp"  : 0,
                "latest_fear_warning"    : 0,
                "latest_state"           : "courage",
                "latest_state_timestamp" : time.time ( )
                }
            self.framework.database.insert_record ( "fear", info )
            current_info = info
        self.db [ player.steamid ] = current_info

    def syncronize_sql ( self ):
        for steamid in self.db.keys ( ):
            self.framework.database.update_record ( "fear", self.db [ steamid ] )

    def trigger_random_event ( self, player, fear ):
        random.seed ( time.time ( ) )
        dice = random.randint ( 0, 100 )
        fear_factor = fear / ( 60 * float ( self.mod_preferences [ 'factor' ] ) )
        if fear_factor > dice:
            self.log.info ( "trigger_random_event: fear_factor {} > dice {}.".format ( fear_factor, dice ) )
            self.framework.console.say ( "{} craps in own pants out of fear, attracting zombies!".format ( player.name_sane ) )
            self.framework.console.se ( player, 'animalRabbit', 2 )
            #self.framework.console.se ( player, 'zombiecrawler', 2 )
            return True
        return False
