import bs4
import logging
import time
import urllib3
import threading

class rank ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.__version__ = '0.1.5'
        self.changelog = {
            '0.1.5' : "Wrapped rank update in an try clause so 404s wont crash the thread.",
            '0.1.4' : "Increased prize for voting.",
            '0.1.3' : "Jazzed up vote thank you. Added log about rank changing position.",
            '0.1.2' : "Increased prize for votes.",
            '0.1.1' : "Changed delay to 10 minutes to not overwhelm the rank server.",
            '0.1.0' : "Initital commit" }

        self.current_rank = -1
        self.daemon = True
        self.framework = framework
        self.players_votes = { }
        self.previous_rank = -1
        self.shutdown = False
        self.timestamp = time.time ( )

    def __del__ ( self ):
        self.shutdown = True
        
    def run ( self ):
        while not self.shutdown:
            now = time.time ( )
            if now - self.timestamp > 600:
                self.log.info ( "Updating rank info." )
                self.update_current_rank ( )
                self.update_players_votes ( )
                self.verify_votes_accounted ( )
                self.timestamp = time.time ( )
            time.sleep ( self.framework.preferences.loop_wait )

    def stop ( self ):
        self.shutdown = True
            
    def update_current_rank ( self ):
        http = urllib3.PoolManager()
        request = http.request ( 'GET', 'http://7daystodie-servers.com/server/14698' )
        soup = bs4.BeautifulSoup ( request.data )
        tds = soup.findAll ( "td" )
        try:
            rank = int ( tds [ 29 ].contents [ 0 ] )
        except Exception as e:
            self.log.error ( "Error parsing rank webpage: {}.".format ( e ) )
            return
        self.current_rank = rank
        if self.previous_rank != self.current_rank:
            if self.previous_rank != -1:
                self.log.info ( "Server rank changed from {} to {}.".format ( self.previous_rank,
                                                                              self.current_rank ) )
            self.previous_rank = self.current_rank
        self.log.info ( "Current rank is {}.".format  ( rank ) )
        
    def update_players_votes ( self ):
        http = urllib3.PoolManager()
        request = http.request ( 'GET', 'http://7daystodie-servers.com/server/14698/vote' )
        soup = bs4.BeautifulSoup ( request.data )
        tds = soup.findAll ( "td" )
        number_of_voters = int ( len ( tds ) / 2 )
        month = time.strftime ( "%Y-%m" )

        for voter in range ( number_of_voters ):
            voter_name = tds [ voter * 2 ].contents [ 0 ]
            voter_votes = int ( tds [ voter * 2 + 1 ].contents [ 0 ] )
            voter_player = self.framework.server.get_player ( voter_name )
            if voter_player:
                self.players_votes [ voter_player.steamid ] = ( month, voter_votes )
                self.log.debug ( "{} voted {} times month {}.".format ( voter_name,
                                                                        voter_votes,
                                                                        month ) )

    def verify_votes_accounted ( self ):
        for player in self.framework.server.get_online_players ( ):
            if player.steamid in self.players_votes.keys ( ):
                self.log.debug ( "Updating voter info of {}.".format ( player.name_sane ) )
                accounted_votes = { }
                if 'accounted_votes' in list ( player.attributes.keys ( ) ):
                    accounted_votes = player.attributes [ 'accounted_votes' ]
                accounted_votes_this_month = 0
                if self.players_votes [ player.steamid ] [ 0 ] in list ( accounted_votes.keys ( ) ):
                    accounted_votes_this_month = accounted_votes [ self.players_votes [ player.steamid ] [ 0 ] ]
                self.log.debug ( "{} has {} accounted votes.".format ( player.name_sane,
                                                                      accounted_votes_this_month ) )
                votes_to_account = self.players_votes [ player.steamid ] [ 1 ] - \
                                   accounted_votes_this_month
                self.log.debug ( "{} to receive {} karma for voting.".format ( player.name_sane,
                                                                              votes_to_account ) )
                if votes_to_account > 0:
                    self.framework.console.say ( "Thank you {} for voting for us! Have some cash and karma! You are [123456]amazing[FFFFFF]!".format (
                        player.name_sane ) )
                    player.karma += votes_to_account
                    player.cash  += votes_to_account * 200
                if 'accounted_votes' not in list ( player.attributes.keys ( ) ):
                    player.attributes [ 'accounted_votes' ] = { }
                player.attributes [ 'accounted_votes' ] [ self.players_votes [ player.steamid ] [ 0 ] ] = self.players_votes [ player.steamid ] [ 1 ]
                                                                                                        
