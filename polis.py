import framework
import logging
import math
import sys
import threading
import time

class polis ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.__version__ = "0.1.8"
        self.changelog = {
            '0.1.8' : "Better logging during vote for debug.",
            '0.1.7' : "Fixed countdown. For real this time. Fixed wrong player handle crashing the mod.",
            '0.1.6' : "Fixed countdown displaying inverted time 0->5min instead of 5->0mins.",
            '0.1.5' : "Fixed countdown display, fixed votes not being registered. Fixed resulting command syntax. Fixed warnings.",
            '0.1.4' : "Fixed inverted time logic to countdown vote.",
            '0.1.3' : "Fixed framework.say -> framework.console.say. Old habits die hard.",
            '0.1.2' : "Fixed bug on proposal index being overflown. Added code to spend karma when proposing.",
            '0.1.1' : "Fixed limits 10, 5 days -> 10, 5 hours",
            '0.1.0' : "Initial version." }
        self.daemon = True        
        self.framework = framework
        self.log = logging.getLogger ( __name__ )
        self.shutdown = False

        self.allowed_commands = [
            ( 'explain', 2 ),
            ( 'free', 1 ),
            ( 'imprison', 1 ),
        ]                                 
        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]
        self.proposal = { }
        self.warn2min = False
        self.warn240 = False
        self.warn270 = False

        self.commands = {
            'propose' : ( self.command_propose, " /propose <command> <arguments> will start a voting to have the server issue the proposed command with the arguments. Costs 1 karma." ),
            'review'  : ( self.command_review,  " /review will display the text of the proposal and its current state." ),
            'vote'    : ( self.command_vote,    " /vote <yes/no> to accept or deny the proposal. No cost." ),
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

            if self.proposal != { }:
                now = time.time ( )
                if now - self.proposal [ 'timestamp' ] > 300:
                    self.output_review ( )
                    if self.proposal [ 'yes' ] > self.proposal [ 'no' ]:
                        self.framework.console.say ( "Motion carries!" )
                        self.framework.console.say ( "/" + self.proposal [ 'text' ] )
                    else:
                        self.framework.console.say ( "Motion denied!" )
                    self.proposal = { }
                    continue
                if now - self.proposal [ 'timestamp' ] > 270 and self.warn270:
                    self.framework.console.say ( "30 seconds to finish voting!" )
                    self.warn270 = False
                    continue
                if now - self.proposal [ 'timestamp' ] > 240 and self.warn240:
                    self.framework.console.say ( "60 seconds to finish voting!" )
                    self.warn240 = False
                    continue
                if now - self.proposal [ 'timestamp' ] > 180 and self.warn2min:
                    self.framework.console.say ( "2 minutes to finish voting!" )
                    self.warn2min = False
                    continue
            
            # ENDMOD                             
            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def command_propose ( self, origin, message ):
        player = self.framework.server.get_player ( origin )
        if not player:
            self.log.error ( "Could not find player from origin {}.".format ( origin ) )

        if player.online_time < 10 * 3600:
            self.framework.console.say ( "{}, only players with more than 10h on the server can make proposals.".format ( player.name_sane ) )
            return

        if self.proposal != { }:
            self.framework.console.say ( "{}, there is already an ongoing proposal. Please wait.".format ( player.name_sane ) )
            return

        if player.karma < 1:
            self.framework.console.say ( "{}, you need 1 karma to make a proposal!".format ( player.name_sane ) )
                
        proposed_text = message [ len ( "/propose " ) : ].strip ( )
        splitted_text = proposed_text.split ( " " )
        command = None
        
        for possibility in self.allowed_commands:
            if splitted_text [ 0 ] == possibility [ 0 ]:
                command = possibility

        if not command:
            self.framework.console.say ( "Proposed command not recognized: {}.".format ( splitted_text [ 0 ] ) )
            return

        if len ( splitted_text ) != command [ 1 ] + 1:
            self.framework.console.say ( "Proposed command {} needs {} arguments but {} were supplied.".format (
                command [ 0 ], command [ 1 ], len ( splitted_text ) ) )
            return

        self.proposal = { 'orator' : player,
                          'text' : proposed_text,
                          'timestamp' : time.time ( ),
                          'votes' : { player : 'yes' },
                          'yes' : 1,
                          'no' : 0 }

        self.warn2min = True
        self.warn240 = True
        self.warn270 = True
        player.karma -= 1

        self.framework.console.say ( "Proposal active! Citizens have 5 minutes to vote." )
        
    def command_review ( self, origin, message ):
        if self.proposal == { }:
            self.framework.console.say ( "There is no ongoing proposal." )
            return
        
        self.count_votes ( )
        self.output_review ( )

    def command_vote ( self, origin, message ):
        player = self.framework.server.get_player ( origin )
        if not player:
            self.log.error ( "Could not find player from origin {}.".format ( origin ) )
            return

        if player.online_time < 5 * 3600:
            self.framework.console.say ( "{}, only players with more than 5h on the server can vote.".format (
                player.name_sane ) )
            return
        self.log.info ( "{} has voting power.".format ( player.name_sane ) )

        vote_text = message [ len ( "/vote " ) : ].strip ( ).lower ( )
        if vote_text == 'yes':
            self.proposal [ 'votes' ] [ player ] = 'yes'
            self.framework.console.pm ( player, "You voted yes." )
            self.log.info ( "{} voted {}.".format ( player.name_sane, vote_text ) )
            return
        if vote_text == 'no':
            self.proposal [ 'votes' ] [ player ] = 'no'
            self.framework.console.pm ( player, "You voted no." )
            self.log.info ( "{} voted {}.".format ( player.name_sane, vote_text ) )
            return
        self.log.info ( "{} voted unintelligeble vote '{}'.".format ( player.name_sane, vote_text ) )


    # /commands

    def count_votes ( self ):
        yes = 0
        no  = 0
        for player in self.proposal [ 'votes' ]:
            if self.proposal [ 'votes' ] [ player ] == 'yes':
                yes += 1
            if self.proposal [ 'votes' ] [ player ] == 'no':
                no += 1

        self.proposal [ 'yes' ] = yes
        self.proposal [ 'no'  ] = no

    def output_review ( self ):
        self.framework.console.say ( "The current proposal is: '{}'.".format ( self.proposal [ 'text' ] ) )
        self.framework.console.say ( "Voting ends in {}min, {} voted yes, {} voted no.".format (
            max ( 0, math.floor ( ( 300 - ( time.time ( ) - self.proposal [ 'timestamp' ] ) ) / 60 ) ),
            self.proposal [ 'yes' ],
            self.proposal [ 'no'  ] ) )

