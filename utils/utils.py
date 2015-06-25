import framework
import math

class utils ( object ):
    def calculate_bearings ( self, player_origin, player_helper ):
        origin_x = player_origin.pos_x
        origin_y = player_origin.pos_y
        helper_x = player_helper.pos_x
        helper_y = player_helper.pos_y
        relative_x = origin_x - helper_x
        relative_y = origin_y - helper_y
        distance = math.sqrt ( relative_x ** 2 + relative_y ** 2 )
        acos = math.degrees ( math.acos ( relative_x / distance ) )
        if ( relative_y < 0 ):
            acos += 180
        return ( distance , int ( ( acos - 90 ) % 360 ) )

    def calculate_distance ( self, point_A, point_B ):
        if len ( point_A ) == 2 and len ( point_B ) == 2:
            return math.sqrt ( ( point_A [ 0 ] - point_B [ 0 ] ) ** 2 +
                               ( point_A [ 1 ] - point_B [ 1 ] ) ** 2 )
        if len ( point_A ) == 3 and len ( point_B ) == 3:
            return math.sqrt ( ( point_A [ 0 ] - point_B [ 0 ] ) ** 2 +
                               ( point_A [ 1 ] - point_B [ 1 ] ) ** 2 +
                               ( point_A [ 2 ] - point_B [ 2 ] ) ** 2 )

    def get_coordinates ( self, player = None ):
        return ( player.pos_x, player.pos_y, player.pos_z )
        
    def get_map_coordinates ( self, code_coordinates = None ):
        x = code_coordinates [ 0 ]
        y = code_coordinates [ 1 ]
        z = code_coordinates [ 2 ]

        result = str ( abs ( x ) )
        if x >= 0:
            result += "E, "
        else:
            result += "W, "
        result += str ( abs ( y ) )
        if y >= 0:
            result += "N"
        else:
            result += "S"

        return result
