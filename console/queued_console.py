import framework
import inspect
import logging
from .queueable_call import queueable_call
import sys
import threading
import time

class queued_console ( threading.Thread ):
    def __init__ ( self, orchestrator ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel = ( logging.INFO )
        self.__version__ = "0.2.0"
        self.changelog = {
            '0.2.0' : "Added lkp queuable command.",
            }        
        self.framework = orchestrator
        self.daemon = True
        self.pm_lag = 10
        self.pm_latest_call = 0
        self.queue = [ ]
        self.queue_lock = None
        self.shutdown = False
        telnet_wait = 6
        self.log.info ( "loading client commands telnet" )
        self.telnet_client_commands = framework.telnet_client ( self.framework )
        self.telnet_client_commands.open_connection ( )
        self.telnet_client_commands.start ( )
        time.sleep ( telnet_wait )
        self.log.info ( "loading le telnet" )
        self.telnet_client_le = framework.telnet_client ( self.framework )
        self.telnet_client_le.open_connection ( )
        self.telnet_client_le.start ( )
        time.sleep ( telnet_wait )
        self.log.info ( "loading lp telnet" )
        self.telnet_client_lp = framework.telnet_client ( self.framework )
        self.telnet_client_lp.open_connection ( )
        self.telnet_client_lp.start ( )
        time.sleep ( telnet_wait )
        self.log.info ( "loading pm telnet" )
        self.telnet_client_pm = framework.telnet_client ( self.framework )
        self.telnet_client_pm.open_connection ( )
        self.telnet_client_pm.start ( )
        time.sleep ( telnet_wait )
        self.timestamp_le = 0
        
    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        while ( self.shutdown == False ):

            unqueueables = [ ]
            self.get_queue_lock ( )
            for command in self.queue:
                self.log.debug ( "for command in queue" )
                if command.destroyable ( ):
                    self.log.debug ( "command can be destroyed" )
                    unqueueables.append ( command )
                if command.timestamp_begun == 0:
                    self.log.debug ( "thread has not run yet" )
                    command.timestamp_begun = time.time ( )
                    command.start ( )

            for command in unqueueables:
                lag = command.timestamp_finish - command.timestamp_execution
                self.log.debug ( "Thread for command that called {} finsihed with lag {:.2f}.".format (
                    str ( command.function ), lag ) )
                self.queue.remove ( command )
            self.let_queue_lock ( )
                    
            time.sleep ( self.framework.preferences.loop_wait )

        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        telnet_wait = 7
        self.log.info ( ".telnet_client_commands.stop ( )" )
        self.telnet_client_commands.stop ( )
        time.sleep ( telnet_wait )
        self.log.info ( ".telnet_client_le.stop ( )" )
        self.telnet_client_le.stop ( )
        time.sleep ( telnet_wait )
        self.log.info ( ".telnet_client_lp.stop ( )" )
        self.telnet_client_lp.stop ( )
        time.sleep ( telnet_wait )
        self.log.info ( ".telnet_client_pm.stop ( )" )
        self.telnet_client_pm.stop ( )
        time.sleep ( telnet_wait )
        self.shutdown = True

    def get_queue_lock ( self ):
        callee_class = inspect.stack ( ) [ 1 ] [ 0 ].f_locals [ 'self' ].__class__.__name__
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        begin = time.time ( )
        while self.queue_lock:
            self.log.info ( "{}.{} wants queue lock from {}.".format (
                callee_class, callee, self.queue_lock ) )
            time.sleep ( 0.1 )
            if time.time ( ) - begin > 60:
                break
        self.queue_lock = callee_class + "." + callee
        self.log.debug ( "{:s} got queue lock.".format ( callee ) )

    def let_queue_lock ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        self.queue_lock = None
        self.log.debug ( "{:s} let queue lock.".format ( callee ) )

    # API
        
    def gt ( self ):
        if self.framework.gt_info [ 'sending' ] [ 'condition' ]:
            self.log.debug ( "Previous gt call not yet finished. Ignoring call for gt." )
            return
        diff = time.time ( ) - self.framework.gt_info [ 'sending' ] [ 'timestamp' ]
        if diff < self.framework.gt_info [ 'lag' ] * 10.1:
            self.log.debug ( "gt timestamp less than 10.1 * lag recent. Ignoring call for gt." )
            return

        if diff < 60:
            return

        self.framework.gt_info [ 'sending' ] [ 'timestamp' ] = time.time ( )
        command_call = queueable_call ( )
        command_call.function = self.gt_wrapper
        command_call.kill_timer = self.framework.preferences.loop_wait * 10
        command_call.retirement_age = self.framework.preferences.loop_wait * 10
        
        self.get_queue_lock ( )
        self.queue.append ( command_call )
        self.let_queue_lock ( )

    def lkp ( self ):
        """
        This method will request a list of the known players.
        """
        command_call = queueable_call ( )
        command_call.function = self.lkp_wrapper
        command_call.kill_timer = self.framework.preferences.loop_wait * 10
        command_call.retirement_age = self.framework.preferences.loop_wait * 10
        
        self.get_queue_lock ( )
        self.queue.append ( command_call )
        self.let_queue_lock ( )

    def llp ( self ):
        self.llp_wrapper ( )
        
    def lp ( self ):
        command_call = queueable_call ( )
        command_call.function = self.lp_wrapper
        command_call.kill_timer = self.framework.preferences.loop_wait * 10
        command_call.retirement_age = self.framework.preferences.loop_wait * 10
        
        self.get_queue_lock ( )
        self.queue.append ( command_call )
        self.let_queue_lock ( )

    def pm ( self, player, message, can_fail = False, loglevel = "INFO" ):
        command_call = queueable_call ( )
        command_call.function = self.pm_wrapper
        command_call.function_args = ( player, message )
        command_call.function_kwargs = { 'can_fail' : can_fail,
                                         'loglevel' : loglevel }
        command_call.kill_timer = self.framework.preferences.loop_wait * 10
        command_call.retirement_age = self.framework.preferences.loop_wait * 10
        
        self.get_queue_lock ( )
        self.queue.append ( command_call )
        self.let_queue_lock ( )

    # /API
        
    def gt_wrapper ( self ):
        self.send ( "gt" )
        self.framework.gt_info [ 'sent' ] = { 'condition' : True,
                                              'timestamp' : time.time ( ) }

    def lkp_wrapper ( self ):
        """
        This method's goal is to send a lkp command to the console.
        """
        self.log.debug ( "sending lkp" )
        self.framework.console.send ( "lkp" )

    def llp_wrapper ( self ):
        self.log.debug ( "sending llp" )
        self.framework.console.send ( "llp" )

    def lp_wrapper ( self ):    
        lp_message = self.telnet_wrapper ( "lp" )
        self.telnet_client_lp.write ( lp_message )

    def lp_finished ( self, lp_finish_matcher ):
        printables = [ "-----------------------------------------------------------------" ]
        counter = 0
        for player in self.framework.server.get_online_players ( ):
            printables.append ( self.framework.server.get_player_summary ( player ) )
            counter += 1
        if counter == int ( lp_finish_matcher [ 0 ] ):
            for entry in printables:
                if self.framework.verbose:
                    print ( entry )
        self.log.debug ( "Counts differ {} != {}".format ( counter, lp_finish_matcher [ 0 ] ) )    
        
    def pm_wrapper ( self, player, message, can_fail = False, loglevel = "INFO" ):
        now = time.time ( )
        while ( now - self.pm_latest_call < self.pm_lag * 1.5 ):
            time.sleep ( 0.1 )
            if can_fail:
                return
            now = time.time ( )

        pm_string = 'pm {} "{}"'.format ( player.steamid, message )
        pm_log_string = 'pm {} "{}"'.format ( player.name_sane, message )
        if loglevel == "INFO":
            self.log.info ( pm_log_string )
        elif loglevel == "DEBUG":
            self.log.debug ( pm_log_string )
        pm_message = self.telnet_wrapper ( pm_string )
        self.telnet_client_pm.write ( pm_message )
        self.pm_latest_call = time.time ( )

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
            self.telnet_client_commands.write ( outputmsg )
        else:    
            self.log.info ( "(silenced) %s" % outputmsg )

    def se ( self, player, entity, quantity ):
        if isinstance ( entity, int ):
            entity_id = entity
        else:
            entity_id = self.framework.server.entity_db [ entity ] [ 'entityid' ]
        for counter in range ( quantity ):
            self.send ( "se {} {}".format ( player.playerid, entity_id ) )
                        
    def telnet_wrapper ( self, message ):
        if isinstance ( message, str ):
            inputmsg = message + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )
        else:
            inputmsg = messagge.decode ( 'ascii' )
            inputmsg = inputmsg + "\n"
            outputmsg = inputmsg.encode ( 'utf-8' )

        return outputmsg
            
    def send ( self, message ):
        self.log.debug ( "send: {}".format ( message ) )
        outputmsg = self.telnet_wrapper ( message )
        self.telnet_client_commands.write ( outputmsg )

    def wrapper_gt ( self, gt_matcher_groups ):
        if gt_matcher_groups [ 7 ] == self.framework.preferences.mod_ip:
            self.log.debug ( "gt matched ip" )
            self.timestamp_gt = time.time ( )
        else:
            self.log.debug ( "gt unmatch ip" )

    def wrapper_pm ( self, pm_matcher_groups ):
        interval = time.time ( ) - self.timestamp_pm
        self.log.debug ( "ACK ({:.1f}s): pm from Telnet {}".format ( interval, pm_matcher_groups [ 0 ] ) )
        self.pm_executing = False
