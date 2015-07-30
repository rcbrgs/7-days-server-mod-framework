import logging
import sys

class preferences ( object ):
    def __init__ ( self, preferences_file_name ):
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.2.1'
        self.changelog = {
            '0.2.1' : "Simplified telnet_port parsing.",
            '0.2.0' : "Added database variables.",
            }
        
        self.mods = { }
        if not preferences_file_name:
            self.chat_log_file = ""
            self.log_file = ""
            self.forbidden_countries = ""
            self.framework_state_file = ""
            self.geoip_file = ""
            self.home_radius = 50
            self.log_file = ""
            self.loop_wait = 2
            self.mod_ip = ""
            self.mods = { }
            self.mysql_user_name = ""
            self.mysql_user_password = ""
            self.mysql_db_name = ""
            self.player_info_file = ""
            self.rank_url = ""
            self.rank_message = ""
            self.teleport_lag_cushion = 3
            self.telnet_ip = ""
            self.telnet_password = ""
            self.telnet_port = 8081
            return

        self.preference_items = [ "mysql_user_name",
                                  "mysql_user_password",
                                  "mysql_db_name",
                                  "telnet_port",
                                  ]

            
        self.preferences_file = open ( preferences_file_name )
        
        for line in self.preferences_file:
            splitted = line.split ( "=" )
            if len ( splitted ) > 1:
                left_hand = splitted [ 0 ] .strip ( ). lower ( )
                right_hand = splitted [ 1 ] [ : -1 ].strip ( ).lower ( )
            else:
                continue

            if ( left_hand == "chat_log_file" ):
                if sys.platform == 'linux':
                    self.chat_log_file = splitted [ 1 ].strip ( )
                else:
                    self.chat_log_file = splitted [ 1 ].strip ( ).encode ( 'unicode-escape' )
                continue

            if ( left_hand == "forbidden_countries" ):
                self.forbidden_countries = [ ]
                countries = splitted [ 1 ].split ( "," )
                for country in countries:
                    self.forbidden_countries.append ( country.strip ( ) )
                continue

            if ( left_hand == "framework_state_file" ):
                if sys.platform == 'linux':
                    self.framework_state_file = splitted [ 1 ].strip ( )
                else:
                    self.framework_state_file = splitted [ 1 ].strip ( ).encode ( 'unicode-escape' )
                continue

            if ( left_hand == "geoip_file" ):
                if sys.platform == 'linux':
                    self.geoip_file = splitted [ 1 ].strip ( )
                else:
                    self.geoip_file = splitted [ 1 ].strip ( ).encode ( 'unicode-escape' )
                continue
            
            if ( left_hand == "home_radius" ):
                self.home_radius = int ( splitted [ 1 ].strip ( ) )
                continue
            
            if ( left_hand == "log_file" ):
                self.log_file = splitted [ 1 ].strip ( )
                continue
            
            if ( left_hand == "loop_wait" ):
                self.loop_wait = int ( splitted [ 1 ] )
                continue

            if ( left_hand == "mod_ip" ):
                self.mod_ip = splitted [ 1 ].strip ( )
                continue

            for item in self.preference_items:
                if left_hand == item:
                    setattr ( self, item, splitted [ 1 ].strip ( ) )
                    continue

            if ( left_hand == "mod_ip" ):
                self.mod_ip = splitted [ 1 ].strip ( )
                continue

            if ( left_hand == "player_info_file" ):
                if sys.platform == 'linux':
                    self.player_info_file = splitted [ 1 ].strip ( )
                else:
                    self.player_info_file = splitted [ 1 ].strip ( ).encode ( 'unicode-escape' )
                continue

            if ( left_hand == "prisoners_file" ):
                if sys.platform == 'linux':
                    self.prisoners_file = splitted [ 1 ].strip ( )
                else:
                    self.prisoners_file = splitted [ 1 ].strip ( ).encode ( 'unicode-escape' )
                continue

            if ( left_hand == "rank_url" ):
                self.rank_url = splitted [ 1 ].strip ( )
                continue
            
            if ( left_hand == "rank_message" ):
                self.rank_message = splitted [ 1 ].strip ( )
                continue
            
            if ( left_hand == "teleport_lag_cushion" ):
                self.teleport_lag_cushion = int ( splitted [ 1 ].strip ( ) )
                continue
            
            if ( left_hand == "telnet_ip" ):
                self.telnet_ip = splitted [ 1 ].strip ( )
                continue
            
            if ( left_hand == "telnet_password" ):
                self.telnet_password = splitted [ 1 ].strip ( )
                continue
            
            #if ( left_hand == "telnet_port" ):
            #    self.telnet_port = int ( splitted [ 1 ] )
            #    continue
            
            if ( left_hand == "zombie_cleanup_threshold" ):
                self.zombie_cleanup_threshold = float ( splitted [ 1 ].strip ( ) )
                continue
           
            if ( right_hand == "mod" ):
                self.mods [ left_hand ] = { }
                continue

        # at this point, the self.mods should contain keys for all mods
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
        self.log.info ( "chat_log_file = %s" % ( self.log_file ) )
        self.log.info ( "forbidden_countries = %s" % ( self.forbidden_countries ) )
        self.log.info ( "framework_state_file = %s" % ( self.framework_state_file ) )
        self.log.info ( "geoip_file = %s" % ( self.geoip_file ) )
        self.log.info ( "home_radius = %s" % ( self.home_radius ) )
        self.log.info ( "log_file = %s" % ( self.log_file ) )
        self.log.info ( "loop_wait = %d" % ( self.loop_wait ) )
        self.log.info ( "mod_ip = %s" % str ( self.mod_ip ) )
        self.log.info ( "mods = %s" % str ( self.mods ) )
        for item in self.preference_items:
            self.log.info ( "{} = {}.".format ( item, getattr ( self, item ) ) )
        self.log.info ( "player_info_file = %s" % ( self.player_info_file ) )
        self.log.info ( "rank_url = %s" % ( self.rank_url ) )
        self.log.info ( "rank_message = %s" % ( self.rank_message ) )
        self.log.info ( "teleport_lag_cushion = %d" % self.teleport_lag_cushion )
        self.log.info ( "telnet_ip = %s" % ( self.telnet_ip ) )
        #print ( "telnet_password = %s" % ( self.telnet_password ) )
        self.log.info ( "telnet_port = %d" % ( self.telnet_port ) )
