class player_info_v1 ( object ):
    def __init__ ( self,
                   deaths = None,
                   health = None,
                   home = None,
                   ip = None,
                   level = None,
                   name = None,
                   online = None,
                   playerid = None,
                   players = None,
                   pos_x = None,
                   pos_y = None,
                   pos_z = None,
                   score = None,
                   steamid = None,
                   zombies = None ):
        super ( player_info, self ).__init__ ( )

        # Attributes received from lp:
        self.deaths = deaths
        self.health = health
        self.home = home
        self.ip = ip
        self.level = level
        self.name = name
        self.online = online
        self.playerid = playerid
        self.players = players
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.score = score
        self.steamid = steamid
        self.zombies = zombies

        # Attributes received from mods:
        self.home_invasion_beacon = None
        self.home_invitees = [ ]
        self.language_preferred = None
        self.languages_spoken = [ ]
        self.map_limit_beacon = None
        self.name_sane = None

        # Extensible attributes dictionary:
        self.attributes = { }

class player_info_v2 ( object ):
    def __init__ ( self,
                   deaths = None,
                   health = None,
                   home = None,
                   ip = None,
                   level = None,
                   name = None,
                   online = None,
                   playerid = None,
                   players = None,
                   pos_x = None,
                   pos_y = None,
                   pos_z = None,
                   score = None,
                   steamid = None,
                   zombies = None ):
        super ( self.__class__, self ).__init__ ( )

        # Attributes received from lp:
        self.deaths = deaths
        self.health = health
        self.home = home
        self.ip = ip
        self.level = level
        self.name = name
        self.online = online
        self.playerid = playerid
        self.players = players
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.score = score
        self.steamid = steamid
        self.zombies = zombies

        # Attributes received from mods:
        self.camp = None
        self.home_invasion_beacon = None
        self.home_invitees = [ ]
        self.language_preferred = None
        self.languages_spoken = [ ]
        self.map_limit_beacon = None
        self.name_sane = None

        # Extensible attributes dictionary:
        self.attributes = { }

class player_info_v3 ( object ):
    def __init__ ( self,
                   deaths = None,
                   health = None,
                   home = None,
                   ip = None,
                   level = None,
                   name = None,
                   online = None,
                   playerid = None,
                   players = None,
                   pos_x = None,
                   pos_y = None,
                   pos_z = None,
                   score = None,
                   steamid = None,
                   zombies = None ):
        super ( self.__class__, self ).__init__ ( )

        # Attributes received from lp:
        self.deaths = deaths
        self.health = health
        self.home = home
        self.ip = ip
        self.level = level
        self.name = name
        self.online = online
        self.playerid = playerid
        self.players = players
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.score = score
        self.steamid = steamid
        self.zombies = zombies

        # Attributes received from mods:
        self.camp = None
        self.cash = None
        self.home_invasion_beacon = None
        self.home_invitees = [ ]
        self.inventory_tracker = None
        self.karma = None
        self.language_preferred = None
        self.languages_spoken = [ ]
        self.permissions = None
        self.player_kills_explanations = None
        self.positions = None
        self.map_limit_beacon = None
        self.name_sane = None
        self.online_time = None
        self.timestamp_latest_update = None
        
        # Extensible attributes dictionary:
        self.attributes = { }

class player_info_v4 ( object ):
    def __init__ ( self,
                   deaths = None,
                   health = None,
                   home = None,
                   ip = None,
                   level = None,
                   name = None,
                   online = None,
                   playerid = None,
                   players = None,
                   pos_x = None,
                   pos_y = None,
                   pos_z = None,
                   score = None,
                   steamid = None,
                   zombies = None ):
        super ( self.__class__, self ).__init__ ( )

        # Attributes received from lp:
        self.deaths = deaths
        self.health = health
        self.home = home
        self.ip = ip
        self.level = level
        self.name = name
        self.online = online
        self.playerid = playerid
        self.players = players
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.score = score
        self.steamid = steamid
        self.zombies = zombies

        # Attributes received from mods:
        self.accounted_zombies = None
        self.camp = None
        self.cash = None
        self.home_invasion_beacon = None
        self.home_invitees = None
        self.inventory_tracker = None
        self.karma = None
        self.language_preferred = None
        self.languages_spoken = None
        self.map_limit_beacon = None
        self.name_sane = None
        self.online_time = None
        self.permissions = None
        self.player_kills_explanations = None
        self.positions = None
        self.timestamp_latest_update = None
        
        # Extensible attributes dictionary:
        self.attributes = { }

class player_info_v5 ( object ):
    def __init__ ( self,
                   deaths = None,
                   health = None,
                   home = None,
                   ip = None,
                   level = None,
                   name = None,
                   online = None,
                   playerid = None,
                   players = None,
                   pos_x = None,
                   pos_y = None,
                   pos_z = None,
                   score = None,
                   steamid = None,
                   zombies = None ):
        super ( self.__class__, self ).__init__ ( )

        # Attributes received from lp:
        self.deaths = deaths
        self.health = health
        self.home = home
        self.ip = ip
        self.level = level
        self.name = name
        self.online = online
        self.playerid = playerid
        self.players = players
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.score = score
        self.steamid = steamid
        self.zombies = zombies

        # Attributes received from mods:
        self.accounted_zombies = None
        self.camp = None
        self.cash = None
        self.home_invasion_beacon = None
        self.home_invitees = None
        self.inventory_tracker = None
        self.karma = None
        self.language_preferred = None
        self.languages_spoken = None
        self.map_limit_beacon = None
        self.name_sane = None
        self.online_time = None
        self.permissions = None
        self.player_kills_explanations = None
        self.positions = None
        self.timestamp_latest_update = None
        
        # Extensible attributes dictionary:
        self.attributes = { }

        # New attributes:
        self.home_invasions = None
        self.latest_teleport = None
        self.new_since_last_update = None
       
class player_info_v6 ( object ):
    def __init__ ( self,
                   deaths = 0,
                   health = 0,
                   home = ( ),
                   ip = "",
                   level = 1,
                   name = "",
                   online = False,
                   ping = 0,
                   playerid = -1,
                   players = 0,
                   pos_x = 0,
                   pos_y = 0,
                   pos_z = 0,
                   score = 0,
                   steamid = -1,
                   zombies = 0 ):
        super ( self.__class__, self ).__init__ ( )

        # Attributes received from lp:
        self.deaths = deaths
        self.health = health
        self.home = home
        self.ip = ip
        self.level = level
        self.name = name
        self.online = online
        self.playerid = playerid
        self.players = players
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.pos_z = pos_z
        self.score = score
        self.steamid = steamid
        self.zombies = zombies

        # Attributes received from mods:
        self.accounted_zombies = 0
        self.camp = ( )
        self.cash = 0
        self.home_invasion_beacon = ( )
        self.home_invasions = { }
        self.home_invitees = [ ]
        self.inventory_tracker = [ ]
        self.karma = 0
        self.language_preferred = ""
        self.languages_spoken = [ ]
        self.latest_teleport = { }
        self.map_limit_beacon = ( )
        self.name_sane = ""
        self.new_since_last_update = { }
        self.online_time = 0
        self.permissions = { }
        self.player_kills_explanations = [ ]
        self.positions = [ ]
        self.timestamp_latest_update = 0
        
        # Extensible attributes dictionary:
        self.attributes = { }

        # New attributes:
        self.old_names = [ ]
        self.ping = ping
        self.countries = [ ]
