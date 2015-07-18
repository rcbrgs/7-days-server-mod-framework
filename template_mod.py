import framework
import logging
import sys
import threading
import time

# change the class name
class template ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.1.0"
        self.changelog = {
            '0.1.0' : "Initial version." }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]

        # To have a new command for players to use, it must be placed in the dict below.
        # The commented example adds the command "/suicide" and have the mod run the function "kill_player ( )".
        # All player chat commands receive two strings as arguments. The first contains the player name (unsanitized) and the second contains the string typed by the player (also unsanitized).
        self.commands = {
            # 'suicide' : ( self.kill_player, " /suicide will kill your character." )
        }
        self.help_items = {
            #"template" : "A mod to do X.",
            }
        
    def __del__ ( self ):
        self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        # this function will be called as a thread from the framework.

        # to call the base framework functions, use the self.framework object.
        # Example: to give player that has id 123 one jar of alcohol:
        # self.framework.server.give_player_stuff ( 123, "grainAlcohol", 1 )

        # To access the current player data, use the players_info dict
        # from framework. Example: to print each players health:
        # for key in self.framework.server.players_info ( keys ):
        #print ( "player %s has %d health." % ( self.framework.server.players_info [ key ].name,
        #                                       self.framework.server.players_info [ key ].health )

        # place your mod code inside the while loop, between the START MOD and END MOD comments.
        # this ensures that your code is run the right number of times.

        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )
            if not self.enabled:
                continue

            # STARTMOD

            
            
            # ENDMOD                             
            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
