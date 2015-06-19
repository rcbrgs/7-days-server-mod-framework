import logging
import sys

class preferences ( object ):
    def __init__ ( self, preferences_file_name ):
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        
        self.mods = { }
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

            if ( left_hand == "teleport_lag_cushion" ):
                self.teleport_lag_cushion = int ( splitted [ 1 ].strip ( ) )
                continue
            
            if ( left_hand == "telnet_ip" ):
                self.telnet_ip = splitted [ 1 ].strip ( )
                continue
            
            if ( left_hand == "telnet_password" ):
                self.telnet_password = splitted [ 1 ].strip ( )
                continue
            
            if ( left_hand == "telnet_port" ):
                self.telnet_port = int ( splitted [ 1 ] )
                continue
            
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

    def output ( self ):
        self.log.debug ( "chat_log_file = %s" % ( self.log_file ) )
        self.log.debug ( "forbidden_countries = %s" % ( self.forbidden_countries ) )
        self.log.debug ( "geoip_file = %s" % ( self.geoip_file ) )
        self.log.debug ( "home_radius = %s" % ( self.home_radius ) )
        self.log.debug ( "log_file = %s" % ( self.log_file ) )
        self.log.debug ( "loop_wait = %d" % ( self.loop_wait ) )
        self.log.debug ( "mods = %s" % str ( self.mods ) )
        self.log.debug ( "player_info_file = %s" % ( self.player_info_file ) )
        self.log.debug ( "teleport_lag_cushion = %d" % self.teleport_lag_cushion )
        self.log.debug ( "telnet_ip = %s" % ( self.telnet_ip ) )
        #print ( "telnet_password = %s" % ( self.telnet_password ) )
        self.log.debug ( "telnet_port = %d" % ( self.telnet_port ) )
