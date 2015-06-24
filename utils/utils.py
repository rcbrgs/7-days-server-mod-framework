import framework

class utils ( object ):
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
