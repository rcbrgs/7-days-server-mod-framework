import copy
import inspect
import logging
import time

class world_state ( object ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )

        self.framework = framework
        
        self.claimstones = { }
        self.claimstones_buffer = { }
        self.claimstones_buffer_player = ( )
        self.claimstones_buffer_total = 0
                                      
        self.claimstones_lock = { 'callee'    : None,
                                  'timeout'   : 10,
                                  'timestamp' : None }
        
        now = time.time ( )
        self.llp_timestamp = 0

        self.gt_timestamp = now

        self.le_timestamp = now

        self.lp_timestamp = now

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
