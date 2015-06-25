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
        self.__version__ = "0.2.1"
        self.changelog = {
            '0.2.1' : "Refactored time accounting to be more efficient.",
            '0.2.0' : "Killing 100 zombies gives some cash to player.",
            '0.1.1' : "Karma gain now PMs player.",
            '0.1.0' : "Initial version." }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.registered_callbacks = {
            'player_killed_100_zombies'  : [ ( self.framework.server.give_cash,
                                               { 'amount' : random.randint ( 50, 150 ) } ),
                                             ( self.framework.server.pm,
                                               { 'msg' : "You found some cash on those zombies corpses!" } ) ],
            'player_played_one_hour'     : [ ( self.framework.server.give_karma,
                                               { 'amount' : 1 } ),
                                             ( self.framework.server.pm,
                                               { 'msg' : "You gained +1 karma for being 1h online!" } ) ],
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

    def day_changed ( self, previous_day ):
        pass
    
    def hour_changed ( self, previous_hour ):
        day = self.framework.server.game_server.day
        hour = self.framework.server.game_server.hour
        minute = self.framework.server.game_server.minute
        self.log.info ( ">>>>>  day %d, %02dh%02d  <<<<<" % ( day, hour, minute ) )
        
    def player_killed_100_zombies ( self, player_id ):
        player = self.framework.server.get_player ( player_id )
        if player == None:
            return
        for callback in self.registered_callbacks [ 'player_killed_100_zombies' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player_id' ] = player
            function ( **kwargs )
        
    def player_played_one_hour ( self, player_id ):
        player = self.framework.server.get_player ( player_id )
        if player == None:
            return
        for callback in self.registered_callbacks [ 'player_played_one_hour' ]:
            function = callback [ 0 ]
            kwargs   = callback [ 1 ]
            kwargs [ 'player_id' ] = player
            function ( **kwargs )
        
