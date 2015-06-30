import inspect
import logging
import re
import sys
import time
import threading

class parser ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.1.0'
        self.changelog = {
            '0.1.0' : "Initial commit." }

        self.daemon = True
        self.match_string_date = r'([0-9]{4})-([0-9]{2})-([0-9]{2}).+([0-9]{2}):([0-9]{2}):([0-9]{2}) ([0-9]+\.[0-9]+)' # 7 groups
        self.match_string_ip = r'([\d]+\.[\d]+\.[\d]+\.[\d]+)' # 1 group
        self.match_string_pos = r'\(([-+]*[\d]*\.[\d]), ([-+]*[\d]*\.[\d]), ([-+]*[\d]*\.[\d])\)'
        self.match_prefix = r'^' + self.match_string_date + r' '
        self.matchers = { }
        self.queue = [ ]
        self.queue_lock = None
        self.shutdown = False
        self.framework = framework
        self.telnet_output_matchers = {
            'chunks saved'         : { 'to_match' : r'.* INF Saving (.*) of chunks took (.*)ms',
                                       'to_call' : [ ] },
            'claim finished'       : { 'to_match' : r'Total of [\d]+ keystones in the game',
                                       'to_call'  : [ self.framework.server.llp_finished ] },
            'claim player'         : { 'to_match' : r'Player "(.*) \(([\d]+)\)" owns [\d]+ ' + \
                                       r'keystones \(protected: [\w]+, current hardness multiplier: [\d]+\)',
                                       'to_call'  : [ self.framework.server.llp_claim_player ] },
            'claim stone'          : { 'to_match' : r'\(([-+]*[\d]*), ([-+]*[\d]*), ([-+]*[\d]*)\)',
                                       'to_call'  : [ self.framework.server.llp_claim_stone ] },
            'deny match'           : { 'to_match' : r'(.*) INF Player (.*) denied: ' + \
                                       r'(.*) has been banned until (.*)',
                                       'to_call'  : [ self.framework.game_events.player_denied ] },
            'EAC callback'         : { 'to_match' : self.match_prefix + r'INF \[EAC\] UserStatusHandler callback.'+\
                                       r' Status: UserAuthenticated GUID: [\d]+ ReqKick: [\w]+ Message:.*$',
                                       'to_call'  : [ ] },
            'empty line'           : { 'to_match' : r'^$',
                                       'to_call'  : [ ] },
            'fell off world'       : { 'to_match' : self.match_string_date + r' WRN Entity \[type=.*, name=.*' +\
                                       r', id=[\d]+\] fell off the world, if=[\d]+ pos=' + self.match_string_date,
                                       'to_call'  : [ ] },
            'gmsg'                 : { 'to_match' : self.match_string_date + r' INF GMSG: (.*: .*)$',
                                       'to_call'  : [ self.framework.server.parse_gmsg ] },
            'gt command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'gt\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ self.command_gt_executing_parser ] },
            'gt command output'    : { 'to_match' : r'Day ([0-9]+), ([0-9]{2}):([0-9]{2})',
                                       'to_call'  : [ self.command_gt_output_parser ] },
            'header  9'            : { 'to_match' : r'^Difficulty:  [\d]+$',
                                       'to_call'  : [ ] },
            'header 10'            : { 'to_match' : r'Press \'help\' to get a list of all commands\. Press ' + \
                                       r'\'exit\' to end session.',
                                       'to_call'  : [ ] },
            'le command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'le\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ self.command_le_executing_parser ] },
            'le output'            : { 'to_match' : r'^[\d]+\. id=([\d]+), \[type=[\w]+, name=(.*),' +\
                                       r' id=[\d]+\], pos=' + self.match_string_pos + r', rot=' + \
                                       self.match_string_pos + r', lifetime=(.*), remote=([\w]+),' + \
                                       r' dead=([\w]+), health=([\d]+)',
                                       'to_call'  : [ self.command_le_output_parser ] },
            'le item output'       : { 'to_match' : r'^[\d]+\. id=([\d]+), Item_[\d]+ \(EntityItem\), ' + \
                                       r'pos=' + self.match_string_pos + r', rot=' + \
                                       self.match_string_pos + r', lifetime=(.*), remote=([\w])+,' + \
                                       r' dead=([\w]+),$',
                                       'to_call'  : [ ] },
            'le falling output'    : { 'to_match' : r'^[\d]+\. id=([\d]+), FallingBlock_[\d]+ \(EntityFallingBlo' +\
                                       r'ck\), pos=' + self.match_string_pos + r', rot=' + self.match_string_pos + \
                                       r', lifetime=(.*), remote=([\w])+, dead=([\w]+),$',
                                       'to_call'  : [ ] },
            'llp executing'        : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'llp\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'loglevel executing'   : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'loglevel [\w]{3} [\w]+\' by Telnet from ' + \
                                       self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'loglevels enable'     : { 'to_match' : r'^[\w]+abling all loglevels on this connection.$',
                                       'to_call'  : [ ] },
            'lp command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'lp\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ self.command_lp_executing_parser ] },
            'lp output'            : { 'to_match' : r'^[\d]+\. id=([\d]+), (.*), pos=' + \
                                       self.match_string_pos + r', rot=' + self.match_string_pos + \
                                       r', remote=([\w]+), health=([\d]+), deaths=([\d]+), zombies=([\d]+), ' + \
                                       r'players=([\d]+), score=([\d]+), level=(1), steamid=([\d]+), ip=' + \
                                       self.match_string_ip + r', ping=([\d]+)',
                                       'to_call'  : [ self.command_lp_output_parser ] },
            'le/lp output footer'  : { 'to_match' : r'^Total of ([\d]+) in the game$',
                                       'to_call'  : [ self.framework.le_lp_footer ] },
            'player online'        : { 'to_match' : r'^' + self.match_string_date + r' INF Player set to online' + \
                                       r' : ([\d]+)$',
                                       'to_call'  : [ self.framework.server.set_steamid_online ] },
            'player died'          : { 'to_match' : self.match_prefix + r'INF GMSG: Player (.*) died$',
                                       'to_call'  : [ self.framework.game_events.player_died ] },
            'player kill'          : { 'to_match' : self.match_prefix + r'INF GMSG: Player (.*)' + \
                                       r' eliminated Player (.*)',
                                       'to_call'  : [ self.framework.game_events.player_kill ] },
            'player left'          : { 'to_match' : self.match_prefix + r'INF GMSG: (.*) left the game$',
                                       'to_call'  : [ self.framework.game_events.player_left ] },
            'mem output'           : { 'to_match' : r'[0-9]{4}-[0-9]{2}-[0-9]{2}.* INF Time: ([0-9]+.[0-9]+)m ' + \
                                       r'FPS: ([0-9]+.[0-9]+) Heap: ([0-9]+.[0-9]+)MB Max: ([0-9]+.[0-9]+)MB ' + \
                                       r'Chunks: ([0-9]+) CGO: ([0-9]+) Ply: ([0-9]+) Zom: (.*) Ent: ([\d]+) ' + \
                                       r'\(([\d]+)\) Items: ([0-9]+)',
                                       'to_call'  : [ self.framework.server.update_mem ] },
            'pm executing'         : { 'to_match' : r'^' + self.match_string_date + r' INF Executing command' + \
                                       r' \'pm (.*) (.*)\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ self.command_pm_executing_parser ] },
            'removing entity'      : { 'to_match' : self.match_prefix + r'INF Removing observed entity [\d]+',
                                       'to_call'  : [ ] },
            'saveworld'            : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'saveworld\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'si command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'si [\d]+\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'say executing'        : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'say ".*"\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'spawn night horde'    : { 'to_match' : r'^' + self.match_string_date + \
                                       r' INF Spawning Night Horde for day [\d]+',
                                       'to_call'  : [ ] },
            'spawn wander horde'   : { 'to_match' : self.match_prefix + r'INF Spawning Wandering Horde.$',
                                       'to_call'  : [ ] },
            'spawned'              : { 'to_match' : r'^' + self.match_string_date + r' INF Spawned ' + \
                                       r'\[type=EntityZombie[\w]*, name=(.*), id=[\d]+\] at ' + \
                                       self.match_string_pos + r' Day=[\d]+ TotalInWave=[\d]+ CurrentWave=[\d]+$',
                                       'to_call'  : [ ] },
            'spawn output'         : { 'to_match' : r'^Spawned [\w\d]+$',
                                       'to_call'  : [ ] },
            'steam auth'           : { 'to_match' : r'^' + self.match_string_date + r' INF \[Steamworks.NET\] ' + \
                                       r'Authentication callback\. ID: [\d]+, owner: [\d]+, result: .*$',
                                       'to_call'  : [ ] },
            'wave spawn'           : { 'to_match' : r'^' + self.match_string_date + r' INF Spawning this wave:' +\
                                       r' ([\d]+)',
                                       'to_call'  : [ ] },
            'wave start'           : { 'to_match' : r'^' + self.match_string_date + r' INF Start a new wave ' + \
                                       r'\'[\w]+\'\. timeout=[\d]+s$',
                                       'to_call'  : [ ] },
            'telnet thread exit'   : { 'to_match' : '^' + self.match_string_date + \
                                       r' INF Exited thread TelnetClientSend_' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'telnet thread start r': { 'to_match' : '^' + self.match_string_date + \
                                       r' INF Started thread TelnetClientReceive_' + self.match_string_ip + \
                                       r':[\d]+$',
                                       'to_call'  : [ ] },
            'telnet thread start s': { 'to_match' : '^' + self.match_string_date + \
                                       r' INF Started thread TelnetClientSend_' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'tp command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'teleportplayer ([\d]+) ([+-]*[\d]+) ' + \
                                       r'([+-]*[\d]+) ([+-]*[\d]+)\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'version'              : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'version\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'exception sharing'    : { 'to_match' : r'IOException: Sharing violation on path .*',
                                       'to_call'  : [ ] },
        }
        # must run after self.telnet_output_matchers is defined
        for key in self.telnet_output_matchers.keys ( ):
            self.matchers [ key ] = {
                'matcher' : re.compile ( self.telnet_output_matchers [ key ] [ 'to_match' ] ),
                'callers' : self.telnet_output_matchers [ key ] [ 'to_call' ] }
        
    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        while ( self.shutdown == False ):

            line = self.dequeue ( )
            self.log.debug ( "dequeued: '{}'.".format ( line [ 'text' ]) ) 
            
            any_match = False
            for key in self.matchers.keys ( ):
                match = self.matchers [ key ] [ 'matcher' ].search ( line [ 'text' ] )
                if match:
                    any_match = True
                    self.log.debug ( "{} groups = {}.".format ( key, match.groups ( ) ) )
                    for caller in self.matchers [ key ] [ 'callers' ]:
                        self.log.debug ( "{} calls {}.".format ( key, caller ) )
                        caller ( match.groups ( ) )
                        self.log.debug ( "{} called {} and finished.".format ( key, caller ) )

            if not any_match:
                self.log.info ( "Unparsed output: '{:s}'.".format ( line [ 'text' ] ) )

            self.log.debug ( "Line parsed in {:.5f}s.".format ( time.time ( ) - line [ 'timestamp' ] ) )

    def stop ( self ):
        self.shutdown = True

    # API

    def enqueue ( self, text ):
        self.lock_queue ( )
        self.queue.append ( { 'text'      : text,
                              'timestamp' : time.time ( ) } )
        self.unlock_queue ( )

    # \API

    def command_gt_executing_parser ( self, match ):
        if self.framework.preferences.mod_ip == match [ 7 ]:
            self.framework.gt_info [ 'sending'   ] [ 'condition' ] = False
            self.framework.gt_info [ 'executing' ] [ 'condition' ] = True
            now = time.time ( )
            self.framework.gt_info [ 'executing' ] [ 'timestamp' ] = now
            old_lag = self.framework.gt_info [ 'lag' ]
            self.framework.gt_info [ 'lag' ] = now - self.framework.gt_info [ 'sent'      ] [ 'timestamp' ]
            self.log.debug ( 'gt executing' )
            if "{:.1f}".format ( self.framework.gt_info [ 'lag' ] ) != "{:.1f}".format ( old_lag ):            
                if ( self.framework.gt_info [ 'lag' ] > 5 ):
                    self.log.info ( "gt lag: {:.1f}s.".format ( self.framework.gt_info [ 'lag' ] ) )

    def command_gt_output_parser ( self, match ):
        day     = int ( match [ 0 ] )
        hour    = int ( match [ 1 ] )
        minutes = int ( match [ 2 ] )
        self.framework.server.get_game_info_lock ( )
        self.framework.server.game_server.day = day
        self.framework.server.game_server.hour = hour
        if minutes % 15 == 0 and minutes != self.framework.server.game_server.minute:
            self.log.info ( "Game date: {} {:02d}:{:02d}.".format ( day, hour, minutes ) )
        self.framework.server.game_server.minute = minutes
        self.framework.server.game_server.time = ( day, hour, minutes )
        self.framework.server.let_game_info_lock ( )

    def command_le_output_parser ( self, match ):
        self.log.debug ( str ( match ) )
        self.framework.server.update_le ( match )

    def command_le_executing_parser ( self, match ):
        if self.framework.preferences.mod_ip == match [ 7 ]:
            self.framework.le_info [ 'executing' ] [ 'condition' ] = True
            self.framework.le_info [ 'executing' ] [ 'timestamp' ] = time.time ( )
            self.log.debug ( 'le executing' )

    def command_lp_executing_parser ( self, match ):
        if self.framework.preferences.mod_ip == match [ 7 ]:
            self.framework.lp_info [ 'sent'      ] [ 'condition' ] = False
            self.framework.lp_info [ 'executing' ] [ 'condition' ] = True
            now = time.time ( )
            self.framework.lp_info [ 'executing' ] [ 'timestamp' ] = now
            old_lag = self.framework.lp_info [ 'lag' ]
            self.framework.lp_info [ 'lag' ] = now - self.framework.lp_info [ 'sent'      ] [ 'timestamp' ]
            self.log.debug ( 'lp executing' )
            if "{:.1f}".format ( self.framework.lp_info [ 'lag' ] ) != "{:.1f}".format ( old_lag ):            
                if ( self.framework.lp_info [ 'lag' ] > 5 ):
                    self.log.info ( "lp lag: {:.1f}s.".format ( self.framework.lp_info [ 'lag' ] ) )

    def command_lp_output_parser ( self, match ):
        self.log.debug ( str ( match ) )
        self.framework.server.update_id ( match )

    def command_pm_executing_parser ( self, match ):
        self.log.debug ( "cmd pm exec parser: {}".format ( match ) )
        if self.framework.preferences.mod_ip == match [ 9 ]:
            self.log.debug ( "pm was from mod" )
            self.framework.pm_info [ 'sending'   ] [ 'condition' ] = False
            self.framework.pm_info [ 'executing' ] [ 'condition' ] = True
            now = time.time ( )
            self.framework.pm_info [ 'executing' ] [ 'timestamp' ] = now
            old_lag = self.framework.pm_info [ 'lag' ]
            self.framework.pm_info [ 'lag' ] = now - self.framework.pm_info [ 'sending' ] [ 'timestamp' ]
            self.log.debug ( 'pm executing' )
            if "{:.1f}".format ( self.framework.pm_info [ 'lag' ] ) != "{:.1f}".format ( old_lag ):
                if self.framework.pm_info [ 'lag' ] > 5:
                    self.log.info ( "pm lag: {:.1f}s.".format ( self.framework.pm_info [ 'lag' ] ) )

    def dequeue ( self ):
        self.lock_queue ( )
        while len ( self.queue ) < 1:
            self.unlock_queue ( )
            time.sleep ( 0.1 )
            self.lock_queue ( )
        popped = self.queue.pop ( 0 )
        self.unlock_queue ( )
        return popped

    def lock_queue ( self ):
        callee_class = inspect.stack ( ) [ 1 ] [ 0 ].f_locals [ 'self' ].__class__.__name__
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        begin = time.time ( )
        while self.queue_lock:
            #self.log.info ( "{}.{} wants parser queue lock from {}.".format (
            #    callee_class, callee, self.queue_lock ) )
            time.sleep ( 0.01 )
            if time.time ( ) - begin > 60:
                break
        self.queue_lock = callee_class + "." + callee
        self.log.debug ( "{:s} got parser queue lock.".format ( callee ) )

    def unlock_queue ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        self.queue_lock = None
        self.log.debug ( "{:s} unlocked the parser queue.".format ( callee ) )
        
    def timestamp_from_date_prefix ( self, date_matcher_groups ):
        self.log.debug ( date_matcher_groups )
        year = date_matcher_groups [ 0 ]
        month = date_matcher_groups [ 1 ]
        day = date_matcher_groups [ 2 ]
        hour = date_matcher_groups [ 3 ]
        minute = date_matcher_groups [ 4 ]
        second = date_matcher_groups [ 5 ]
        server_time = time.strptime ( "{} {} {} {} {} {}".format (
            year, month, day, hour, minute, second ),
                                      "%Y %m %d %H %M %S" )

        return time.mktime ( server_time )
        
