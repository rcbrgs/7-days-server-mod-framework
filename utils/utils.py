import framework
import inspect
import logging
import math
import time

class utils ( object ):
    def __init__ ( self ):
        self.__version__ = '0.1.0'
        self.changelog = {
            '0.1.0' : "Initial changelog version." 
            }
        self.log = logging.getLogger ( __name__ )

    def calculate_bearings ( self, point_A, point_B ):
        origin_x = point_A [ 0 ]
        origin_y = point_A [ 1 ]
        helper_x = point_B [ 0 ]
        helper_y = point_B [ 1 ]
        relative_x = origin_x - helper_x
        relative_y = origin_y - helper_y

        relative = abs ( relative_x / relative_y )
        if relative > 0.75:
            if relative_y > 0:
                cardinal = "W"
            else:
                cardinal = "E"
        elif relative < 0.25:
            if relative_y > 0:
                cardinal = "N"
            else:
                cardinal = "S"
        else:
            if relative_y > 0:
                if relative_x > 0:
                    cardinal = "SW"
                else:
                    cardinal = "SE"
            elif relative_x > 0:
                cardinal = "NW"
            else:
                cardinal = "NE"
        return cardinal
            
    def calculate_distance ( self, point_A, point_B ):
        if ( ( len ( point_A ) == 2 and len ( point_B ) == 2 ) or
             ( len ( point_A ) == 3 and len ( point_B ) == 2 ) or
             ( len ( point_A ) == 2 and len ( point_B ) == 3 ) ):
            return math.sqrt ( ( point_A [ 0 ] - point_B [ 0 ] ) ** 2 +
                               ( point_A [ 1 ] - point_B [ 1 ] ) ** 2 )
        if ( len ( point_A ) == 3 and
             len ( point_B ) == 3 ):
            return math.sqrt ( ( point_A [ 0 ] - point_B [ 0 ] ) ** 2 +
                               ( point_A [ 1 ] - point_B [ 1 ] ) ** 2 +
                               ( point_A [ 2 ] - point_B [ 2 ] ) ** 2 )

    def get_coordinates ( self, player = None ):
        return ( player.pos_x, player.pos_y, player.pos_z )
        
    def get_map_coordinates ( self, code_coordinates = None ):
        x = code_coordinates [ 0 ]
        y = code_coordinates [ 1 ]
        z = code_coordinates [ 2 ]

        result = str ( round ( abs ( x ) ) )
        if x >= 0:
            result += "E, "
        else:
            result += "W, "
        result += str ( round ( abs ( y ) ) )
        if y >= 0:
            result += "N"
        else:
            result += "S"

        return result

    def wait_nonnull ( self, variable ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name 
        self.log.info ( "wait_nonnull callee = {}".format ( callee ) )
        now = time.time ( )
        while time.time ( ) - now < 60:
            if not variable:
                time.sleep ( 0.1 )
            else:
                return
        self.log.error ( "wait_nonnull exiting due to timeout, callee = {}!".format ( callee ) )
            
    def wait_not_empty ( self, variable ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name 
        self.log.info ( "wait_not_empty callee = {}".format ( callee ) )
        now = time.time ( )
        while time.time ( ) - now < 60:
            if variable == [ ]:
                time.sleep ( 0.1 )
            else:
                self.log.info ( "wait_not_empty from callee = '{}' returning with variable = {}".format ( 
                        callee, variable ) )
                return
        self.log.error ( "wait_not_empty exiting due to timeout, callee = {}, variable = '{}'.".format ( 
                callee, variable ) )
