import copy
import framework
import inspect
import logging
import threading
import time

class game_server_info ( object ):
    def __init__ ( self ):
        self.day = 0
        self.hour = 0
        self.mem = ( { }, 0 )
        self.minute = 0
        self.time = ( 0, 0, 0 )

class world_state ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.__version__ = '0.4.15'
        self.changelog = {
            '0.4.15' : "Fixed logic for claimstone update.",
            '0.4.14' : "Fixes to get claimstones to update correctly.",
            '0.4.13' : "Using local copy of buffer to avoi dict change exceptions during claimstone update.",
            '0.4.12' : "Fixed error falsely reported on lock claimstones.",
            '0.4.11' : "Fixed si string on process si.",
            '0.4.10' : "Refactored to use command guard for si. Time threshold 600 -> 60.",
            '0.4.9' : "Refactore le_lag for simplicity.",
            '0.4.8' : "Added more logging to decide_le.",
            '0.4.7' : "gale summary now display lag info.",
            '0.4.6' : "Changed inventory threhsold from 6 to 600 seconds to avoid sell all inventory bug.",
            '0.4.5' : "Added 60s to min le lag.",
            '0.4.4' : "Handler for exception on possible race condition.",
            '0.4.3' : "Tweaked gt lag.",
            '0.4.2' : "Tweaked le_lag and lp_lag calculations and default values.",
            '0.4.1' : "Refactored le and lp lags to be more inertial on their adjustment.",
            '0.4.0' : "Moved entity info to here.",
            }
        self.daemon = True
        self.framework = framework
        self.shutdown = False
        
        self.claimstones = { }
        self.claimstones_buffer = { }
        self.claimstones_buffer_player = ( )
        self.claimstones_buffer_total = 0
                                      
        self.claimstones_lock = { 'callee'    : None,
                                  'timeout'   : 10,
                                  'timestamp' : None }

        self.friendships = { }
        self.game_server = game_server_info ( )

        self.inventory = { }
        self.inventory_lock = { 'callee'    : None,
                                'timeout'   : 10,
                                'timestamp' : None }
        self.inventory_wrong_spawns = [ ]

        now = time.time ( )
        self.llp_timestamp = time.time ( ) - 540
        self.le_timestamp = now
        
        # game time
        self.gt_timestamp = now
        self.gt_queue = [ ]
        self.gt_queue_lock = { 'callee'    : None,
                               'timeout'   : 10,
                               'timestamp' : None }
        self.latest_gt_call = 0
        self.gt_lag = 10

        # le
        self.entities = { }
        self.le_queue = [ ]
        self.le_queue_lock = { 'callee'    : None,
                               'timeout'   : 10,
                               'timestamp' : None }
        self.latest_le_call = 0
        self.le_lag = 20

        # list players
        self.players = { }
        self.lp_queue = [ ]
        self.lp_queue_lock = { 'callee'    : None,
                               'timeout'   : 10,
                               'timestamp' : None }
        self.latest_lp_call = 0
        self.lp_lag = 5

    def run ( self ):
        while not self.shutdown:
            time.sleep ( 0.01 )

            if len ( self.lp_queue ) > 0:
                self.dequeue_lp ( )
            else:
                self.prune_players ( )
                self.decide_lp ( )

            if len ( self.le_queue ) > 0:
                self.dequeue_le ( )
            else:
                self.prune_entities ( )
                self.decide_le ( )

            self.decide_gt ( )
            self.decide_llp ( )
            #self.update_claimstones ( )

    def stop ( self ):
        self.shutdown = True
            
    def buffer_claimstones ( self, match ):
        """
        Output parsed as being relative to claimstones ends here.
        """
        self.log.debug ( "buffer_claimstones ( '{}' )".format ( match ) )
        if len ( match ) == 1:
            self.log.debug ( "total" )
            if self.claimstones_buffer_total != 0:
                self.log.error ( "Next llp total before parsing old one!" )
            self.claimstones_buffer_total = int ( match [ 0 ] )
            self.unbuffer_claimstones ( )
            return
        if len ( match ) == 2:
            self.log.debug ( "player" )
            if self.claimstones_buffer_player != ( ):
                self.log.error ( "Next player claimstones listed before parsing all of current." )
                self.log.error ( "bufferplayer = {} match = {}".format ( str ( self.claimstones_buffer_player ),
                                                                         str ( match ) ) )
                return
            self.claimstones_buffer_player = ( int ( match [ 0 ] ), int ( match [ 1 ] ) )
            return
        if len ( match ) == 3:
            self.log.debug ( "claim" )
            if self.claimstones_buffer_player == ( ):
                self.log.error ( "Claimstone coords received for None player (match = {}).".format ( match ) )
                return
            steamid = self.claimstones_buffer_player [ 0 ]
            amount  = self.claimstones_buffer_player [ 1 ]
            claim = ( int ( match [ 0 ] ),
                      int ( match [ 2 ] ),
                      int ( match [ 1 ] ) )
            if steamid in self.claimstones_buffer.keys ( ):
                self.claimstones_buffer [ steamid ].append ( claim )
            else:
                self.claimstones_buffer [ steamid ] = [ claim ]
            self.log.debug ( "Added claim {} to player {} in buffer.".format ( claim,
                                                                              steamid ) )
            if amount > 1:
                self.claimstones_buffer_player = ( steamid, amount - 1 )
            else:
                self.claimstones_buffer_player = ( )

    def unbuffer_claimstones ( self ):
        """
        Should only be called when a "total X claimstone" output is buffered.
        """
        count = 0
        for steamid in self.claimstones_buffer.keys ( ):
            for claim in self.claimstones_buffer [ steamid ]:
                count += 1
        if count != self.claimstones_buffer_total:
            self.log.error ( "Claimstones total and count differ." )
            return

        deletable_players = [ ]
        deletable_stones  = [ ]
        places = self.framework.mods [ "place_protection" ] [ "reference" ].places
        for steamid in self.claimstones_buffer.keys ( ):
            player = self.framework.server.get_player ( steamid )
            if not player:
                self.log.info ( "Unknown player {}".format ( steamid ) )
                deletable_players.append ( steamid )
                continue
            for claim in self.claimstones_buffer [ steamid ]:
                for place_key in places.keys ( ):
                    if self.framework.utils.calculate_distance ( places [ place_key ] [ 0 ],
                                                                 claim ) < places [ place_key ] [ 1 ]:
                        if ( steamid, claim ) not in deletable_stones:
                            deletable_stones.append ( ( steamid, claim ) )
                            self.log.debug ( "Removing claim because of place protection" )
        for steamid in deletable_players:
            del ( self.claimstones_buffer [ steamid ] )
        for stone in deletable_stones:
            if stone [ 0 ] in self.claimstones_buffer.keys ( ):
                if stone [ 1 ] in self.claimstones_buffer [ stone [ 0 ] ]:
                    self.claimstones_buffer [ stone [ 0 ] ].remove ( stone [ 1 ] )

        self.log.debug ( "buffer b4 update = '{}'".format ( self.claimstones_buffer ) )
        self.update_claimstones ( )

    def update_claimstones ( self ):
        self.log.info ( "Updating current claimstones data with buffer." )
        claimstones = self.claimstones_buffer
        self.log.info ( "buffer = '{}'".format ( claimstones ) )

        events = [ ]
        for steamid in claimstones.keys ( ):
            self.log.debug ( "steamid = {}".format ( steamid ) )
            player = self.framework.server.get_player ( steamid )
            if not player:
                self.log.info ( "Unknown player {}".format ( steamid ) )

            if player.steamid not in list ( self.claimstones.keys ( ) ):
                self.claimstones [ steamid ] = claimstones [ steamid ]
                #events.append ( ( self.framework.game_events.player_set_claimstones,
                #                  ( steamid, self.claimstones_buffer [ steamid ] ) ) )
            else:
                self.log.debug ( "Player in claimstones dict." )
                for claim in claimstones [ steamid ]:
                    self.log.debug ( "considering claim {}".format ( claim ) )
                    if claim not in self.claimstones [ steamid ]:
                        self.log.info ( "claim append" )
                        self.claimstones [ steamid ].append ( claim )
                        #events.append ( ( self.framework.game_events.player_added_claimstone,
                        #                  ( steamid, claim ) ) )
                for claim in self.claimstones [ steamid ]:
                    if claim not in claimstones [ steamid ]:
                        self.log.info ( "claim remove" )
                        self.claimstones [ steamid ].remove ( claim )
                        #events.append ( ( self.framework.game_events.player_removed_claimstone,
                        #                  ( steamid, claim ) ) )
        
        self.let_claimstones ( )
        
        self.claimstones_buffer = { }
        self.claimstones_buffer_total = 0

        for event in events:
            event [ 0 ] ( *event [ 1 ] )

    def update_friendships ( self ):
        self.friendships = { }
        records = [ ]
        self.framework.database.select_record ( "friends", { '1' : "1" }, records )
        self.framework.utils.wait_not_empty ( records )
        for record in records:
            steamid = record [ 'steamid' ]
            friend  = record [ 'friend'  ]
            try:
                self.friendships [ steamid ].append ( friend )
            except KeyError:
                self.friendships [ steamid ] = [ friend ]

    def obtain_inventory ( self, player ):
        pass
            
    # API
    
    def get_claimstones ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        now = time.time ( )
        
        while ( self.claimstones_lock [ 'callee' ] ):
            if ( now - self.claimstones_lock [ 'timestamp' ] > self.claimstones_lock [ 'timeout' ] ):
                break
            time.sleep ( 0.1 )
              
        self.claimstones_lock [ 'callee'    ] = callee_function
        self.claimstones_lock [ 'timestamp' ] = now

        self.log.debug ( "get_claimstones returning" )
        return self.claimstones

    def let_claimstones ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        if ( self.claimstones_lock [ 'callee' ] != callee_function and
             self.claimstones_lock [ 'callee' ] != None ):
            self.log.error ( "Claimstones lock being freed by another function '{}' than callee '{}'!".format (
                    callee_function, self.claimstones_lock [ 'callee' ] ) )
        self.claimstones_lock [ 'callee'    ] = None
        self.claimstones_lock [ 'timestamp' ] = None

    def blocking_get_inventory ( self, player ):
        timestamp = time.time ( )
        self.get_inventory ( )
        self.request_inventory ( player )
        while self.inventory [ 'checking' ]:
            self.log.info ( "Waiting for si to complete..." )
            time.sleep ( 2 )
            if time.time ( ) - timestamp > 60:
                break
        inventory = self.inventory
        self.let_inventory ( )
        return inventory

    def display_game_server ( self ):
        print ( self.get_game_server_summary ( ) )
        
    def get_game_server_summary ( self ):
        mi = self.game_server.mem [ 0 ]
        if 'time' not in mi.keys ( ):
            return
        staleness = time.time ( ) - self.game_server.mem [ 1 ]
        msg = "{:.1f}s {:s}m {:s}/{:s}MB {:s}chu {:s}cgo {:s}p/{:s}z/{:s}i/{:s}({:s})e ".format (
            staleness,
            str ( mi [ 'time' ] ), str ( mi [ 'heap' ] ), str ( mi [ 'max' ] ), str ( mi [ 'chunks' ] ),
            str ( mi [ 'cgo' ] ), str ( mi [ 'players' ] ), str ( mi [ 'zombies' ] ), str ( mi [ 'items' ] ),
            str ( mi [ 'entities_1' ] ), str ( mi [ 'entities_2' ] ) ) 

        msg += "le_lag {:.1f}, lp_lag {:.1f}, gt_lag {:.1f}.".format ( self.le_lag, self.lp_lag, self.gt_lag )
        return msg
                
    # /API
        
    def buffer_shop_item ( self, matches ):
        self.log.info ( matches )
        pos_x = float ( matches [ 10 ] )
        pos_y = float ( matches [ 12 ] )
        pos_z = float ( matches [ 11 ] )
        self.log.info ( "Wrong spawn item at ({} {} {}).".format ( pos_x, pos_y, pos_z ) )
        self.inventory_wrong_spawns.append ( ( pos_x, pos_y, pos_z ) )

    def get_inventory ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        now = time.time ( )
        
        while ( self.inventory_lock [ 'callee' ] ):
            if ( now - self.inventory_lock [ 'timestamp' ] > self.inventory_lock [ 'timeout' ] ):
                break
            time.sleep ( 0.1 )
              
        self.inventory_lock [ 'callee'    ] = callee_function
        self.inventory_lock [ 'timestamp' ] = now

    def let_inventory ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        if self.inventory_lock [ 'callee' ] != callee_function:
            self.log.error ( "Inventory lock being freed by another function than callee!" )
        self.inventory_lock [ 'callee'    ] = None
        self.inventory_lock [ 'timestamp' ] = None

    def request_inventory ( self, player ):
        self.inventory = { 'checking' : True }
        self.framework.console.send ( "si {}".format ( player.steamid ) )
        self.framework.console.send ( "si{}".format ( player.steamid ) )

    def si_process_guard ( self, si_string ):
        steamid = int ( si_string [ len ( "si" ) : ] )
        player = self.framework.server.get_player ( steamid )
        if not player:
            self.log.warning ( "si_process_guard could not get valid player from '{}'.".format ( steamid ) )
            return
        self.inventory [ 'checking' ] = False

    def update_inventory ( self, matches ):
        self.log.debug ( "update inventory ( {} )".format ( matches ) )
        if len ( matches ) == 2:
            player = self.framework.server.get_player ( matches [ 1 ] )
            if not player:
                self.log.error ( "No player {} found for si update!".format ( matches [ 1 ] ) )
                return
            self.inventory [ 'storage' ] = matches [ 0 ]
        if len ( matches ) == 3:
            slot = int ( matches [ 0 ] )
            quantity = int ( matches [ 1 ] )
            kind = matches [ 2 ]
            key_string = "{} {} {} {}".format ( self.inventory [ 'storage' ],
                                                slot,
                                                quantity,
                                                kind )
            self.inventory [ key_string ] = ( self.inventory [ 'storage' ],
                                              slot,
                                              quantity,
                                              kind )
            if slot == 31:
                self.inventory [ 'checking' ] = False

    # get time:

    def decide_gt ( self ):
        """
        Verifies if it is appropriate to send a new gt call, and does so accordingly.
        """
        self.lock_gt_queue ( )
        current_length = len ( self.gt_queue )
        self.unlock_gt_queue ( )
        if current_length > 0:
            return
        now = time.time ( )
        if now - self.latest_gt_call < self.gt_lag:
            self.log.debug ( "decide_gt: gt_lag ({:.2f}).".format ( self.gt_lag ) )
            return
        self.latest_gt_call = now
        gt_message = self.framework.console.telnet_wrapper ( "gt" )
        self.framework.console.telnet_client_commands.write ( gt_message )

    def process_gt ( self, day_match_groups ):
        self.log.debug ( "update_gt ( {} )".format ( day_match_groups ) )
        now = time.time ( )
        new_gt = { }

        previous_day = self.game_server.day
        previous_hour = self.game_server.hour
        previous_minute = self.game_server.minute
        
        day    = int ( day_match_groups [ 0 ] )
        hour   = int ( day_match_groups [ 1 ] )
        minute = int ( day_match_groups [ 2 ] )
            
        self.game_server.time   = ( day, hour, minute )
        self.game_server.day    = day
        self.game_server.hour   = hour
        self.game_server.minute = minute

        self.log.debug ( "Checking for time events." )
        if ( previous_day != self.game_server.day ):
            self.framework.game_events.day_changed ( previous_day )
        if ( previous_hour != self.game_server.hour ):
            self.framework.game_events.hour_changed ( previous_hour )

        self.game_server.gt = ( new_gt, now )

        if minute != previous_minute:
            if minute % 15 == 0:
                self.log.info ( "Game date: {} {:02d}:{:02d}.".format ( day, hour, minute ) )

        old_lag = self.gt_lag
        new_lag = time.time ( ) - self.latest_gt_call
        if new_lag > old_lag:
            self.gt_lag += 0.1
        if new_lag < old_lag:
            self.gt_lag -= 0.1
        self.gt_lag = max ( self.gt_lag, self.framework.preferences.loop_wait )
        if self.gt_lag != old_lag:
            self.log.info ( "gt_lag = {:.2f}s".format ( self.gt_lag ) )

    def decide_llp ( self ):
        if time.time ( ) - self.llp_timestamp > 600:
            self.log.info ( "decided to llp" )
            self.framework.console.llp ( )
            self.llp_timestamp = time.time ( )

    def lock_gt_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.gt_queue_lock
        now = time.time ( )
        
        while ( lock [ 'callee' ] ):
            if ( now - lock [ 'timestamp' ] > lock [ 'timeout' ] ):
                self.log.error ( "Breaking lock due to timeout!" )
                break
            time.sleep ( 0.1 )
              
        lock [ 'callee'    ] = callee_function
        lock [ 'timestamp' ] = now

    def unlock_gt_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.gt_queue_lock
        
        if lock [ 'callee' ] != callee_function:
            self.log.error ( "Lock being freed by another function than callee!" )
        lock [ 'callee'    ] = None
        lock [ 'timestamp' ] = None

    # le

    def decide_le ( self ):
        self.lock_le_queue ( )
        current_length = len ( self.le_queue )
        self.unlock_le_queue ( )
        if current_length > 0:
            return
        now = time.time ( )
        if now - self.latest_le_call < self.le_lag:
            self.log.debug ( "decide_le: ignore since le_lag is {:.2f}.".format ( self.le_lag ) )
            return
        self.log.info ( "calling le" )
        self.latest_le_call = time.time ( )
        le_message = self.framework.console.telnet_wrapper ( "le" )
        self.framework.console.telnet_client_le.write ( le_message )

    def buffer_le ( self, matches ):
        self.log.debug ( "buffer_le: {}.".format ( matches ) )
        new_le = framework.entity_info ( )
        new_le.entity_id = int ( matches [ 0 ] )
        new_le.entity_type = matches [ 1 ]
        new_le.pos_x = matches [ 2 ]
        new_le.pos_y = matches [ 4 ]
        new_le.pos_z = matches [ 3 ]
        new_le.rot_x = matches [ 5 ]
        new_le.rot_y = matches [ 7 ]
        new_le.rot_z = matches [ 6 ]
        new_le.lifetime = matches [ 8 ]
        new_le.remote = matches [ 9 ]
        new_le.dead = matches [ 10 ]
        new_le.health = int ( matches [ 11 ] )
        new_le.timestamp = time.time ( )
        self.enqueue_le ( new_le )
        
    def enqueue_le ( self, le_data ):
        self.log.debug ( "enqueue_le: {}.".format ( le_data.entity_type ) )
        self.lock_le_queue ( )
        self.le_queue.append ( le_data )
        self.unlock_le_queue ( )

    def dequeue_le ( self ):
        self.lock_le_queue ( )
        le_data = None
        if len ( self.le_queue ) > 0:
            le_data = self.le_queue.pop ( )
        self.unlock_le_queue ( )
        if le_data:
            self.log.debug ( "dequeue_le: {}.".format ( le_data.entity_type ) )
            self.process_le ( le_data )

    def process_le ( self, le_data ):
        self.entities [ le_data.entity_id ] = le_data

    def prune_entities ( self ):
        to_delete = [ ]
        for entityid in list ( self.entities.keys ( ) ):
            if self.entities [ entityid ].timestamp < time.time ( ) - 120:
                to_delete.append ( entityid )
        for entityid in to_delete:
            del self.entities [ entityid ]
        
    def lock_le_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.le_queue_lock
        now = time.time ( )
        
        while ( lock [ 'callee' ] ):
            try:
                if ( now - lock [ 'timestamp' ] > lock [ 'timeout' ] ):
                    self.log.error ( "Breaking lock due to timeout!" )
                    break
            except:
                self.log.info ( "lock callee exists but not timestamp." )
            time.sleep ( 0.1 )
              
        lock [ 'callee'    ] = callee_function
        lock [ 'timestamp' ] = now

    def unlock_le_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.le_queue_lock
        
        if lock [ 'callee' ] != callee_function:
            self.log.error ( "Lock being freed by another function than callee!" )
        lock [ 'callee'    ] = None
        lock [ 'timestamp' ] = None


    # Player info related:

    def decide_lp ( self ):
        self.lock_lp_queue ( )
        current_length = len ( self.lp_queue )
        self.unlock_lp_queue ( )
        if current_length > 0:
            return
        now = time.time ( )
        if now - self.latest_lp_call < self.lp_lag:
            self.log.debug ( "decide_lp: lp_lag ({:.2f}).".format ( self.lp_lag ) )
            return
        self.latest_lp_call = time.time ( )
        lp_message = self.framework.console.telnet_wrapper ( "lp" )
        self.framework.console.telnet_client_lp.write ( lp_message )

    def footer_lp ( self, matches ):
        total = int ( matches [ 0 ] )
        num_players = len ( list ( self.players.keys ( ) ) )
        num_entities = len ( list ( self.entities.keys ( ) ) )
        if total > num_players - 2 and total < num_players + 2:
            old_lag = self.lp_lag
            new_lag = time.time ( ) - self.latest_lp_call
            if new_lag > self.lp_lag:
                self.lp_lag += 0.1
            if new_lag < self.lp_lag:
                self.lp_lag -= 0.1
            self.lp_lag = max ( self.lp_lag, self.framework.preferences.loop_wait )
            if self.lp_lag != old_lag:
                self.log.info ( "lp_lag = {:.1f}s".format ( self.lp_lag ) )
        if total > num_entities - 5 and total < num_entities + 5:
            old_lag = self.le_lag
            latest_interval = time.time ( ) - self.latest_le_call
            if latest_interval > self.le_lag:
                self.le_lag += 0.1
            if latest_interval < self.le_lag:
                self.le_lag -= 0.1
            self.le_lag = max ( self.le_lag, self.framework.preferences.loop_wait + 60 )
            if self.le_lag != old_lag:
                self.log.info ( "le_lag = {:.1f}s".format ( self.le_lag ) )
        
    def buffer_lp ( self, matches ):
        self.log.debug ( "buffer_lp: {}.".format ( matches [ 1 ] ) )
        new_lp = framework.lp_data ( int ( matches [  0 ] ),
                                     matches [  1 ],
                                     float ( matches [  2 ] ),
                                     float ( matches [  3 ] ), 
                                     float ( matches [  4 ] ),
                                     float ( matches [  5 ] ),
                                     float ( matches [  6 ] ),
                                     float ( matches [  7 ] ),
                                     matches [  8 ],
                                     int ( matches [  9 ] ),
                                     int ( matches [ 10 ] ),
                                     int ( matches [ 11 ] ),
                                     int ( matches [ 12 ] ),
                                     int ( matches [ 13 ] ),
                                     int ( matches [ 14 ] ),
                                     int ( matches [ 15 ] ),
                                     matches [ 16 ],
                                     int ( matches [ 17 ] ) )
        self.enqueue_lp ( new_lp )
        
    def enqueue_lp ( self, lp_data ):
        self.log.debug ( "enqueue_lp: {}.".format ( lp_data.name ) )
        self.lock_lp_queue ( )
        self.lp_queue.append ( lp_data )
        self.unlock_lp_queue ( )

    def dequeue_lp ( self ):
        self.lock_lp_queue ( )
        lp_data = None
        if len ( self.lp_queue ) > 0:
            lp_data = self.lp_queue.pop ( )
        self.unlock_lp_queue ( )
        if lp_data:
            self.log.debug ( "dequeue_lp: {}.".format ( lp_data.name ) )
            self.process_lp ( lp_data )

    def process_lp ( self, lp_data ):
        if lp_data.steamid not in list ( self.players.keys ( ) ):
            self.players [ lp_data.steamid ] = { }
        self.players [ lp_data.steamid ] = lp_data

    def prune_players ( self ):
        for steamid in list ( self.players.keys ( ) ):
            if self.players [ steamid ].timestamp < time.time ( ) - 120:
                del self.players [ steamid ]
        
    def lock_lp_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.lp_queue_lock
        now = time.time ( )
        
        while ( lock [ 'callee' ] ):
            try:
                if ( now - lock [ 'timestamp' ] > lock [ 'timeout' ] ):
                    self.log.error ( "Breaking lock due to timeout!" )
                    break
                time.sleep ( 0.1 )
            except Exception as e:
                continue
              
        lock [ 'callee'    ] = callee_function
        lock [ 'timestamp' ] = now

    def unlock_lp_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.lp_queue_lock
        
        if lock [ 'callee' ] != callee_function:
            self.log.error ( "Lock being freed by another function than callee!" )
        lock [ 'callee'    ] = None
        lock [ 'timestamp' ] = None

    # mem

    def update_mem ( self, match ):
        now =  time.time ( )
        new_mem_info = { } 
        new_mem_info [ 'time'       ] = match [ 0  ]
        new_mem_info [ 'fps'        ] = match [ 1  ]
        new_mem_info [ 'heap'       ] = match [ 2  ]
        new_mem_info [ 'max'        ] = match [ 3  ]
        new_mem_info [ 'chunks'     ] = match [ 4  ]
        new_mem_info [ 'cgo'        ] = match [ 5  ]
        new_mem_info [ 'players'    ] = match [ 6  ]
        new_mem_info [ 'zombies'    ] = match [ 7  ]
        new_mem_info [ 'entities_1' ] = match [ 8  ]
        new_mem_info [ 'entities_2' ] = match [ 9  ]
        new_mem_info [ 'items'      ] = match [ 10 ]
            
        self.game_server.mem = ( new_mem_info, now )
        
