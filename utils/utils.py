import framework
import math

class utils ( object ):
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
            
    def calculate_bearings2 ( self, point_A, point_B ):
        origin_x = point_A [ 0 ]
        origin_y = point_A [ 1 ]
        helper_x = point_B [ 0 ]
        helper_y = point_B [ 1 ]
        relative_x = origin_x - helper_x
        relative_y = origin_y - helper_y
        distance = math.sqrt ( relative_x ** 2 + relative_y ** 2 )
        acos = math.degrees ( math.acos ( relative_x / distance ) )
        if ( relative_y < 0 ):
            acos += 180
        #return ( distance , int ( ( acos - 90 ) % 360 ) )
        angle = ( acos - 90 ) % 360
        cardinals = { 0   : 'E',
                      45  : 'NE',
                      90  : 'N',
                      135 : 'NW',
                      180 : 'W',
                      225 : 'SW',
                      270 : 'S',
                      315 : 'SE' }
        cardinal_keys = list ( cardinals.keys ( ) )
        for key in cardinal_keys:
            if abs ( angle - key ) <= 22.5:
                return "{} ({:.0f} deg)".format ( cardinals [ key ], angle )
                #return "{}".format ( cardinals [ key ] )
        
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
