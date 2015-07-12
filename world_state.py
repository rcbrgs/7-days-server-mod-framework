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
        self.__version__ = '0.3.3'
        self.changelog = {
            '0.3.3' : "decide_lp and footer_lp less spammy: only log if lag > loop_wait.",
            '0.3.2' : "Throttled down gt calls by limiting to 1 per loop_wait.",
            '0.3.1' : "Fixed non-existing telnet object being called.",
            '0.3.0' : "Integrated gt code here.",
            '0.2.8' : "Simplified interface by removing unnecessary lock.",
            '0.2.7' : "Added mem and gt stuff here.",
            '0.2.6' : "Added lp_lag logging.",
            '0.2.5' : "Loosened lp cycle from 110 to 150% of lag estimation due to occasional lp storm.",
            '0.2.4' : "Added stop method.",
            '0.2.3' : "Fixed typo on get_inventory.",
            '0.2.2' : "Put lp in world state control.",
            '0.2.1' : "lp call cycle setup.",
            '0.2.0' : "Initial work for lp info.",
            '0.1.1' : "Added blocking_get_inventory." }
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

        self.game_server = game_server_info ( )

        self.inventory = { }
        self.inventory_lock = { 'callee'    : None,
                                'timeout'   : 10,
                                'timestamp' : None }

        now = time.time ( )
        self.llp_timestamp = 0
        self.le_timestamp = now
        
        # game time
        self.gt_timestamp = now
        self.gt_queue = [ ]
        self.gt_queue_lock = { 'callee'    : None,
                               'timeout'   : 10,
                               'timestamp' : None }
        self.latest_gt_call = 0
        self.gt_lag = 0.1

        # list players
        self.players = { }
        self.lp_queue = [ ]
        self.lp_queue_lock = { 'callee'    : None,
                               'timeout'   : 10,
                               'timestamp' : None }
        self.latest_lp_call = 0
        self.lp_lag = 0.1

    def run ( self ):
        while not self.shutdown:
            time.sleep ( 0.01 )

            while ( len ( self.lp_queue ) ) > 0:
                self.dequeue_lp ( )

            self.prune_players ( )
            self.decide_lp ( )
            self.decide_gt ( )

    def stop ( self ):
        self.shutdown = True
            
    def buffer_claimstones ( self, match ):
        if len ( match ) == 1:
            if self.claimstones_buffer_total != 0:
                self.log.error ( "Next llp total before parsing old one!" )
            self.claimstones_buffer_total = int ( match [ 0 ] )
            self.unbuffer_claimstones ( )
            return
        if len ( match ) == 2:
            if self.claimstones_buffer_player != ( ):
                self.log.error ( "Next player claimstones listed before parsing all of current." )
                self.log.error ( "bufferplayer = {} match = {}".format ( str ( self.claimstones_buffer_player ),
                                                                         str ( match ) ) )
                return
            self.claimstones_buffer_player = ( int ( match [ 0 ] ), int ( match [ 1 ] ) )
            return
        if len ( match ) == 3:
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
            if steamid not in self.framework.server.players_info.keys ( ):
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

        self.update_claimstones ( )

    def update_claimstones ( self ):
        self.log.info ( "Updating current claimstones data with buffer." )
        claimstones = self.get_claimstones ( )

        events = [ ]
        for steamid in self.claimstones_buffer.keys ( ):
            if steamid not in claimstones.keys ( ):
                claimstones [ steamid ] = self.claimstones_buffer [ steamid ]
                #events.append ( ( self.framework.game_events.player_set_claimstones,
                #                  ( steamid, self.claimstones_buffer [ steamid ] ) ) )
            else:
                for claim in self.claimstones_buffer [ steamid ]:
                    if claim not in claimstones [ steamid ]:
                        claimstones [ steamid ].append ( claim )
                        #events.append ( ( self.framework.game_events.player_added_claimstone,
                        #                  ( steamid, claim ) ) )
                for claim in claimstones [ steamid ]:
                    if claim not in self.claimstones_buffer [ steamid ]:
                        claimstones [ steamid ].remove ( claim )
                        #events.append ( ( self.framework.game_events.player_removed_claimstone,
                        #                  ( steamid, claim ) ) )
        
        self.let_claimstones ( )
        
        self.claimstones_buffer = { }
        self.claimstones_buffer_total = 0

        for event in events:
            event [ 0 ] ( *event [ 1 ] )

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

        return self.claimstones

    def let_claimstones ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        if self.claimstones_lock [ 'callee' ] != callee_function:
            self.log.error ( "Claimstones lock being freed by another function than callee!" )
        self.claimstones_lock [ 'callee'    ] = None
        self.claimstones_lock [ 'timestamp' ] = None

    def blocking_get_inventory ( self, player ):
        timestamp = time.time ( )
        self.get_inventory ( )
        self.request_inventory ( player )
        while self.inventory [ 'checking' ]:
            self.log.info ( "Waiting for si to complete..." )
            time.sleep ( 1 )
            if time.time ( ) - timestamp > 10:
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
        msg = "{:.1f}s {:s}m {:s}/{:s}MB {:s}chu {:s}cgo {:s}p/{:s}z/{:s}i/{:s}({:s})e.".format (
            staleness,
            str ( mi [ 'time' ] ), str ( mi [ 'heap' ] ), str ( mi [ 'max' ] ), str ( mi [ 'chunks' ] ),
            str ( mi [ 'cgo' ] ), str ( mi [ 'players' ] ), str ( mi [ 'zombies' ] ), str ( mi [ 'items' ] ),
            str ( mi [ 'entities_1' ] ), str ( mi [ 'entities_2' ] ) ) 

        return msg
                
    # /API
        
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

    def update_inventory ( self, matches ):
        self.log.info ( "update inventory ( {} )".format ( matches ) )
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
        if now - self.latest_gt_call < self.framework.preferences.loop_wait:
            return
        if now - self.latest_gt_call < self.gt_lag * 1.5:
            self.log.debug ( "decide_gt: gt_lag ({:.2f}).".format ( self.gt_lag ) )
            return
        if self.gt_lag > self.framework.preferences.loop_wait:
            self.log.info ( "decide_gt: call gt ({:.2f}).".format ( self.gt_lag ) )
        self.latest_gt_call = now
        self.gt_lag += 1
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

        self.log.info ( "Game date: {} {:02d}:{:02d}.".format ( day, hour, minute ) )
        
        self.gt_lag = time.time ( ) - self.latest_gt_call
        if self.gt_lag > self.framework.preferences.loop_wait:
            self.log.info ( "gt_lag = {:.2f}s".format ( self.gt_lag ) )

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

    # Player info related:

    def decide_lp ( self ):
        self.lock_lp_queue ( )
        current_length = len ( self.lp_queue )
        self.unlock_lp_queue ( )
        if current_length > 0:
            return
        now = time.time ( )
        if now - self.latest_lp_call < self.lp_lag * 1.5:
            self.log.debug ( "decide_lp: lp_lag ({:.2f}).".format ( self.lp_lag ) )
            return
        if self.lp_lag > self.framework.preferences.loop_wait:
            self.log.info ( "decide_lp: call lp ({:.2f}).".format ( self.lp_lag ) )
        self.latest_lp_call = time.time ( )
        self.lp_lag += 1
        lp_message = self.framework.console.telnet_wrapper ( "lp" )
        self.framework.console.telnet_client_lp.write ( lp_message )

    def footer_lp ( self, matches ):
        total = int ( matches [ 0 ] )
        if total == len ( list ( self.players.keys ( ) ) ):
            self.lp_lag = time.time ( ) - self.latest_lp_call
            if self.lp_lag > self.framework.preferences.loop_wait:
                self.log.info ( "lp_lag = {:.2f}s".format ( self.lp_lag ) )
        
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
            if ( now - lock [ 'timestamp' ] > lock [ 'timeout' ] ):
                self.log.error ( "Breaking lock due to timeout!" )
                break
            time.sleep ( 0.1 )
              
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
        
