import logging
import sys
import threading
import time

# change the class name
class template ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__.__name__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.version = "0.0.0"
        self.framework = framework

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ].enabled
        self.commands = { }

    def greet ( self ):
        self.framework.server.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.version )  

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

            # STARTMOD

            
            
            # ENDMOD                             
            
            time.sleep ( self.framework.preferences.loop_wait )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
