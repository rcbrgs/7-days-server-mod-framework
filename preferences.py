import framework
import logging
import sys

class preferences ( object ):
    def __init__ ( self, preferences_file_name ):
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.2.4'
        self.changelog = {
            '0.2.4' : "Refactored to parse parameters in a consistent manner.",
            '0.2.3' : "Added system to parse file preferences more dynamically.",
            '0.2.2' : "Improved auto parametrizer to set parameters as ints and floats when possible.",
            '0.2.1' : "Simplified telnet_port parsing.",
            '0.2.0' : "Added database variables.",
            }
        
        self.mods = { }

        self.preference_items = [ 
            "forbidden_countries",
            "loop_wait",
            "mod_ip",
            "mysql_user_name",
            "mysql_user_password",
            "mysql_db_name",
            "rank_message",
            "rank_url",
            "teleport_lag_cushion",
            "telnet_ip",
            "telnet_password",
            "telnet_port",
            ]
        for item in self.preference_items:
            setattr ( self, item, "" )

        self.preference_files = [
            "chat_log_file",
            "framework_state_file",
            "geoip_file",
            "log_file",
            "player_info_file",
            "server_rules_file"
            ]
        for file_item in self.preference_files:
            setattr ( self, file_item, "" )

        try:
            self.preferences_file = open ( preferences_file_name )
        except Exception as e:
            framework.console.output_exception ( e )
            return
        
        for line in self.preferences_file:
            splitted = line.split ( "=" )
            if len ( splitted ) > 1:
                left_hand = splitted [ 0 ] .strip ( ). lower ( )
                right_hand = splitted [ 1 ] [ : -1 ].strip ( ).lower ( )
            else:
                continue

            for item in self.preference_items:
                if left_hand == item:
                    try:
                        setattr ( self, item, int ( splitted [ 1 ].strip ( ) ) )
                        continue
                    except ValueError:
                        pass
                    try:
                        setattr ( self, item, float ( splitted [ 1 ].strip ( ) ) )
                        continue
                    except ValueError:
                        pass
                    setattr ( self, item, splitted [ 1 ].strip ( ) )
                    continue

            for file_item in self.preference_files:
                if left_hand == file_item:
                    if sys.platform == 'linux':
                        setattr ( self, file_item, splitted [ 1 ].strip ( ) )
                    else:
                        setattr ( self, file_item, splitted [ 1 ].strip ( ).encode ( 'unicode-escape' ) )
                    continue
           
            if ( right_hand == "mod" ):
                self.mods [ left_hand ] = { }
                continue

        # at this point, the self.mods should contain keys for all mods
        # so lets parse all mods keys as strings
        self.preferences_file.seek ( 0 )
        for line in self.preferences_file:
            splitted = line.split ( "=" )
            if len ( splitted ) > 1:
                left_hand = splitted [ 0 ] .strip ( ). lower ( )
                right_hand = splitted [ 1 ] [ : -1 ].strip ( )
            else:
                continue

            for key in self.mods.keys ( ):
                if ( left_hand == key + "_enabled" ):
                    if ( right_hand.lower ( ) == "true" ):
                        self.mods [ key ] [ 'enabled' ] = True
                    else:
                        self.mods [ key ] [ 'enabled' ] = False
                    break
                
                if ( left_hand == key + "_module" ):
                    self.mods [ key ] [ 'module' ] = right_hand
                    break

                if ( key + "_"  == left_hand [ : len ( key ) + 1 ] ):
                    self.mods [ key ] [ left_hand.split ( key + "_" ) [ 1 ] ] = right_hand.lower ( )
                    break;

    def output ( self ):
        for item in self.preference_items:
            if 'password' in item:
                continue
            self.log.info ( "{} = {}.".format ( item, getattr ( self, item ) ) )
        for item in self.preference_files:
            self.log.info ( "{} = {}.".format ( item, getattr ( self, item ) ) )
        for key in self.mods.keys ( ):
            for preference_key in self.mods [ key ].keys ( ):
                if 'password' in preference_key:
                    continue
                self.log.info ( "Mod {} {} = {}.".format ( 
                        key, preference_key, self.mods [ key ] [ preference_key ] ) )
