import inspect
import logging
import re
import sys
import time
import threading

class parser ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( ).__init__ ( )
        self.log = logging.getLogger ( __name__ )
        self.log.setLevel ( logging.INFO )
        self.__version__ = '0.2.10'
        self.changelog = {
            '0.2.10' : "Matcher for EAC package lost.",
            '0.2.9'  : "Logging server chat upon early detection.",
            '0.2.8'  : "Detecting server chat messages sooner.",
            '0.2.7'  : "Fixed false positives on server chat command detection.",
            '0.2.6'  : "Matcher for steam kick over invalid login.",
            '0.2.5'  : "More logging for guard matcher.",
            '0.2.4'  : "Matcher of EAC log user dconn.",
            '0.2.3'  : "Fixed translation call syntax on deprecation.",
            '0.2.2'  : "Added call to translation after deprecation check.",
            '0.2.1'  : "Fixed syntax error on callback for guard matcher of sell.",
            '0.2.0'  : "Added command guard matcher and processing.",
            }

        self.daemon = True
        self.llp_current_player = None
        self.llp_total_recently_set = True
        self.match_string_date = r'([0-9]{4})-([0-9]{2})-([0-9]{2}).+([0-9]{2}):([0-9]{2}):([0-9]{2}) ([+-]*[0-9]+\.[0-9]+)' # 7 groups
        self.match_string_ip = r'([\d]+\.[\d]+\.[\d]+\.[\d]+)' # 1 group
        self.match_string_pos = r'\(([-+]*[\d]*\.[\d]), ([-+]*[\d]*\.[\d]), ([-+]*[\d]*\.[\d])\)'
        self.match_prefix = r'^' + self.match_string_date + r' '
        self.matchers = { }
        self.queue = [ ]
        self.queue_lock = None
        self.shutdown = False
        self.framework = framework
        self.telnet_output_matchers = {
            'add obs entity'       : { 'to_match' : self.match_prefix + r'INF Adding observed entity: ' +\
                                       r'[\d]+, ' + self.match_string_pos + r', [\d]+$',
                                       'to_call'  : [ ] },
            'AI air drop paths'    : { 'to_match' : self.match_prefix + r'INF AIAirDrop: Computed flight paths for 1 aircraft$',
                                       'to_call'  : [ ] },
            'AI night horde'       : { 'to_match' : self.match_prefix + r'INF AIDirector: Night Horde Spawn Finished \(all mobs spawned\).$',
                                       'to_call'  : [ ] },
            'AI no good spot'      : { 'to_match' : self.match_prefix + r'INF AIDirector: Could not find a valid position to spawn wandering horde \(trying again in 1 hour\)$',
                                       'to_call'  : [ ] },
            'AI scout horde'       : { 'to_match' : self.match_prefix + r'INF AIDirector: scout horde zombie' + \
                                       r' \'\[type=EntityZombie, name=spiderzombie, id=[\d]+\]\' was spawned' + \
                                       r' and is moving towards point of interest\.$',
                                       'to_call'  : [ ] },
            'AI scouts'            : { 'to_match' : self.match_prefix + r'INF AIDirector: Spawning scouts @ \(' + \
                                       self.match_string_pos + r'\) heading towards \(' + self.match_string_pos + \
                                       r'\)$',
                                       'to_call'  : [ ] },
            'AI scout fail'        : { 'to_match' : self.match_prefix + r'INF AIDirector: Scout spawning failed,'+\
                                       r' FindHordeTargets\(\) returned false!',
                                       'to_call'  : [ ] },
            'AI scout finish'      : { 'to_match' : self.match_prefix + r'INF AIDirector: Scout Horde Spawn Finished \(all mobs spawned\)\.$',
                                       'to_call'  : [ ] },
            'AI scout remove'      : { 'to_match' : self.match_prefix + r'INF AIDirector: scout horde zombie \'[type=[\w]+, name=[\w]+, id=[\d]+\]\' is being removed from horde control.$',
                                       'to_call'  : [ ] },
            'AI scout-trig fin'    : { 'to_match' : self.match_prefix + r'INF AIDirector: Scout-Triggered Horde Finished \(all mobs spawned\).$',
                                       'to_call'  : [ ] },
            'AI wanderer'          : { 'to_match' : self.match_prefix + r'INF AIDirector: wandering horde zombie' +\
                                       r' \'[type=[\w]+, name=[\w]+, id=[\d]+\]\' was spawned and is moving ' + \
                                       r'towards pitstop.$',
                                       'to_call'  : [ ] },
            'AI wander finish'     : { 'to_match' : self.match_prefix + r'INF AIDirector: Wandering Horde Spawn Finished \(all mobs spawned\)\.$',
                                       'to_call'  : [ ] },
            'AI wanderer player'   : { 'to_match' : self.match_prefix + r'INF AIDirector: Spawning wandering horde moving towards player \'\[type=EntityPlayer, name=.*, id=[\d]+\]\'$',
                                       'to_call'  : [ ] },
            'AI wander remove'     : { 'to_match' : self.match_prefix + r'INF AIDirector: wandering horde zombie \'[type=[\w]+, name=[\w]+, id=[\d]+\]\' is being removed from horde control.$',
                                       'to_call'  : [ ] },
            'AI wander stop'       : { 'to_match' : self.match_prefix + r'INF AIDirector: wandering horde zombie \'\[type=.*, name=.*, id=[\d]+\]\' has wandered long enough and is going to endstop now.$',
                                       'to_call'  : [ ] },
            'AI wander trouble'    : { 'to_match' : self.match_prefix + r'INF AIDirector: wandering horde zombie \'\[type=.*, name=.*, id=[\d]\]\' reached pitstop and will wander around for awhile looking for trouble.$',
                                       'to_call'  : [ ] },
            'allowing player'      : { 'to_match' : self.match_prefix + r'INF Allowing player with id [\d]+$',
                                       'to_call'  : [ ] },
            'behaviour'            : { 'to_match' : r'The referenced script on this Behaviour is missing!$',
                                       'to_call'  : [ ] },
            'biome animal'         : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ AnimalsAll_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome animalSmall'    : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'AnimalsSmall_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome animalSmall zom': { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'AnimalsSmall_Any: c=[\d]+/r=[\d]+ ZombiesAll_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome ani zom'       : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'AnimalsAll_Any: c=[\d]+/r=[\d]+ ZombiesAll_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome ani zom snow'  : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'AnimalsAll_Any: c=[\d]+/r=[\d]+ SnowZombies_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome sani zom'      : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'AnimalsSmall_Any: c=[\d]+/r=[\d]+ ZombiesAll_any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome snowzom'       : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned' + \
                                      r' [\w\d]+ pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                      r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ SnowZombies_Any: c=[\d]+/r=[\d]+$',
                                      'to_call'  : [ ] },
            'biomed zom'          : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned' + \
                                      r' [\w\d]+ pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                      r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ZombiesAll_Any: c=[\d]+/r=[\d]+$',
                                      'to_call'  : [ ] },
            'biome zom ani'       : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'ZombiesAll_Any: c=[\d]+/r=[\d]+ AnimalsAll_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome zom ani snow'  : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'SnowZombies_Any: c=[\d]+/r=[\d]+ AnimalsAll_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome zom small ani' : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'ZombiesAll_Any: c=[\d]+/r=[\d]+ AnimalsSmall_Any: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome waste day'      : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'ZombiesWasteland_Day: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome waste day night': { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'ZombiesWasteland_Day: c=[\d]+/r=[\d]+ ZombiesWastelandNight_Night: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome waste night'    : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'ZombiesWastelandNight_Night: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'biome waste nit day'  : { 'to_match' : self.match_prefix + r'INF BiomeSpawnManager spawned ' + \
                                       r'.* pos=' + self.match_string_pos + r' id=[\d]+ CBD=BiomeId' + \
                                       r'=[\d]+ XZ=[+-]*[\d]+/[+-]*[\d]+ ' + \
                                       r'ZombiesWastelandNight_Night: c=[\d]+/r=[\d]+ ZombiesWasteland_Day: c=[\d]+/r=[\d]+$',
                                       'to_call'  : [ ] },
            'chunks saved'         : { 'to_match' : r'.* INF Saving (.*) of chunks took (.*)ms',
                                       'to_call'  : [ ] },
            'claim finished'       : { 'to_match' : r'Total of ([\d]+) keystones in the game',
                                       'to_call'  : [ self.framework.world_state.buffer_claimstones ] },
            'claim player'         : { 'to_match' : r'Player ".* \(([\d]+)\)" owns ([\d]+) ' + \
                                       r'keystones \(protected: [\w]+, current hardness multiplier: [\d]+\)',
                                       'to_call'  : [ self.framework.world_state.buffer_claimstones ] },
            'claim stone'          : { 'to_match' : r'\(([-+]*[\d]*), ([-+]*[\d]*), ([-+]*[\d]*)\)$',
                                       'to_call'  : [ self.framework.world_state.buffer_claimstones ] },
            'couldnt RPC'          : { 'to_match' : r'^Couldn\'t send RPC function \'RPC_RawData\'$',
                                       'to_call'  : [ ] },
            'created new player'   : { 'to_match' : self.match_prefix + r'INF Created new player entry for' + \
                                       r' ID: [\d]+$',
                                       'to_call'  : [ ] },
            'deny match'           : { 'to_match' : r'(.*) INF Player (.*) denied: ' + \
                                       r'(.*) has been banned until (.*)',
                                       'to_call'  : [ self.framework.game_events.player_denied ] },
            'denying command'      : { 'to_match' : self.match_prefix + r'INF Denying command \'(.*)\' from client (.*)$',
                                       'to_call'  : [ self.framework.server.console_command ] },
            'EAC backend conn'     : { 'to_match' : self.match_prefix + r'INF \[EAC\] Log: Backend connection established\.$',
                                       'to_call'  : [ ] },
            'EAC callback'         : { 'to_match' : self.match_prefix + r'INF \[EAC\] UserStatusHandler callback.'+\
                                       r' Status: UserAuthenticated GUID: [\d]+ ReqKick: [\w]+ Message:.*$',
                                       'to_call'  : [ ] },
            'EAC free user'        : { 'to_match' : r'INF \[EAC\] FreeUser \(.*\)',
                                       'to_call'  : [ ] },
            'EAC kicking player'   : { 'to_match' : self.match_prefix + r'Kicking player: Kicked by EAC. ' + \
                                       r'Please check if you started the game with AntiCheat protection ' + \
                                       r'software enabled$',
                                       'to_call'  : [ ] },
            'EAC log conn lost'    : { 'to_match' : self.match_prefix + r'INF \[EAC\] Log: User EAC client connection lost: [\d]+$',
                                       'to_call'  : [ ] },
            'EAC log dconn'         : { 'to_match' : self.match_prefix + r'INF \[EAC\] Log: User without EAC connection: [\d]+. User status: Disconnected$',
                                       'to_call'  : [ ] },
            'EAC Auth'             : { 'to_match' : self.match_prefix + r'INF \[Steamworks\.NET\] Authenticating player: [\w]+ SteamId: [\d]+ TicketLen: [\d]+ Result: k_EBeginAuthSessionResultOK$',
                                       'to_call'  : [ ] },
            'EAC package'          : { 'to_match' : self.match_prefix + r'ERR \[Steamworks\.NET\] NET: Could not send package to client [\d]+$',
                                       'to_call'  : [ ] },
            'EAC status change'    : { 'to_match' : self.match_prefix + r'INF \[EAC\] Log: User status changed' + \
                                       r': [\d]+. Status: Authenticated Message: N/A$',
                                       'to_call'  : [ ] },
            'EAC unregister'       : { 'to_match' : self.match_prefix + r'INF \[EAC\] Log: User unregistered. GUID: [\d]+$',
                                       'to_call'  : [ ] },
            'empty line'           : { 'to_match' : r'^$',
                                       'to_call'  : [ ] },
            'ERROR'                : { 'to_match' : r'\*\*\* ERROR: unknown command \'(.*)\'',
                                       'to_call'  : [ self.output_guard_error] },
            'executing cmd give'   : { 'to_match' : self.match_prefix + r'INF Executing command \'give ' + \
                                       r'[\d]+ [\w\d]+ [\d]+\' by Telnet from ' + self.match_string_ip + \
                                       r':[\d]+$',
                                       'to_call'  : [ ] },
            'executing cmd se'     : { 'to_match' : self.match_prefix + r'INF Executing command \'se ' + \
                                       r'[\d]+ [\d]+\' by Telnet from ' + self.match_string_ip + \
                                       r':[\d]+$',
                                       'to_call'  : [ ] },
            'executing version'    : { 'to_match' : self.match_prefix + r'INF Executing command \'version\' from client [\d]+$',
                                       'to_call'  : [ ] },
            'failed set triangles' : { 'to_match' : r'Failed setting triangles. Some indices are referencing out of bounds vertices. IndexCount: [\d]+, VertexCount: [\d]+$',
                                       'to_call'  : [ ] },
            'failed extract'       : { 'to_match' : r'Failed to extract collision data: Submesh [\d]+ uses unsupported primitive type "Unknown type". Please use either "TriangleStrip" or "Triangles". Mesh asset path "" Mesh name ""$',
                                       'to_call'  : [ ] },
            'failed mesh'          : { 'to_match' : r'Failed getting triangles. Submesh [\d]+ has no indices. Mesh asset path "" Mesh name ""$',
                                       'to_call'  : [ ] },
            'falling tree'         : { 'to_match' : r'^[\d]+. id=[\d]+, FallingTree_[\d]+' + \
                                       r' \(EntityFallingTree\), pos=' +self.match_string_pos + r', rot=' + \
                                       self.match_string_pos + r', lifetime=[\d]+\.[\d]+, remote=[\w]+, ' + \
                                       r'dead=[\w]+,$',
                                       'to_call'  : [ self.framework.game_events.tree_felled ] }, 
            'fell off world'       : { 'to_match' : self.match_prefix + r'WRN Entity \[type=.*, name=.*' +\
                                       r', id=[\d]+\] fell off the world, id=[\d]+ pos=' + \
                                       self.match_string_pos + r'$',
                                       'to_call'  : [ ] },
            'block fell off'       : { 'to_match' : self.match_prefix + r'WRN Entity FallingBlock_[\d]+ \(EntityFallingBlock\) fell off the world, id=[\d]+ pos=' + self.match_string_pos + r'$',
                                       'to_call'  : [ ] },
            'could not save file'  : { 'to_match' : self.match_prefix + r'ERR Could not save file \'.*\': Sharing violation on path .*$',
                                       'to_call'  : [ ] },
            'item fell off'        : { 'to_match' : self.match_prefix + r'WRN Entity Item_([\d]+) \(EntityItem\) ' + \
                                       r'fell off the world, id=([\d]+) pos=' + self.match_string_pos + r'$',
                                       'to_call'  : [ ] },
            'gmsg'                 : { 'to_match' : self.match_string_date + r' INF GMSG: (.*: .*)$',
                                       'to_call'  : [ self.advise_deprecation_chat ] },
            'gt command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'gt\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'gt command output'    : { 'to_match' : r'Day ([0-9]+), ([0-9]{2}):([0-9]{2})',
                                       'to_call'  : [ self.framework.world_state.process_gt ] },
            'header  0'            : { 'to_match' : r'^\*\*\* Connected with 7DTD server\.$',
                                       'to_call'  : [ ] },
            'header  1'            : { 'to_match' : r'^\*\*\* Server version: Alpha [\d]+\.[\d]+ \(.*\) Compatibility Version: Alpha [\d]+\.[\d]+.*$',
                                       'to_call'  : [ ] },
            'header  2'            : { 'to_match' : r'^\*\*\* Dedicated server only build$',
                                       'to_call'  : [ ] },
            'header  3'            : { 'to_match' : r'^Server IP:   ' + self.match_string_ip + r'$',
                                       'to_call'  : [ ] },
            'header server ip any' : { 'to_match' : r'^Server IP:   Any$',
                                       'to_call'  : [ ] },
            'header  4'            : { 'to_match' : r'^Server port: [\d]+$',
                                       'to_call'  : [ ] },
            'header  5'            : { 'to_match' : r'^Max players: [\d]+$',
                                       'to_call'  : [ ] },
            'header  6'            : { 'to_match' : r'^Game mode:   GameModeSurvivalMP$',
                                       'to_call'  : [ ] },
            'header  7'            : { 'to_match' : r'^World:       Random Gen$',
                                       'to_call'  : [ ] },
            'header  8'            : { 'to_match' : r'Game name:   (.*)$',
                                       'to_call'  : [ ] },
            'header  9'            : { 'to_match' : r'^Difficulty:  [\d]+$',
                                       'to_call'  : [ ] },
            'header 10'            : { 'to_match' : r'Press \'help\' to get a list of all commands\. Press ' + \
                                       r'\'exit\' to end session.',
                                       'to_call'  : [ ] },
            'header A12'           : { 'to_match' : '\*\*\* Server version: Alpha 12 \(b56\) Compatibility Version: Alpha 12$',
                                       'to_call'  : [ ] },
            'icon nof found'       : { 'to_match' : self.match_prefix + r'INF Web:IconHandler:FileNotFound: ".*"$',
                                       'to_call'  : [ ] },
            'static not found'     : { 'to_match' : self.match_prefix + r'INF Web:Static:FileNotFound: ".*" @ ".*"$',
                                       'to_call'  : [ ] },
            'instantiate'          : { 'to_match' : self.match_prefix + r'WRN InstantiateEntities: ignoring [\d]+ as it is already added\.$',
                                       'to_call'  : [ ] },
            'inventory belt/bag'   : { 'to_match' : r'([\w]+) of player (.*):$',
                                       'to_call'  : [ self.framework.world_state.update_inventory ] },
            'inventory item'       : { 'to_match' : r'^Slot ([\d]+): ([\d]+) \* (.*)$',
                                       'to_call'  : [ self.framework.world_state.update_inventory ] },
            'IOException'          : { 'to_match' : self.match_prefix + r'ERR IOException in ReadLine: Read failure$',
                                       'to_call'  : [ ] },
            'item dropped'         : { 'to_match' : r'^Dropped item$',
                                       'to_call'  : [ ] },
            'kicking executing'    : { 'to_match' : self.match_prefix + r'INF Executing command \'kick' + \
                                       r' [\d]+ .*\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'kicking player'       : { 'to_match' : self.match_prefix + r'INF Kicking player: .*$',
                                       'to_call'  : [ ] },
            'gg executing'         : { 'to_match' : self.match_prefix + r'INF Executing command \'gg (.*)\' from client ([\d]+)$',
                                       'to_call'  : [ self.admin_command_mod ] },
            'le command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'le\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'le output'            : { 'to_match' : r'^[\d]+\. id=([\d]+), \[type=[\w]+, name=(.*),' +\
                                       r' id=[\d]+\], pos=' + self.match_string_pos + r', rot=' + \
                                       self.match_string_pos + r', lifetime=(.*), remote=([\w]+),' + \
                                       r' dead=([\w]+), health=([\d]+)',
                                       'to_call'  : [ self.framework.world_state.buffer_le ] },
            'le item output'       : { 'to_match' : r'^[\d]+\. id=([\d]+), Item_[\d]+ \(EntityItem\), ' + \
                                       r'pos=' + self.match_string_pos + r', rot=' + \
                                       self.match_string_pos + r', lifetime=(.*), remote=([\w])+,' + \
                                       r' dead=([\w]+),$',
                                       'to_call'  : [ ] },
            'le falling output'    : { 'to_match' : r'^[\d]+\. id=([\d]+), FallingBlock_[\d]+ \(EntityFallingBlo' +\
                                       r'ck\), pos=' + self.match_string_pos + r', rot=' + self.match_string_pos + \
                                       r', lifetime=(.*), remote=([\w])+, dead=([\w]+),$',
                                       'to_call'  : [ ] },
            'llp executing'        : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'llp\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'loglevel executing'   : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'loglevel [\w]{3} [\w]+\' by Telnet from ' + \
                                       self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'loglevels enable'     : { 'to_match' : r'^[\w]+abling all loglevels on this connection.$',
                                       'to_call'  : [ ] },
            'lp command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'lp\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'lp output'            : { 'to_match' : r'^[\d]+\. id=([\d]+), (.*), pos=' + \
                                       self.match_string_pos + r', rot=' + self.match_string_pos + \
                                       r', remote=([\w]+), health=([\d]+), deaths=([\d]+), zombies=([\d]+), ' + \
                                       r'players=([\d]+), score=([\d]+), level=(1), steamid=([\d]+), ip=' + \
                                       self.match_string_ip + r', ping=([\d]+)',
                                       'to_call'  : [ self.command_lp_output_parser, self.framework.world_state.buffer_lp ] },
            'le/lp output footer'  : { 'to_match' : r'^Total of ([\d]+) in the game$',
                                       'to_call'  : [ self.framework.world_state.footer_lp ] },
            'mem output'           : { 'to_match' : r'[0-9]{4}-[0-9]{2}-[0-9]{2}.* INF Time: ([0-9]+.[0-9]+)m ' + \
                                       r'FPS: ([0-9]+.[0-9]+) Heap: ([0-9]+.[0-9]+)MB Max: ([0-9]+.[0-9]+)MB ' + \
                                       r'Chunks: ([0-9]+) CGO: ([0-9]+) Ply: ([0-9]+) Zom: (.*) Ent: ([\d]+) ' + \
                                       r'\(([\d]+)\) Items: ([0-9]+)',
                                       'to_call'  : [ self.framework.world_state.update_mem ] },
            'message player'       : { 'to_match' : r'Message to player ".*" sent with sender "Server"',
                                       'to_call'  : [ ] },
            'not found'            : { 'to_match' : r'^Playername or entity ID not found.$',
                                       'to_call'  : [ ] },
            'player created'       : { 'to_match' : self.match_prefix + r'INF Created player with id=([\d]+)$',
                                       'to_call'  : [ self.framework.game_events.player_created ] },
            'player joined'        : { 'to_match' : self.match_prefix + 'INF GMSG: .* joined the game',
                                       'to_call'  : [ ] },
            'player kicked'        : { 'to_match' : self.match_prefix + r'INF Executing command \'kick [\d]+\'' + \
                                       r' by Telnet from ' + self.match_string_ip + ':[\d]+$',
                                       'to_call'  : [ ] },
            'playerlogin'          : { 'to_match' : self.match_prefix + r'INF PlayerLogin: .*/Alpha [\d]+\.[\d]+$',
                                       'to_call'  : [ ] },
            'playername not found' : { 'to_match' : r'^Playername or entity/steamid id not found$',
                                       'to_call'  : [ ] },
            'player offline'       : { 'to_match' : self.match_prefix + r'INF Player set to offline: [\d]+$',
                                       'to_call'  : [ ] },
            'player online'        : { 'to_match' : self.match_prefix + r'INF Player set to online' + \
                                       r': ([\d]+)$',
                                       'to_call'  : [ self.framework.server.set_steamid_online ] },
            'player connected'     : { 'to_match' : self.match_prefix + r'INF Player connected, entityid=[\d]+, ' +\
                                       r'name=.*, steamid=[\d]+, ip=' + self.match_string_ip + r'$',
                                       'to_call'  : [ ] },
            'player disconnected'  : { 'to_match' : self.match_prefix + r'INF Player disconnected: EntityID=' + \
                                       r'-*[\d]+, PlayerID=\'[\d]+\', OwnerID=\'[\d]+\', PlayerName=\'.*\'$',
                                       'to_call'  : [ ] },
            'player cdonn after'   : { 'to_match' : self.match_prefix + r'INF Player .* disconnected after [\d]+\.[\d] minutes$',
                                       'to_call'  : [ ] },
            'player disconn error' : { 'to_match' : self.match_prefix + r'ERR DisconnectClient: Player ' + \
                                       r'[\d]+ not found$',
                                       'to_call'  : [ ] },
            'player dconn NET'     : { 'to_match' : self.match_prefix + r'INF \[NET\] Player disconnected: ' + \
                                       r'EntityID=' + \
                                       r'-*[\d]+, PlayerID=\'[\d]+\', OwnerID=\'[\d]+\', PlayerName=\'.*\'$',
                                       'to_call'  : [ ] },
            'player dconn NET2'    : { 'to_match' : self.match_prefix + r'INF \[NET\] PlayerDisconnected ' + \
                                       r'EntityID=' + \
                                       r'-*[\d]+, PlayerID=\'([\d]+)\', OwnerID=\'[\d]+\', PlayerName=\'(.*)\'$',
                                       'to_call'  : [ self.framework.game_events.player_disconnected ] },
            'player died'          : { 'to_match' : self.match_prefix + r'INF GMSG: Player (.*) died$',
                                       'to_call'  : [ self.framework.game_events.player_died ] },
            'player kill'          : { 'to_match' : self.match_prefix + r'INF GMSG: Player (.*)' + \
                                       r' eliminated Player (.*)',
                                       'to_call'  : [ self.framework.game_events.player_kill ] },
            'player left'          : { 'to_match' : self.match_prefix + r'INF GMSG: (.*) left the game$',
                                       'to_call'  : [ self.framework.game_events.player_left ] },
            'player login'         : { 'to_match' : self.match_prefix + r'INF PlayerLogin: .*/Alpha 11\.6$',
                                       'to_call'  : [ ] },
            'player req spawn'     : { 'to_match' : self.match_prefix + r'INF RequestToSpawnPlayer: [\d]+, ' + \
                                       r'.*, [\d]+$',
                                       'to_call'  : [ ] },
            'pm executing'         : { 'to_match' : r'^' + self.match_string_date + r' INF Executing command' + \
                                       r' \'pm (.*) (.*)\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ self.command_pm_executing_parser ] },
            'registering player'   : { 'to_match' : self.match_prefix + r'INF \[EAC\] Registering user: id=[\d]+,'+\
                                       r' owner=[\d]+$',
                                       'to_call'  : [ ] },
            'removing entity'      : { 'to_match' : self.match_prefix + r'INF Removing observed entity [\d]+',
                                       'to_call'  : [ ] },
            'request to enter'     : { 'to_match' : self.match_prefix + r'INF RequestToEnterGame: [\d]+/.*$',
                                       'to_call'  : [ ] },
            'saveworld'            : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'saveworld\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'si command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'si [\d]+\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'say executing'        : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'say ".*"\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'socket exception'     : { 'to_match' : self.match_prefix + r'SocketException: An established connection was aborted by the software in your host machine.',
                                       'to_call'  : [ ] },
            'spawn feral horde'    : { 'to_match' : self.match_prefix + r'INF Spawning Feral Horde\.$',
                                       'to_call'  : [ ] },
            'spawn night horde'    : { 'to_match' : r'^' + self.match_string_date + \
                                       r' INF Spawning Night Horde for day [\d]+',
                                       'to_call'  : [ ] },
            'spawn wander horde'   : { 'to_match' : self.match_prefix + r'INF Spawning Wandering Horde.$',
                                       'to_call'  : [ ] },
            'spawned'              : { 'to_match' : r'^' + self.match_string_date + r' INF Spawned ' + \
                                       r'\[type=[\w]+, name=(.*), id=[\d]+\] at ' + \
                                       self.match_string_pos + r' Day=[\d]+ TotalInWave=[\d]+ CurrentWave=[\d]+$',
                                       'to_call'  : [ ] },
            'spawn ent wrong pos'  : { 'to_match' : self.match_prefix + r'WRN Spawned entity with wrong pos: Item_([\d]+) \((EntityItem)\) id=([\d]+) pos=' + self.match_string_pos + r'$',
                                       'to_call'  : [ self.framework.world_state.buffer_shop_item ] },
            'spawn output'         : { 'to_match' : r'^Spawned [\w\d]+$',
                                       'to_call'  : [ ] },
            'spider spawn horde'   : { 'to_match' : self.match_prefix + r'INF Spider scout spawned a zombie' + \
                                       r' horde!$',
                                       'to_call'  : [ ] },
            'steam auth ()'        : { 'to_match' : self.match_prefix + r'INF \[Steamworks.NET\] Auth\.' + \
                                       r'AuthenticateUser\(\)$',
                                       'to_call'  : [ ] },
            'steam auth'           : { 'to_match' : self.match_prefix + r'INF \[Steamworks\.NET\] Authent' + \
                                       r'icating player: .* SteamId: [\d]+ TicketLen: [\d]+ Result: ' + \
                                       r'k_EBeginAuthSessionResultOK$',
                                       'to_call'  : [ ] },
            'steam auth callback'  : { 'to_match' : self.match_prefix + r'INF \[Steamworks.NET\] ' + \
                                       r'Authentication callback\. ID: [\d]+, owner: [\d]+, result: .*$',
                                       'to_call'  : [ ] },
            'steam drop client'    : { 'to_match' : self.match_prefix + r'INF \[Steamworks\.NET\] NET: Dropping client: [\d]+$',
                                       'to_call'  : [ ] },
            'steam kick'           : { 'to_match' : self.match_prefix + r'INF \[Steamworks\.NET\] Kick player for invalid login: [\d]+ .*$',
                                       'to_call'  : [ ] },
            'steam player connect' : { 'to_match' : self.match_prefix + r'INF \[NET\] PlayerConnected ' + \
                                       r'EntityID=-1, PlayerID=\'\', OwnerID=\'\', PlayerName=\'\'$',
                                       'to_call'  : [ ] },
            'supply crate'         : { 'to_match' : self.match_prefix + r'INF AIAirDrop: Spawned supply ' + \
                                       r'crate @ \(' + self.match_string_pos + r'\)$',
                                       'to_call'  : [ ] },
            'supply plane'         : { 'to_match' : r'[\d]+\. id=[\d]+, GameObject (EntitySupplyPlane), pos=' +\
                                       self.match_string_pos + r', rot=' + self.match_string_pos + \
                                       r', lifetime=float.Max, remote=False, dead=False,$',
                                       'to_call'  : [ ] },
            'telnet closed'        : { 'to_match' : self.match_prefix + r'INF Telnet connection closed: ' +\
                                       self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'wave spawn'           : { 'to_match' : r'^' + self.match_string_date + r' INF Spawning this wave:' +\
                                       r' ([\d]+)',
                                       'to_call'  : [ ] },
            'wave start'           : { 'to_match' : r'^' + self.match_string_date + r' INF Start a new wave ' + \
                                       r'\'[\w]+\'\. timeout=[\d]+s$',
                                       'to_call'  : [ ] },
            'telnet conn block'    : { 'to_match' : self.match_prefix + r'INF Telnet connection closed for too many login attempts: ' + self.match_string_ip + ':[\d]+$',
                                       'to_call'  : [ ] },
            'telnet conn from'     : { 'to_match' : self.match_prefix + r'INF Telnet connection from: ' + \
                                       self.match_string_ip + ':[\d]+$',
                                       'to_call'  : [ ] },
            'telnet thread exit'   : { 'to_match' : '^' + self.match_string_date + \
                                       r' INF Exited thread TelnetClient[\w]+_' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'telnet thread start r': { 'to_match' : '^' + self.match_string_date + \
                                       r' INF Started thread TelnetClientReceive_' + self.match_string_ip + \
                                       r':[\d]+$',
                                       'to_call'  : [ ] },
            'telnet thread start s': { 'to_match' : '^' + self.match_string_date + \
                                       r' INF Started thread TelnetClientSend_' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'token length'         : { 'to_match' : self.match_prefix + r'INF Token length: [\d]+$',
                                       'to_call'  : [ ] },
            'tp command executing' : { 'to_match' : self.match_string_date + \
                                       r' INF Executing command \'teleportplayer ([\d]+) ([+-]*[\d]+) ' + \
                                       r'([+-]*[\d]+) ([+-]*[\d]+)\' by Telnet from ' + \
                                       self.match_string_ip + ':([\d]+)',
                                       'to_call'  : [ ] },
            'version'              : { 'to_match' : r'^' + self.match_string_date + r' INF Executing ' + \
                                       r'command \'version\' by Telnet from ' + self.match_string_ip + r':[\d]+$',
                                       'to_call'  : [ ] },
            'exception sharing'    : { 'to_match' : r'IOException: Sharing violation on path .*',
                                       'to_call'  : [ self.framework.quiet_listener ] },
        }
        # must run after self.telnet_output_matchers is defined
        for key in self.telnet_output_matchers.keys ( ):
            self.matchers [ key ] = {
                'matcher' : re.compile ( self.telnet_output_matchers [ key ] [ 'to_match' ] ),
                'callers' : self.telnet_output_matchers [ key ] [ 'to_call' ] }
        
    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        while ( self.shutdown == False ):
            
            line = self.dequeue ( )
            self.log.debug ( "dequeued: '{}'.".format ( line [ 'text' ]) ) 
            
            any_match = False
            for key in self.matchers.keys ( ):
                match = self.matchers [ key ] [ 'matcher' ].search ( line [ 'text' ] )
                if match:
                    any_match = True
                    matched_key = key
                    match_timestamp = time.time ( )
                    self.log.debug ( "{} groups = {}.".format ( key, match.groups ( ) ) )
                    for caller in self.matchers [ key ] [ 'callers' ]:
                        self.log.debug ( "{} calls {}.".format ( key, caller ) )
                        try:
                            caller ( match.groups ( ) )
                        except Exception as e:
                            self.log.error ( "Exception in {} ( match.groups ( ) ): {}".format ( str ( caller ),
                                                                                                 e ) )
                        self.log.debug ( "{} called {} and finished.".format ( key, caller ) )

            if not any_match:
                self.log.info ( "Unparsed output: '{:s}'.".format ( line [ 'text' ] ) )
                continue

            match_delay = time.time ( ) - match_timestamp
            delay = time.time ( ) - line [ 'timestamp' ]
            if delay > 15:
                self.log.info ( "Line matched {} in {:.1f}s, parsed in {:.1f}.".format ( matched_key,
                                                                                         match_delay,
                                                                                         delay ) )
                if matched_key == 'gt command executing':
                    self.framework.world_state.gt_lag += 0.1
                    self.log.info ( "gt_lag = {:.1f}".format ( self.framework.world_state.gt_lag ) )
                if matched_key == 'le command executing' or matched_key == 'le_output':
                    self.framework.world_state.le_lag += 0.1
                    self.log.info ( "le_lag = {:.1f}".format ( self.framework.world_state.le_lag ) )
                if matched_key == 'lp command executing' or matched_key == 'lp output':
                    self.framework.world_state.lp_lag += 0.1
                    self.log.info ( "lp_lag = {:.1f}".format ( self.framework.world_state.lp_lag ) )

    def stop ( self ):
        self.shutdown = True

    # API

    def enqueue ( self, text ):
        self.lock_queue ( )
        self.queue.append ( { 'text'      : text,
                              'timestamp' : time.time ( ) } )
        self.unlock_queue ( )

    # \API

    def admin_command_mod ( self, match ):
        refactored_match = list ( match )
        player = self.framework.server.get_player ( int ( refactored_match [ 8 ] ) )
        if not player:
            self.log.error ( "Could not find player for match '{}'.".format ( match ) )
            return
        temp = refactored_match [ 7 ]
        refactored_match [ 7 ] = "{}: {}".format ( player.name, temp )
        self.log.info ( "refactored_match [ 7 ] = {}".format ( refactored_match [ 7 ] ) )
        self.framework.server.parse_gmsg ( tuple ( refactored_match ) )

    def advise_deprecation_chat ( self, match ):
        if match [ 7 ] [ : len ( "Server: /" ) ] == "Server: /":
            self.log.info ( "Server chat command '{}' detected.".format ( match [ 7 ] [ len ( "Server: " ) : ] ) )
            self.log.info ( "CHAT {}".format ( match [ 7 ] ) )
            refactored_match = list ( match )
            refactored_match.append ( "Server" )
            self.framework.server.parse_gmsg ( tuple ( refactored_match ) )
            return
        if match [ 7 ] [ : len ( "Server: " ) ] == "Server: ":
            self.log.debug ( "Server chat message '{}' detected.".format ( match [ 7 ] [ len ( "Server: " ) : ] ) )
            self.log.info ( "CHAT {}".format ( match [ 7 ] ) )
            return       

        player = self.framework.server.get_player ( match [ 7 ].split ( ": " ) [ 0 ] )
        if not player:
            self.log.warning ( "deprecation: could not find player '{}'.".format ( 
                    match [ 7 ].split ( ": " ) [ 0 ] ) )
        command = match [ 7 ].split ( ": " ) [ 1 ]
        if command [ 0 ] != "/":
            self.log.info ( "CHAT {}".format ( match [ 7 ] ) )
            self.log.debug ( "Going for a translation." )
            if 'translator'  in self.framework.mods.keys ( ):
                translator = self.framework.mods [ 'translator' ] [ 'reference' ]
                if translator.enabled:
                    #translator.translate ( msg_origin, msg_content [ : ] )
                    translator.translate ( player.name, match [ 7 ] [ len ( player.name + ": " ) : ] )
                else:
                    self.log.info ( "translate not enabled" )
            else:
                self.log.info ( "translate module not loaded" )

            return
        if not player:
            self.log.info ( "CHAT {}".format ( match [ 7 ] ) )
            self.log.error ( "Unkown player from match '{}' on advise_deprecation_chat.".format ( match ) )
            return
        self.log.info ( "CHAT {}".format ( match [ 7 ] ) )
        self.framework.console.pm ( player, "The commands now go in the console, prefixing with gg (example: `gg /list auger)." )

    def command_lp_output_parser ( self, match ):
        self.log.debug ( str ( match ) )
        self.framework.server.update_id ( match )

    def command_pm_executing_parser ( self, match ):
        self.log.debug ( "cmd pm exec parser: {}".format ( match ) )
        if self.framework.preferences.mod_ip == match [ 9 ]:
            self.log.debug ( "pm was from mod" )
            now = time.time ( )
            old_lag = self.framework.console.pm_lag
            new_lag = now - self.framework.console.pm_latest_call
            if new_lag >= old_lag:
                self.framework.console.pm_lag += 0.1
            else:
                self.framework.console.pm_lag -= 0.1
            self.log.debug ( 'pm executing' )
            if self.framework.console.pm_lag > 5:
                self.log.info ( "pm lag: {:.1f}s.".format ( self.framework.console.pm_lag ) )

    def dequeue ( self ):
        self.lock_queue ( )
        while len ( self.queue ) < 1:
            self.unlock_queue ( )
            time.sleep ( 0.1 )
            self.lock_queue ( )
        popped = self.queue.pop ( 0 )
        self.unlock_queue ( )
        return popped

    def llp_claim_player ( self, matcher ):
        self.log.info ( "llp_claim_player {}".format ( matcher [ 0 ] ) )
        player = self.framework.server.get_player ( int ( matcher [ 1 ] ) )
        if player:
            self.llp_current_player = player
        else:
            self.llp_current_player = None

    def llp_claim_stone ( self, matcher ):
        places = self.framework.mods [ 'place_protection' ] [ 'reference' ].places
        self.log.info ( "llp_claim_stone {}".format ( matcher ) )
        if self.llp_current_player:
            for place_key in places.keys ( ):
                distance_place = self.framework.utils.calculate_distance ( ( float ( matcher [ 0 ] ),
                                                                             float ( matcher [ 2 ] ) ),
                                                                           places [ place_key ] [ 0 ] )
                if distance_place < places [ place_key ] [ 1 ] + self.framework.preferences.home_radius:
                    return
            claimstones = self.framework.world_state.get_claimstones ( )
            if self.llp_current_player.steamid in claimstones.keys ( ):
                claimstones [ self.llp_current_player.steamid ].append ( ( float ( matcher [ 0 ] ),
                                                                           float ( matcher [ 2 ] ),
                                                                           float ( matcher [ 1 ] ) ) )
            else:
                claimstones [ self.llp_current_player.steamid ] = [ ( float ( matcher [ 0 ] ),
                                                                      float ( matcher [ 2 ] ),
                                                                      float ( matcher [ 1 ] ) ) ]
            self.framework.world_state.let_claimstones ( )
        else:
            self.log.debug ( "No player attached to this claimstone." )
        
    def llp_finished ( self, matcher ):
        self.llp_total_recently_set = True
        
    def lock_queue ( self ):
        callee_class = inspect.stack ( ) [ 1 ] [ 0 ].f_locals [ 'self' ].__class__.__name__
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        begin = time.time ( )
        while self.queue_lock:
            self.log.debug ( "{}.{} wants parser queue lock from {}.".format (
                callee_class, callee, self.queue_lock ) )
            time.sleep ( 0.01 )
            if time.time ( ) - begin > 60:
                break
        self.queue_lock = callee_class + "." + callee
        self.log.debug ( "{:s} got parser queue lock.".format ( callee ) )

    def output_guard_error ( self, matches ):
        """
        When necessary, framework will send an invalid command, so that the game server respond with an error containing the said invalid command string.
        Using that, the framework is able to know when a command sent BEFORE the invalid one has finished.
        Example: the si command can end with any slot, up to the backpack's 31th slot. By sending an invalid command after the si, when the error is sent we know the command is finished.
        """
        command_string = matches [ 0 ]
        self.log.info ( "command_string = '{}'.".format ( command_string ) )

        callbacks = {
            "si" : self.framework.world_state.si_process_guard
            }

        for key in callbacks.keys ( ):
            if command_string [ : len ( key ) ] == key:
                self.log.info ( "output_guard_error matched key of '{}' for matches [ 0 ] = '{}'".format ( 
                        key, matches [ 0 ] ) )
                callbacks [ key ] ( command_string )

    def unlock_queue ( self ):
        callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        self.queue_lock = None
        self.log.debug ( "{:s} unlocked the parser queue.".format ( callee ) )
        
    def timestamp_from_date_prefix ( self, date_matcher_groups ):
        self.log.debug ( date_matcher_groups )
        year = date_matcher_groups [ 0 ]
        month = date_matcher_groups [ 1 ]
        day = date_matcher_groups [ 2 ]
        hour = date_matcher_groups [ 3 ]
        minute = date_matcher_groups [ 4 ]
        second = date_matcher_groups [ 5 ]
        server_time = time.strptime ( "{} {} {} {} {} {}".format (
            year, month, day, hour, minute, second ),
                                      "%Y %m %d %H %M %S" )

        return time.mktime ( server_time )
        
