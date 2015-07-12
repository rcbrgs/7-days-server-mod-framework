import framework
import importlib
import inspect
import logging
import pickle
import sys
import threading
import time
import traceback

class orchestrator ( threading.Thread ):
    def __init__ ( self ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.daemon = True
        self.__version__ = '0.5.2'
        self.changelog = {
            '0.5.2' : "Cleanup for new lp cycle.",
            '0.5.1' : "Added header to status.",
            '0.5.0' : "Added status() to call each telnet's status().",
            '0.4.3' : "After shutdown sequence, logging level goes to debug.",
            '0.4.2' : "Soft shutdown refactor, using a more systematic approach.",
            '0.4.1' : "Added a framework.rank object to scrape 7daystodie-servers.com. Initial work on soft shutdown for components.",
            '0.4.0' : "Major refactor to use multiple telnets and parsers.",
            '0.3.8' : "Separated send and list channels. Makes sense; who talks through their ears?",
            '0.3.7' : "Reverted to reliable non-self-healing version.",
            '0.3.6' : "Extended with utils module. Added db_lock functionality.",
            '0.3.5' : "Linked with game events.",
            '0.3.4' : "Only call lp if needed.",
            '0.3.3' : "Do not call module when module reload fails.",
            '0.3.2' : "Let players know when mods go up or down.",
            '0.3.1' : "Framework state will now save and output changelog.",
            '0.3.0' : "Added support for saving the framework state.",
            '0.2.2' : "Increased interval between offline_all_players calls, because everything is racing this.",
            '0.2.1' : "Fixing errors regarding self.mods change.",
            '0.2.0' : "Changed self.mods to be a dict, and output changelog during updates." }

        self.le_info = {
            'sent'      : { 'condition' : False,
                            'timestamp' : 0 },
            'executing' : { 'condition' : False,
                            'timestamp' : 0 },
            'parsed'    : { 'condition' : False,
                            'timestamp' : 0 },
            }
        self.pm_info = {
            'enqueueing' : { 'condition' : True,
                            'timestamp' : 0 },
            'sending'    : { 'condition' : False,
                            'timestamp' : 0 },
            'executing'  : { 'condition' : False,
                            'timestamp' : 0 },
            'parsed'     : { 'condition' : False,
                            'timestamp' : 0 },
            'lag'        : 0
            }

        self.db_lock = None
        self.ent_lock = None
        self.framework_state = None
        self.items_lock = None
        self.load_time = time.time ( )
        self.mods = { }
        self.rank = framework.rank ( self )
        self.stop_on_shutdown = [ ]
        self.verbose = False
        self.world_state = framework.world_state ( self )
        
    def __del__ ( self ):
        self.log.error ( "<framework>.__del__ being called instead of stop!" )
        if not self.shutdown:
            self.stop ( )

    def run ( self ):            
        self.server.offline_players ( )
        count = 1

        try:
            while self.shutdown == False:
                self.log.debug ( "Tick" )
                
                for mod_key in self.mods.keys ( ):
                    mod = self.mods [ mod_key ] [ 'reference' ]
                    if mod.is_alive ( ) == False:
                        self.log.warning ( "mod %s is dead, restarting." % str ( mod ) )
                        self.shutdown = True
                        break
                    
                        old_version = mod.__version__
                        module_name = mod.__class__.__name__
                        mod.shutdown = True
                        mod.join ( )
                        mod_instance = self.load_mod ( module_name )
                        if mod_instance == None:
                            continue
                        mod_instance.start ( )
                        new_version = mod_instance.__version__
                        if old_version != new_version:
                            self.log.info ( "Mod %s updated to v%s. Changelog: %s" %
                                            ( mod_key, old_version, new_version,
                                              mod_instance.changelog [ new_version ] ) )

                if count % 100 == 0:
                    self.server.offline_players ( )
                            
                self.log.debug ( "Asking server for updates." )
                now = time.time ( )
                if now - self.world_state.le_timestamp > self.preferences.loop_wait:
                    pass
                    self.world_state.le_timestamp = now
                    self.console.le ( )
                if now - self.world_state.llp_timestamp > self.preferences.loop_wait * 100:
                    self.world_state.llp_timestamp = now
                    self.console.llp ( )

                time.sleep ( self.preferences.loop_wait )
                count += 1
        except Exception as e:
            self.log.critical ( "Shutting down mod framework due to unhandled exception: %s." % str ( e ) )
            exception_info = sys.exc_info ( )
            self.log.critical ( traceback.print_tb ( exception_info [ 2 ] ) )

        self.shutdown = True
        self.stop ( )

        self.log.info ( "**************************   Stopping framework   ***************************" )
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def config ( self, preferences_file_name ):
        self.silence = False
        self.shutdown = False
        self.preferences = framework.preferences ( preferences_file_name )
        self.rank.start ( )
        self.stop_on_shutdown.append ( self.rank )
        self.server = framework.server ( framework = self )
        self.game_events = framework.game_events ( framework = self )
        
        framework.set_log_file ( self.preferences.log_file )

        self.log.info ( "**************************   Starting framework   ***************************" )
        
        self.preferences.output ( )

        file_found = True
        try:
            pickle_file = open ( self.preferences.framework_state_file, 'rb' )
        except FileNotFoundError as e:
            self.log.error ( e )
            self.log.info ( "Creating new framework state file." )
            file_found = False

        if ( file_found ):
            self.old_framework_state = pickle.load ( pickle_file )
        else:
            self.old_framework_state = None

        self.framework_state = { 'orchestrator' : { 'version' : self.__version__,
                                                    'changelog' : self.changelog [ self.__version__ ], } }
                                                    #'reference' : self } }

        self.log.info ( "Loading console." )
        self.console = framework.queued_console ( self )
        self.console.start ( )
        self.stop_on_shutdown.append ( self.console )

        self.world_state.start ( )
        self.stop_on_shutdown.append ( self.world_state )

        self.log.debug ( "Loading telnet." )
        self.telnet = framework.telnet_client ( framework = self )
        self.log.debug ( "Connecting telnet." )
        self.telnet.open_connection ( )
        time.sleep ( 9 )
        self.server.start ( )
        self.stop_on_shutdown.append ( self.server )
        self.telnet.start ( )
        self.stop_on_shutdown.append ( self.telnet )
        self.telnet.write ( "loglevel ALL true\n".encode ( 'utf-8') )

        self.game_events.start ( )
        self.stop_on_shutdown.append ( self.game_events )

        self.utils = framework.utils ( )


        self.framework_state [ 'telnet' ] = { 'version'   : self.telnet.__version__,
                                              'changelog' : self.telnet.changelog [ self.telnet.__version__ ], }
                                              #'reference' : self.telnet }
        self.framework_state [ 'server' ] = { 'version'   : self.server.__version__,
                                              'changelog' : self.server.changelog [ self.server.__version__ ], }
                                              #'reference' : self.server }
        self.framework_state [ 'game_events' ] = { 'version'   : self.game_events.__version__,
                                                   'changelog' : self.game_events.changelog [ self.game_events.__version__ ], }
                                                   #'reference' : self.game_events }
        self.framework_state [ 'rank' ] = { 'version'   : self.rank.__version__,
                                            'changelog' : self.rank.changelog [ self.rank.__version__ ], }
                                            #'reference' : self.rank }

        for mod in self.preferences.mods.keys ( ):
            module_name = self.preferences.mods [ mod ] [ 'module' ]
            self.load_mod ( module_name )
        
        for mod in self.mods.keys ( ):
            self.mods [ mod ] [ 'reference' ].start ( )

        for component in self.framework_state.keys ( ):
            try:
                old_version = self.old_framework_state [ component ] [ 'version' ]
            except Exception as e:
                self.log.error ( e )
                old_version = 'unknown'
            new_version = self.framework_state [ component ] [ 'version' ]
            if ( old_version != new_version and
                 old_version != 'unknown' ):
                self.console.say ( "Mod %s updated to %s: %s" %
                                   ( str ( component ), str ( new_version ),
                                     str ( self.framework_state [ component ] [ 'changelog' ] ) ) )
            
    def get_db_lock ( self ):
        callee_class = inspect.stack ( ) [ 1 ] [ 0 ].f_locals [ 'self' ].__class__.__name__
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        begin = time.time ( )
        while self.db_lock:
            self.log.info ( "{}.{} wants player db lock from {}.".format (
                callee_class, callee, self.db_lock ) )
            time.sleep ( 0.6 )
            if time.time ( ) - begin > 60:
                break
        self.db_lock = callee_class + "." + callee
        self.log.debug ( "{:s} get player db lock.".format ( callee ) )

    def get_ent_lock ( self ):
        callee_class = inspect.stack ( ) [ 1 ] [ 0 ].f_locals [ 'self' ].__class__.__name__
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        while self.ent_lock:
            self.log.info ( "{}.{} wants entities db lock from {}.".format (
                callee_class, callee, self.ent_lock ) )
            time.sleep ( 0.6 )
        self.ent_lock = callee_class + "." + callee
        self.log.debug ( "{:s} get entities db lock.".format ( callee ) )

    def let_db_lock ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        self.db_lock = None
        self.log.debug ( "{:s} let player db lock.".format ( callee ) )

    def let_ent_lock ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        self.ent_lock = None
        self.log.debug ( "{:s} let entities db lock.".format ( callee ) )

    def load_mod ( self, module_name ):
        full_module_name = module_name + "." + module_name
        
        if full_module_name in list (  self.mods.keys ( ) ):
            self.log.info ( "mod %s already in self.mods." % full_module_name )
            return
        
        self.log.debug ( "Attempting to load module %s." % full_module_name )
        try:
            mod_module = importlib.import_module ( full_module_name )
            mod_module = importlib.reload ( mod_module )
        except Exception as e:
            self.log.error ( "Ignoring unloadable module: %s." % str ( e ) )
            return
        self.log.debug ( "mod_module = %s" % str ( mod_module ) )
        mod_class = getattr ( mod_module, module_name )
        mod_instance = mod_class ( framework = self )
        self.log.info ( "Mod %s loaded." % module_name )
        self.framework_state [ module_name ] = { 'version'   : mod_instance.__version__,
                                                 'changelog' : mod_instance.changelog [ mod_instance.__version__ ], }
                                                 #'reference' : mod_instance }
        self.mods [ module_name ] = { 'reference'      : mod_instance,
                                      'loaded version' : mod_instance.__version__ }
        self.log.debug ( "framework_state update with info for mod %s." %
                         module_name )
        return mod_instance

    def status ( self ):
        self.log.info ( "telnet listener status:" )
        self.telnet.status ( )
        self.log.info ( "telnet commands status:" )
        self.console.telnet_client_commands.status ( )
        self.log.info ( "telnet lp status:" )
        self.console.telnet_client_lp.status ( )
        self.log.info ( "telnet le status:" )
        self.console.telnet_client_le.status ( )
        self.log.info ( "telnet pm status:" )
        self.console.telnet_client_pm.status ( )
        
    def stop ( self ):
        self.log.info ( "framework.stop" )
        if self.shutdown:
            self.log.setLevel ( logging.DEBUG )
        pickle_file = open ( self.preferences.framework_state_file, 'wb' )
        pickle.dump ( self.framework_state, pickle_file, pickle.HIGHEST_PROTOCOL )

        self.shutdown = True
        all_mods = list ( self.mods.keys ( ) )
        for mod_key in self.mods.keys ( ):
            self.log.info ( "Mods to shutdown: {}".format ( all_mods ) )
            all_mods.remove ( mod_key )
            mod = self.mods [ mod_key ] [ 'reference' ]
            self.log.info ( "mod %s stop" % str ( mod ) )
            mod.stop ( )
            if mod.is_alive ( ):
                self.log.info ( "mod %s still alive" % str ( mod ) )
                #mod.join ( )
        self.log.info ( "All mods stopped." )

        for component in self.stop_on_shutdown:
            self.log.info ( "Trying soft shutdown of {}.".format ( str ( component ) ) )
            component.stop ( )
            #self.log.info ( "{} join".format ( str ( component ) ) )
            #component.join ( )
        self.log.info ( "Shutdown sequence complete." )
        self.log.setLevel ( logging.DEBUG )

