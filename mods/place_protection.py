import logging
import sys
import threading
import time

class place_protection ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.daemon = True
        self.__version__ = '0.1.5'
        self.changelog = {
            '0.1.5' : "Added a city, removed function to remove sethomes within protection.",
            '0.1.4' : "Removed places from previous map.",
            '0.1.3' : "Claimstones now teleport away from claimed area.",
            '0.1.2' : "Fixed call to utils.calculate_distance. Added a city.",
            '0.1.1' : "Added changelog." }
        
        self.framework = framework
        self.shutdown = False


        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]
        self.commands = { 'protected_places' : ( self.command_protected_places,
                                                 " /protected_places shows where you cannot build." ), }

        # To add a protected place, insert it in this dictionary:
        #                              -W / +E  +N / -S
        # The format is '<name>' : ( ( <pos_x>, <pos_y> ), <radius> )
        self.places = { #'prison'                          : ( (  2612, -2976 ), 400 ),
                        #'starter base'                    : ( (  1500,   350 ), 150 ),
                        #'<name>'        : ( (   <x>,   <y> ), <radius> ),
        }

    def command_protected_places ( self, origin, message ):
        for key in self.places.keys ( ):
            msg = "%s has a %dm radius protection around %s." % ( key,
                                                                  self.places [ key ] [ 1 ],
                                                                  self.places [ key ] [ 0 ] )
            self.framework.console.say ( msg )
        
    def greet ( self ):
        if self.enabled == True:
            self.framework.console.say ( "%s mod %s loaded." % ( self.__class__.__name__,
                                                                self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        while self.shutdown == False:
            time.sleep ( self.framework.preferences.loop_wait )
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
