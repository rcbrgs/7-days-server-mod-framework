import framework
import logging
import sys
import threading
import time

class console ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.3.0"
        self.changelog = {
            '0.3.0' : "Added specialized le.",
            '0.2.0' : "Added spealized pm, lp, gt and se.",
            '0.1.0' : "Initial version." }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.pm_executing = False
        self.timestamp_gt = 0
        self.timestamp_le = 0
        self.timestamp_lp = 0
        self.timestamp_pm = 0

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True

    def gt ( self ):
        self.log.warning ( "DEPRECATED call to gt." )
        self.framework.queued_console.gt ( )
        return
        if ( time.time ( ) - self.timestamp_gt ) < self.framework.preferences.loop_wait:
            self.log.debug ( "gt timestamp too recent. Ignoring call for gt." )
            return
            
        self.timestamp_gt = time.time ( )
        self.send ( "gt" )        

    def le ( self ):
        if ( time.time ( ) - self.timestamp_le ) < self.framework.preferences.loop_wait:
            self.log.debug ( "le timestamp less than loop_wait recent. Ignoring call for le." )
            return

        if ( time.time ( ) - self.timestamp_le ) < self.framework.server.telnet_connection.lag_max [ 'lag' ]:
            self.log.debug ( "le timestamp less older than 60-sec max lag. Ignoring call for le." )
            return
        
        if self.framework.server.clear_online_property:
            self.framework.server.entities = { }
        
        self.timestamp_le = time.time ( )
        self.send ( "le" )


    def lp ( self ):
        if ( time.time ( ) - self.timestamp_lp ) < self.framework.preferences.loop_wait:
            self.log.debug ( "lp timestamp less than loop_wait recent. Ignoring call for lp." )
            return

        if ( time.time ( ) - self.timestamp_lp ) < self.framework.server.telnet_connection.lag_max [ 'lag' ]:
            self.log.debug ( "lp timestamp less older than 60-sec max lag. Ignoring call for lp." )
            return
        
        if self.framework.server.clear_online_property:
            self.framework.server.offline_players ( )
        
        self.timestamp_lp = time.time ( )
        self.send ( "lp" )

    def lp_finished ( self, lp_finish_matcher ):
        printables = [ "-----------------------------------------------------------------" ]
        counter = 0
        for player in self.framework.server.get_online_players ( ):
            printables.append ( self.framework.server.get_player_summary ( player ) )
            counter += 1
        if counter == int ( lp_finish_matcher [ 0 ] ):
            self.timestamp_lp = time.time ( )
            for entry in printables:
                if self.framework.verbose:
                    print ( entry )
        self.log.debug ( "Counts differ {} != {}".format ( counter, lp_finish_matcher [ 0 ] ) )    
        
    def pm ( self, player, message ):
        #self.log.debug ( "PM being redirected." )
        #self.say ( message )
        #return
        limit = self.framework.server.telnet_connection.lag_max [ 'lag' ]
        begin = time.time ( )
        while self.pm_executing:
            self.log.debug ( "Waiting for PM to execute." )
            time.sleep ( 0.1 )
            if time.time ( ) - begin > limit:
                self.log.warning ( "Unblocking PM by limit exceeded." )
                self.pm_executing = False
                
        pm_string = 'pm {} "{}"'.format ( player.steamid, message )
        self.log.info ( pm_string )
        self.send ( pm_string )
        self.timestamp_pm = time.time ( )
        self.pm_executing = True

    def say ( self, msg ):
        """
        TELNET MESSAGING String-Conversion Check for Ascii/Bytes and Send-Message Function
        Because Casting Byte to Byte will fail.
        """
        if isinstance ( msg, str ):
            inputmsg = 'say "' + msg.replace ( '"', ' ' ) + '"' + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = msg.decode('ascii')
            inputmsg = 'say "' + inputmsg.replace ( '"', ' ' ) + '"' + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        self.log.debug ( outputmsg )
        if not self.framework.silence:
            self.framework.server.telnet_connection.write ( outputmsg )
        else:    
            self.log.info ( "(silenced) %s" % outputmsg )

    def se ( self, player, entity, quantity ):
        if isinstance ( entity, int ):
            entity_id = entity
        else:
            entity_id = self.framework.server.entity_db [ entity ] [ 'entityid' ]
        for counter in range ( quantity ):
            self.send ( "se {} {}".format ( player.playerid, entity_id ) )
                        
            
    def send ( self, message ):
        self.log.debug ( "telnet send: {}".format ( message ) )
            
        if isinstance ( message, str ):
            inputmsg = message + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = messagge.decode ( 'ascii' )
            inputmsg = inputmsg + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
                
        self.framework.server.telnet_connection.write ( outputmsg )

    def wrapper_gt ( self, gt_matcher_groups ):
        if gt_matcher_groups [ 7 ] == self.framework.preferences.mod_ip:
            self.log.debug ( "gt matched ip" )
            self.timestamp_gt = time.time ( )
        else:
            self.log.debug ( "gt unmatch ip" )

    def wrapper_lp ( self, lp_matcher_groups ):
        #self.log.warning ( "Calling deprecated wrapper_lp" )
        if lp_matcher_groups [ 7 ] == self.framework.preferences.mod_ip:
            self.log.debug ( "lp matched ip" )
            self.timestamp_lp = time.time ( )
        else:
            self.log.debug ( "lp unmatch ip" )

    def wrapper_pm ( self, pm_matcher_groups ):
        interval = time.time ( ) - self.timestamp_pm
        self.log.debug ( "ACK ({:.1f}s): pm from Telnet {}".format ( interval, pm_matcher_groups [ 0 ] ) )
        self.pm_executing = False
