import framework
import importlib
import logging
import pickle
import sys
import threading
import time

class orchestrator ( threading.Thread ):
    def __init__ ( self ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.daemon = True
        self.__version__ = '0.3.5'
        self.changelog = {
            '0.3.5' : "Linked with game events.",
            '0.3.4' : "Only call lp if needed.",
            '0.3.3' : "Do not call module when module reload fails.",
            '0.3.2' : "Let players know when mods go up or down.",
            '0.3.1' : "Framework state will now save and output changelog.",
            '0.3.0' : "Added support for saving the framework state.",
            '0.2.2' : "Increased interval between offline_all_players calls, because everything is racing this.",
            '0.2.1' : "Fixing errors regarding self.mods change.",
            '0.2.0' : "Changed self.mods to be a dict, and output changelog during updates." }

    def config ( self, preferences_file_name ):
        self.silence = False
        self.shutdown = False
        self.preferences = framework.preferences ( preferences_file_name )

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
                                                    'changelog' : self.changelog [ self.__version__ ] } }
        
        self.telnet = framework.telnet_connect ( framework = self )
        self.telnet.open_connection ( )

        self.server = framework.server ( framework = self )

        self.server.start ( )
        self.telnet.start ( )

        self.game_events = framework.game_events ( framework = self )
        self.game_events.start ( )

        self.framework_state [ 'telnet' ] = { 'version' : self.telnet.__version__,
                                              'changelog' : self.telnet.changelog [ self.telnet.__version__ ] }
        self.framework_state [ 'server' ] = { 'version' : self.server.__version__,
                                              'changelog' : self.server.changelog [ self.server.__version__ ] }
        self.framework_state [ 'game_events' ] = { 'version'   : self.game_events.__version__,
                                                   'changelog' : self.game_events.changelog [ self.game_events.__version__ ] }

        self.mods = { }

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
            if old_version != new_version:
                self.server.say ( "Mod %s updated to %s: %s" %
                                  ( str ( component ), str ( new_version ),
                                    str ( self.framework_state [ component ] [ 'changelog' ] ) ) )
            
    def load_mod ( self, module_name ):
        full_module_name = module_name + "." + module_name
        
        if ( full_module_name in self.mods ):
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
        self.framework_state [ module_name ] = { 'version' : mod_instance.__version__,
                                                 'changelog' : mod_instance.changelog [ mod_instance.__version__ ] }
        self.mods [ module_name ] = { 'reference'      : mod_instance,
                                      'loaded version' : mod_instance.__version__ }
        self.log.info ( "framework_state update with info for mod %s." %
                        module_name )
        return mod_instance

    def run ( self ):            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

        self.server.say ( "Mods up." )
        self.server.offline_players ( )
        count = 1

        try:
            while self.shutdown == False:
                self.log.debug ( "Tick" )
                
                for mod_key in self.mods.keys ( ):
                    mod = self.mods [ mod_key ] [ 'reference' ]
                    if mod.is_alive ( ) == False:
                        self.log.warning ( "mod %s is dead, restarting." % str ( mod ) )
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
                            self.server.say ( "Mod %s updated to v%s. Changelog: %s" %
                                              ( mod_key, old_version, new_version,
                                                mod_instance.changelog [ new_version ] ) )
                        #while not mod_instance.is_alive ( ):
                        #    self.log.warning ( "Sleeping 1 second to wait mod to run." )
                        #    time.sleep ( 1 )

                self.log.debug ( "Before gt" )
                self.server.console ( "gt" )
                self.log.debug ( "After gt" )
                
                if count % 100 == 0:
                    self.server.offline_players ( )

                if ( time.time ( ) - self.server.latest_id_parse_call ) > self.preferences.loop_wait:
                    self.log.debug ( "Too long since last update, doing lp." )
                    self.server.console ( "lp" )
            
                time.sleep ( self.preferences.loop_wait )
                count += 1
        except Exception as e:
            self.log.critical ( "Shutting down mod framework due to unhandled exception: %s." % str ( e ) )
            self.shutdown = True

        for mod_key in self.mods.keys ( ):
            mod = self.mods [ mod_key ] [ 'reference' ]
            self.log.info ( "mod %s stop" % str ( mod ) )
            mod.stop ( )
            self.log.info ( "mod %s join" % str ( mod ) )
            if mod.is_alive ( ):
                mod.join ( )
        self.log.info ( "All mods stopped." )

        self.telnet.stop ( )
        self.telnet.join ( )
        self.telnet.close_connection ( )

        self.log.info ( "**************************   Stopping framework   ***************************" )
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.log.info ( "<framework>.stop" )
        self.server.say ( "Mods down." )
        pickle_file = open ( self.preferences.framework_state_file, 'wb' )
        pickle.dump ( self.framework_state, pickle_file, pickle.HIGHEST_PROTOCOL )

        self.shutdown = True

    def __del__ ( self ):
        self.log.info ( "<framework>.__del__" )
        self.stop ( )
