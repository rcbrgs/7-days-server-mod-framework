import logging
import random
import sys
import threading
import time

class chat_commands ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( "framework.{}".format ( __name__ ) )
        self.log_level = logging.INFO
        self.__version__ = "0.4.5"
        self.changelog = {
            '0.4.5' : "Read rules from text file.",
            '0.4.4' : "Finalized curses being read from file.",
            '0.4.3' : "Hooked to correct logging namespace.",
            '0.4.2' : "Better logging system. Curses are read from file.",
            '0.4.1' : "Added better stop system.",
            '0.4.0' : "Moved command_curse to here."
            }
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]

        self.commands = {
            'curse'       : ( self.command_curse,
                              " /curse player_name prints an unfriendly message." ),
            'rules'       : ( self.command_rules,
                              " /rules will print server rules." ),
            'track'    : ( self.command_track,
                          " /track checks which players passed within 5 blocks of your current position in the last real 24h. Costs 1 karma." ),
        }

        try:
            self.starterbase = tuple ( map ( 
                    int, self.framework.preferences.mods [ self.__class__.__name__ ] [ 'starterbase' ] [ 1 : -1 ].split ( ',' ) ) )
        except:
            self.starterbase = ( 0, 0, -5000 )

        try:
            self.curses_file = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'curses_file' ]
        except:
            self.curses_file = None

        self.curses = [ "{}, you suck!" ]
        if self.curses_file:
            curses = open ( self.curses_file, "r" )
            for line in curses:
                self.curses.append ( line [ : -1 ] )

    def __del__ ( self ):
        self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )
            self.log.setLevel ( self.log_level )
            if not self.enabled:
                continue

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
        while self.is_alive ( ):
            self.log.info ( "Self still alive." )
            time.sleep ( 1 )

    def command_curse ( self, msg_origin, msg_content ):
        self.log.info ( "self.curses = {}".format ( self.curses ) )
        target = self.framework.server.get_player ( msg_content [ len ( "/curse " ) : ] )
        if not target:
            self.log.warning ( "Invalid player destiny on curse" )
            return
        curses = self.curses
        some_msg = curses [ random.randint ( 0, len ( curses ) - 1 ) ]
        self.framework.console.say ( some_msg.format ( target.name_sane ) )

    def command_rules ( self, origin, message ):
        rules_file = open ( self.framework.preferences.server_rules_file, "r" )
        for line in rules_file:
            self.framework.console.say ( "{}".format ( line [ : - 1 ] ) )

    def command_track ( self, player_id = None, msg = None ):
        player = self.framework.server.get_player ( player_id )
        if player is None:
            return
        if player.karma >= 1:
            self.framework.server.give_karma ( player, -1 )
            self.framework.console.pm ( player, "You spent 1 karma to track." )
            tracked_playerids = self.framework.server.list_nearby_tracks ( ( player.pos_x,
                                                                             player.pos_y,
                                                                             player.pos_z ) )
            tracked_playernames = ""
            for tracked in tracked_playerids:
                tracked_player = self.framework.server.get_player ( tracked )
                if tracked_playernames != "":
                    tracked_playernames += ", "
                tracked_playernames += tracked_player.name_sane

            self.framework.console.say ( "Players that passed near {:s} in the last real 24h: {:s}.".format (
                self.framework.utils.get_map_coordinates ( self.framework.utils.get_coordinates ( player ) ),
                tracked_playernames ) )
                
        else:
            self.framework.console.pm ( player, "You don't have enough karma!" )
