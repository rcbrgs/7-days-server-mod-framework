import time

class lp_data ( object ):
    """
    Object to store the data obtained from a line of output from a lp call.
    """
    def __init__ ( self,
                   _id = -1,
                   name = "",
                   pos_x = 0.0,
                   pos_z = 0.0,
                   pos_y = 0.0,
                   rot_x = 0.0,
                   rot_z = 0.0,
                   rot_y = 0.0,
                   remote = False,
                   health = -1,
                   deaths = -1,
                   zombies = -1,
                   players = -1,
                   score = -1,
                   level = -1,
                   steamid = -1,
                   ip = "",
                   ping = -1 ):

        super ( self.__class__, self ).__init__ ( )

        self._id     = _id
        self.name    = name
        self.pos_x   = pos_x
        self.pos_z   = pos_z
        self.pos_y   = pos_y
        self.rot_x   = rot_x
        self.rot_z   = rot_z
        self.rot_y   = rot_y
        self.remote  = remote
        self.health  = health
        self.deaths  = deaths
        self.zombies = zombies
        self.players = players
        self.score   = score
        self.level   = level
        self.steamid = steamid
        self.ip      = ip
        self.ping    = ping

        self.timestamp = time.time ( )
