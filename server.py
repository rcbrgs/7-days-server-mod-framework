"""
The scope for this module is to facilitate actions by a developer or admin. So functionalities that are "one step above" the low-level wrappers belong here. For example, a wrapper around lp doesnt belong here; a wrapper to yield a list of online players does.
"""

import copy
import framework
from framework.player_info import player_info_v5 as player_info
import inspect
import logging
import math
import pickle
import pygeoip
import random
import re
import sys
import threading
import time

class server ( threading.Thread ):
    def __init__ ( self, framework ):
        super ( server, self ).__init__ ( )
        self.daemon = True
        self.log = logging.getLogger ( __name__ )
        self.__version__ = '0.9.0'
        self.changelog = {
            '0.9.0' : "Added parser for lkp output.",
            }
        self.shutdown = False
        
        self.log.info ( "Server module initializing." )

        self.chat = None
        self.clear_online_property = False
        self.entities = { }
        self.entity_db = {
            'animalBear'        : { 'entityid' : 27, 'is_animal' : True,  'is_zombie' : False },
            'animalPig'         : { 'entityid' : 29, 'is_animal' : True,  'is_zombie' : False },
            'animalRabbit'      : { 'entityid' : 28, 'is_animal' : True,  'is_zombie' : False },
            'animalStag'        : { 'entityid' : 26, 'is_animal' : True,  'is_zombie' : False },
            'burntzombie'       : { 'entityid' : 12, 'is_animal' : False, 'is_zombie' : True  },
            'car_Blue'          : { 'entityid' : 22, 'is_animal' : False, 'is_zombie' : False },
            'car_Orange'        : { 'entityid' : 23, 'is_animal' : False, 'is_zombie' : False },
            'car_Red'           : { 'entityid' : 24, 'is_animal' : False, 'is_zombie' : False },
            'car_White'         : { 'entityid' : 25, 'is_animal' : False, 'is_zombie' : False },
            'EntityPlayer'      : { 'entityid' : -1, 'is_animal' : False, 'is_zombie' : False },
            'EntitySupplyPlane' : { 'entityid' : -1, 'is_animal' : False, 'is_zombie' : False },
            'fatzombie'         : { 'entityid' : 19, 'is_animal' : False, 'is_zombie' : True  },
            'fatzombiecop'      : { 'entityid' : 18, 'is_animal' : False, 'is_zombie' : True  },
            'hornet'            : { 'entityid' : 20, 'is_animal' : False, 'is_zombie' : True  },
            'minibike'          : { 'entityid' : 34, 'is_animal' : False, 'is_zombie' : False },
            'sc_General'        : { 'entityid' : 31, 'is_animal' : False, 'is_zombie' : False },
            'snowzombie01'      : { 'entityid' : 8 , 'is_animal' : False, 'is_zombie' : True  },
            'snowzombie02'      : { 'entityid' : 9 , 'is_animal' : False, 'is_zombie' : True  },
            'snowzombie03'      : { 'entityid' : 10, 'is_animal' : False, 'is_zombie' : True  },
            'spiderzombie'      : { 'entityid' : 11, 'is_animal' : False, 'is_zombie' : True  },
            'supplyPlane'       : { 'entityid' : 30, 'is_animal' : False, 'is_zombie' : False },
            'zombie01'          : { 'entityid' : 6 , 'is_animal' : False, 'is_zombie' : True  },
            'zombie02'          : { 'entityid' : 17, 'is_animal' : False, 'is_zombie' : True  },
            'zombie04'          : { 'entityid' : 1 , 'is_animal' : False, 'is_zombie' : True  },
            'zombie05'          : { 'entityid' : 3 , 'is_animal' : False, 'is_zombie' : True  },
            'zombie06'          : { 'entityid' : 4 , 'is_animal' : False, 'is_zombie' : True  },
            'zombie07'          : { 'entityid' : 5 , 'is_animal' : False, 'is_zombie' : True  },
            'zombiecrawler'     : { 'entityid' : 7 , 'is_animal' : False, 'is_zombie' : True  },
            'zombiedog'         : { 'entityid' : 21, 'is_animal' : False, 'is_zombie' : True  },
            'zombieferal'       : { 'entityid' : 2 , 'is_animal' : False, 'is_zombie' : True  },
            'zombiegal01'       : { 'entityid' : 13, 'is_animal' : False, 'is_zombie' : True  },
            'zombiegal02'       : { 'entityid' : 14, 'is_animal' : False, 'is_zombie' : True  },
            'zombiegal03'       : { 'entityid' : 15, 'is_animal' : False, 'is_zombie' : True  },
            'zombiegal04'       : { 'entityid' : 16, 'is_animal' : False, 'is_zombie' : True  },
            'zombieUMAfemale'   : { 'entityid' : 32, 'is_animal' : False, 'is_zombie' : True  },
            'zombieUMAmale'     : { 'entityid' : 33, 'is_animal' : False, 'is_zombie' : True  },
            }
            
        # Other programs might have /keywords that we want to ignore. Put those here.
        self.external_commands = [ 'restart' ]
        self.framework = framework
        self.help_items = {
            'democracy' : ( "Honestly, the admins cannot be online all the time. So veteran"
                            " players can create proposals and vote on those proposals, "
                            "to decide if it is right to punish players after an offense." ),
            'karma' : ( "Karma is a measure of how much we trust you, the player."
                        " You gain 1 karma per hour played. You spend karma to teleport,"
                        " sethome, and other actions." ),
            'night' : ( "Night is when zombies run and you hide. In this server"
                        " it happens between 0h and 6h." ),
            'portal' : ( "Portals allow you to teleport instantly. You can use 'set portal X' to"
                         " create a portal destination, and then 'go X' to teleport there." ),
            'prison' : ( "Or swiss prison will rehabilitate you: if you try to invade bases,"
                         " you go to prison, to meditate on your evil ways. If you kill another"
                         " player, you fo to prison, until we decide you can go outside your cage." ),
            'shop'  : ( "The shop is run by a mighty Ogre. Possible exits are N, E and SE." ),
            }
            
        self.latest_player_db_backup = 0
        self.player_db_save_timestamp = 0
        self.preferences = self.framework.preferences
        self.preteleport_queue = [ ]
        self.preteleport_queue_lock = { 'callee'    : None,
                                        'timeout'   : 10,
                                        'timestamp' : None }

        self.chat_log_file = self.preferences.chat_log_file
        self.player_info_file = self.preferences.player_info_file
        self.geoip = pygeoip.GeoIP ( self.preferences.geoip_file, pygeoip.MEMORY_CACHE )
        
        self.commands = { 'me'          : ( self.command_me,
                                            " /me will print your info." ),
                          'help'        : ( self.command_help,
                                            " /help shows the list of commands." ),
                          'sos'         : ( self.sos,
                                            " /sos will ask players to help you." ),
                          }
        
        file_found = True
        try:
            pickle_file = open ( self.player_info_file, 'rb' )
        except FileNotFoundError as e:
            self.log.error ( "While openeing pickle: {}".format ( e ) )
            self.log.info ( "Creating new player info file." )
            file_found = False

        if ( file_found ):
            self.players_info = pickle.load ( pickle_file )
        else:
            self.players_info = { }

        self.server_uptime = 0.
        self.shutdown_triggered = False
        self.shutdown_warning = None
        self.shutdown_warning_minute = None

    def __del__ ( self ):
        if not self.shutdown:
            self.log.error ( "__del__ being called before stop!" )
            self.shutdown = True
            self.stop ( )

    def run ( self ):
        while not self.shutdown:
            self.log.debug ( "Tick" )
            time.sleep ( self.framework.preferences.loop_wait )

            self.dequeue_preteleport ( )

        if self.chat != None:
            self.chat.close ( )
        self.log.info ( "Saving player db." )
        pickle_file = open ( self.player_info_file, 'wb' )
        pickle.dump ( self.players_info, pickle_file, pickle.HIGHEST_PROTOCOL )
                  
    def command_help ( self, msg_origin, msg_content ):
        player = self.get_player ( msg_origin )
        if not player:
            self.log.error ( "could not get_player for '{}' on command_help".format ( msg_origin ) )
            return
        if len ( msg_content ) > len ( "/help" ):
            predicate = msg_content [ len ( "/help " ) : ]
            for key in self.commands.keys ( ):
                if msg_content [ 6 : ] == key:
                    self.framework.console.pm ( player, self.commands [ key ] [ 1 ] )
                    return
            for mod_key in self.framework.mods.keys ( ):
                mod = self.framework.mods [ mod_key ] [ 'reference' ]
                if not mod.enabled:
                    continue
                for key in mod.commands.keys ( ):
                    if msg_content [ 6 : ] == key:
                        self.framework.console.pm ( player, mod.commands [ key ] [ 1 ] )
                        return
            for help_item in self.help_items.keys ( ):
                if help_item == predicate:
                    self.framework.console.pm ( player, self.help_items [ help_item ] )
                    return
            for mod_key in self.framework.mods.keys ( ):
                mod = self.framework.mods [ mod_key ] [ 'reference' ]
                if not mod.enabled:
                    continue
                if not hasattr ( mod, "help_items" ):
                    continue
                for key in mod.help_items.keys ( ):
                    if key == predicate:
                        self.framework.console.pm ( player, mod.help_items [ key ] )
                        return

        command_list = [ ]
        for key in self.commands.keys ( ):
            command_list.append ( key )
        for mod_key in self.framework.mods:
            mod = self.framework.mods [ mod_key ] [ 'reference' ]
            if not mod.enabled:
                continue
            for key in mod.commands.keys ( ):
                command_list.append ( key )

        help_message = "Available commands: "
        color = "white"
        for mod_key in sorted ( command_list ):
            if color == "white":
                help_message += "[BBBBBB]" + mod_key + "[FFFFFF] "
                color = "blue"
            else:
                help_message += mod_key + " "
                color = "white"
        
        self.framework.console.pm ( player, help_message )
            
    def command_me ( self, player_identifier, message ):
        self.log.debug ( "me: start" )
        player = self.get_player ( player_identifier )
        if player == None:
            self.framework.console.say ( "No such player: %s" % str ( player_identifier ) )
            return
        msg = "%s: " % player.name_sane
        msg += self.geoip.country_code_by_addr ( player.ip )
        self.log.debug ( "me: home" )
        if player.home != None:
            msg += ", home at %s" % ( self.framework.utils.get_map_coordinates ( player.home ) )
            if self.framework.utils.calculate_distance ( self.framework.utils.get_coordinates ( player ),
                                                         player.home ) < self.preferences.home_radius:
                msg += ", inside"
            else:
                msg += ", outside"
        if player.steamid in self.framework.world_state.claimstones.keys ( ):
            msg += ", claims: "
            claim_msg = ""
            for claim in self.framework.world_state.claimstones [ player.steamid ]:
                if claim_msg == "":
                    claim_msg = str ( claim )
                else:
                    claim_msg += ", " + str ( claim )
            msg += claim_msg
        self.log.debug ( "me: languages" )
        if player.languages_spoken:
            msg += ", speaks"
            for language in player.languages_spoken:
                msg += " " + language
        if player.language_preferred:
            msg += ', translation to %s' % player.language_preferred
        msg += ', played %dh' % ( round ( player.online_time / 3600 ) )
        self.log.debug ( "me: pkills" )
        if isinstance ( player.player_kills_explanations, list ):
            msg += ", pkills (total/explained): %d/%d" % (
                player.players, len ( player.player_kills_explanations ) )
        self.log.debug ( "me: karma" )
        msg += ", karma {:d}".format ( player.karma )
        msg += ", cash {:d}".format ( player.cash )
        msg += "."
        self.framework.console.pm ( player, msg )
        self.log.debug ( "me: end" )

    def display_entities ( self ):
        print ( "stal | entty_id | entity_type | lifetime  | remot | dead  | heal | pos" )
        self.wait_entities ( )
        #self.framework.get_ent_lock ( )
        for key in self.entities.keys ( ):
            entity = self.entities [ key ]
            self.log.debug ( str ( entity ) )
            print ( "{: 2.1f} | {: <8d} | {: <11s} | {} | {:5s} | {:5s} | {:4d} | {: 5.1f},{: 5.1f},{: 5.1f}".format (
                time.time ( ) - entity.timestamp,
                entity.entity_id,
                entity.entity_type [ : 11 ],
                entity.lifetime,
                entity.remote,
                entity.dead,
                entity.health,
                entity.pos_x, entity.pos_y, entity.pos_z,
            ) )
        #self.framework.let_ent_lock ( )

    def find_nearest_player ( self, steamid ):
        player_distances = { }
        player_inverted_directions = { }
        distances = [ ]
        origin_x = self.players_info [ steamid ].pos_x
        origin_y = self.players_info [ steamid ].pos_y
        for key in self.players_info.keys ( ):
            if key != steamid:
                if self.players_info [ key ].online == True:
                    helper_x = self.players_info [ key ].pos_x
                    helper_y = self.players_info [ key ].pos_y
                    relative_x = origin_x - self.players_info [ key ].pos_x
                    relative_y = origin_y - self.players_info [ key ].pos_y
                    distance = math.sqrt ( relative_x ** 2 + relative_y ** 2 )
                    player_distances [ key ] = distance
                    distances.append ( distance )
                    acos = math.degrees ( math.acos ( relative_x / distance ) )
                    if ( relative_y < 0 ):
                        acos += 180
                    
                    player_inverted_directions [ key ] = int ( ( acos - 90 ) % 360 )
        min_distance = min ( distances )
        for key in player_distances.keys ( ):
            if player_distances [ key ] == min_distance:
                return ( key, min_distance, player_inverted_directions [ key ] )

    def find_nearest_player_to_position ( self, position ):
        player_distances = { }
        player_inverted_directions = { }
        distances = [ ]
        origin_x = position [ 0 ]
        origin_y = position [ 1 ]
        for key in self.players_info.keys ( ):
            if self.players_info [ key ].online == True:
                helper_x = self.players_info [ key ].pos_x
                helper_y = self.players_info [ key ].pos_y
                relative_x = origin_x - helper_x
                relative_y = origin_y - helper_y
                distance = math.sqrt ( relative_x ** 2 + relative_y ** 2 )
                player_distances [ key ] = distance
                distances.append ( distance )
                acos = math.degrees ( math.acos ( relative_x / distance ) )
                if ( relative_y < 0 ):
                    acos += 180
                    
                player_inverted_directions [ key ] = int ( ( acos - 90 ) % 360 )
        min_distance = min ( distances )
        for key in player_distances.keys ( ):
            if player_distances [ key ] == min_distance:
                return ( key, min_distance, player_inverted_directions [ key ] )

    def get_nearest_animal ( self, player ):
        self.wait_entities ( )
        #self.framework.get_ent_lock ( )
        animal_entities_list = [ ]
        for key in self.entities.keys ( ):
            if self.entity_db [ self.entities [ key ].entity_type ] [ 'is_animal' ]:
                if self.entities [ key ].dead == "False":
                    animal_entities_list.append ( key )
        #self.framework.let_ent_lock ( )
        self.log.info ( "get_nearest_animal: list: {}.".format ( str ( animal_entities_list ) ) ) 
        min_distance = None
        min_entity_id = None
        for entity in animal_entities_list:
            distance = self.framework.utils.calculate_distance ( ( self.entities [ entity ].pos_x,
                                                                   self.entities [ entity ].pos_y,
                                                                   self.entities [ entity ].pos_z ),
                                                                 self.framework.utils.get_coordinates ( player ) )
            self.log.info ( "distance = {}".format ( str ( distance ) ) )
            if not min_distance:
                min_distance = distance
            min_distance = min ( min_distance, distance )
            if min_distance == distance:
                min_entity_id = entity

        if min_entity_id:
            if min_entity_id in self.entities.keys ( ):
                min_type = self.entities [ min_entity_id ].entity_type
                self.log.info ( "min_entity_id = {}, type = {}".format ( min_entity_id, min_type ) )
                return min_entity_id, min_type
        return -1, 'nothing'

    def get_nearest_entity ( self, player ):
        self.wait_entities ( )
        #self.framework.get_ent_lock ( )
        min_distance = None
        min_entity_id = None
        for key in self.entities.keys ( ):
            if self.entities [ key ].dead == "True":
                continue
            distance = self.framework.utils.calculate_distance ( ( self.entities [ key ].pos_x,
                                                                   self.entities [ key ].pos_y,
                                                                   self.entities [ key ].pos_z ),
                                                                 self.framework.utils.get_coordinates ( player ) )
            self.log.debug ( "distance: {}".format ( distance ) )
            if not min_distance:
                min_distance = distance
            min_distance = min ( min_distance, distance )
            if min_distance == distance:
                min_entity_id = key
        self.log.debug ( "nearest: {}".format ( min_distance ) )

        if min_entity_id not in self.entities.keys ( ):
            #self.framework.let_ent_lock ( )
            time.sleep ( 1 )
            self.log.warning ( "Recursively trying to find a near entity." )
            return self.get_nearest_entity ( player )
        
        min_type = self.entities [ min_entity_id ].entity_type
        #self.framework.let_ent_lock ( )
        return min_entity_id, min_type

    def get_nearest_zombie ( self, player ):
        self.log.debug ( "get_nearest_zombie ( {} )".format ( player.name_sane ) )
        #self.wait_entities ( )
        #self.framework.get_ent_lock ( )
        min_distance = None
        min_entity_id = None
        entities = copy.copy ( self.framework.world_state.entities )
        for key in entities.keys ( ):
            if entities [ key ].dead == "True":
                continue
            if entities [ key ].health == 0:
                continue
            if not entities [ key ].entity_type in list ( self.entity_db.keys ( ) ):
                continue
            if not self.entity_db [ entities [ key ].entity_type ] [ 'is_zombie' ]:
                continue
            distance = self.framework.utils.calculate_distance ( ( float ( entities [ key ].pos_x ),
                                                                   float ( entities [ key ].pos_y ),
                                                                   float ( entities [ key ].pos_z ) ),
                                                                 self.framework.utils.get_coordinates ( player ) )
            self.log.debug ( "distance: {}".format ( distance ) )
            if not min_distance:
                min_distance = distance
            min_distance = min ( min_distance, distance )
            if min_distance == distance:
                min_entity_id = key
        self.log.debug ( "nearest: {}".format ( min_distance ) )

        if min_entity_id not in entities.keys ( ):
            self.log.warning ( "No zombie near player." )
            return None, None, None
        
        min_type = entities [ min_entity_id ].entity_type
        #self.framework.let_ent_lock ( )
        return min_distance, min_entity_id, min_type
            
    def get_online_players ( self ):
        result = [ ]
        self.framework.get_db_lock ( )
        for key in self.players_info.keys ( ):
            player = self.players_info [ key ]
            if player.online:
                result.append ( player )
        self.framework.let_db_lock ( )
        return result

    def get_player ( self, player_id ):
        if isinstance ( player_id, player_info ):
            self.log.debug ( "get_player called with player_info argument by %s" %
                             str ( sys._getframe ( ).f_code.co_name ) )
            return player_id
        if isinstance ( player_id, int ):
            if player_id in self.players_info.keys ( ):
                return self.players_info [ player_id ]
            else:
                return None
        if isinstance ( player_id, tuple ):
            try:
                steamid = int ( player_id [ 2 ] )
                self.log.debug ( "Player steamid = {}.".format ( steamid ) )
                if steamid in self.players_info.keys ( ):
                    self.log.debug ( "Player name = {}".format ( self.players_info [ steamid ].name_sane ) )
                    return self.players_info [ steamid ]
                return None
            except:
                self.log.error ( "isinstance ( player, tuple ) with tuple = {}".format ( player_id ) )
                return None
        if not isinstance ( player_id, str ):
            return None
        possibilities = [ ]
        for key in self.players_info.keys ( ):
            if player_id == self.players_info [ key ].name:
                return self.players_info [ key ]
            if player_id.lower ( ) in self.players_info [ key ].name.lower ( ):
                possibilities.append ( key )
        if len ( possibilities ) == 1:
            return self.players_info [ possibilities [ 0 ] ]
        elif len ( possibilities ) > 1:
            self.log.info ( "called from %s" % str ( sys._getframe ( ).f_back.f_code.co_name ) )
            msg = "I can't decide if you mean "
            for entry in possibilities:
                msg += self.players_info [ entry ].name_sane + ", "
            msg = msg [ : -2 ]
            msg += "."
            
            if len ( possibilities ) > 5:
                msg = "I can't decide if you mean "
                for entry in possibilities [ 0 : 2 ]:
                    msg += self.players_info [ entry ].name_sane + ", "
                msg += " or " + str (  len ( possibilities ) - 3 ) + " others."

            self.framework.console.say ( msg )
            self.log.info ( "player_id for mutiple get_player result: {}.".format ( player_id ) )
            return None
        
        self.log.info ( "No player with identifier %s." % str ( player_id ) )
        return None

    def get_player_summary ( self, player ):
        player_line = "{: >4.1f} {:<11s} {:<10d} {: >5.1f} {:>2d}/{:<2d} {:>3d} {: >5d} {: >5d}" .format (
            time.time ( ) - player.timestamp_latest_update,
            str ( player.name_sane [ : 10 ] ),
            player.steamid,
            player.online_time / 3600,
            player.players,
            len ( player.player_kills_explanations ),
            int ( player.karma ),
            int ( player.cash ),
            int ( player.zombies ) )
        return player_line
        
    def get_random_entity ( self ):
        self.wait_entities ( )
        #self.framework.get_ent_lock ( )
        random_index = random.choice ( list ( self.entities.keys ( ) ) )
        random_type = self.entities [ random_index ].entity_type
        #self.framework.let_ent_lock ( )
        return random_index, random_type
    
    def give_cash ( self, player = None, amount = 0 ):
        if not isinstance ( player, player_info ):
            self.log.warning ( "calling give_cash with playerid" )
            player = self.get_player ( player )            
        if amount == 0:
            return
        try:
            self.log.debug ( player.cash )
            player.cash += amount
            self.log.debug ( player.cash )
        except Exception as e:
            self.log.error ( "give_cash: {}".format ( e ) )
        
    def give_karma ( self, player = None, amount = 0 ):
        if amount == 0:
            return
        if player is None:
            return
        try:
            self.log.debug ( player.karma )
            player.karma += amount
            self.log.debug ( player.karma )
        except Exception as e:
            self.log.error ( "give karma {}".format ( e ) )
    
    def give_player_stuff ( self, player, stuff, quantity ):
        msg = 'give ' + str ( player.steamid ) + ' ' + stuff + ' ' + str ( quantity )
        self.log.info ( msg )
        self.framework.console.send ( msg )

    def greet ( self ):
        self.framework.console.say ( "%s module %s loaded." % ( self.__class__.__name__,
                                              self.__version__ ) )
        
    def list_nearby_tracks ( self, position ):
        result = [ ]
        for steamid in self.players_info.keys ( ):
            player = self.players_info [ steamid ]
            now = time.time ( )
            if not isinstance ( player.timestamp_latest_update, float ):
                continue
            if ( now - player.timestamp_latest_update ) > ( 24 * 3600 ):
                continue
            if not isinstance ( player.positions, list ):
                continue
            for track in player.positions:
                self.log.debug ( "distance between %s and %s is < 5?" % (
                    str ( track ), str ( position ) ) )
                if ( abs ( position [ 0 ] - track [ 0 ] ) < 5 and
                     abs ( position [ 1 ] - track [ 1 ] ) < 5 and
                     abs ( position [ 2 ] - track [ 2 ] ) < 5 ):
                    result.append ( player.steamid )
                    break
        return result
            
    def list_online_players ( self ):
        print ( "----+-----------+-----------------+-----+-----+---+-----+-----+" )
        last_lp = self.framework.world_state.latest_lp_call
        while self.framework.world_state.latest_lp_call == last_lp:
            time.sleep ( 0.1 )
        for player in self.get_online_players ( ):
            pos = self.framework.utils.get_coordinates ( player )
            pos_string = "({: >6.0f} {: >6.0f} {: >4.0f})".format ( pos [ 0 ], pos [ 1 ], pos [ 2 ] )
            pos_mod = ""
            if len ( player.positions ) > 1:
                diff_x = player.pos_x - player.positions [ -2 ] [ 0 ]
                diff_y = player.pos_y - player.positions [ -2 ] [ 1 ]
                diff_z = player.pos_z - player.positions [ -2 ] [ 2 ]
                pos_mod = "({: >3.0f} {: >3.0f} {: >3.0f})".format ( diff_x, diff_y, diff_z )
            print ( "{} {} {}".format ( self.get_player_summary ( player ), pos_string, pos_mod ) )

    def mod_status ( self, msg_origin, msg_content ):
        self.greet ( )
        for key in self.framework.mods.keys ( ):
            self.framework.mods [ key ] [ 'reference'].greet ( )

    def offline_player ( self, server_log ):
        self.log.info ( "%s" % server_log )

        player_name = server_log.split ( " INF Player " )
        if len ( player_name ) > 1:
            player_name = player_name [ 1 ].split ( " disconnected after " )
            if len ( player_name ) > 1:
                player_name = player_name [ 0 ]
            else:
                player_name = server_log.split ( "', PlayerName='" )
                if len ( player_name ) > 1:
                    player_name = player_name [ 1 ] [ : -2 ]

        if player_name == "":
            return
        
        self.log.info ( "Trying get_player ( %s )" % str ( player_name ) )
        try:
            player = self.get_player ( player_name )
        except Exception as e:
            self.log.error ( "offline_player ( '%s' ): %s." % ( server_log, str ( e ) ) )
            player = None
            
        if player != None:
            player.online = False
            self.log.info ( "%s.online == %s" % ( player.name_sane, str ( player.online ) ) )
            return
        
    def offline_lagged_players ( self ):
        online_players = self.get_online_players ( )
        self.framework.get_db_lock ( )
        for player in online_players:
            if not player.timestamp_latest_update:
                player.timestamp_latest_update = time.time ( )
            if time.time ( ) - player.timestamp_latest_update > self.framework.world_state.lp_lag * 10:
                player.online = False
        self.framework.let_db_lock ( )

    def console_command ( self, match ):
        refactored_match = list ( match )
        refactored_match [ 7 ] = "{}: {}".format ( match [ 8 ], match [ 7 ] )
        self.parse_gmsg ( tuple ( refactored_match ) )

    def kill_unclaim_and_ban ( self, player ):
        """
        Will sequentially send commands to kill player, rlp its claims, and ban him for 1 year.
        """
        if player == None:
            return
        self.log.warning ( "Killing, rlp and banning player {}.".format ( player.name_sane ) )
        self.framework.console.send ( "kill {}".format ( player.steamid ) )
        self.framework.console.send ( "rlp {}".format ( player.steamid ) )
        self.framework.console.send ( "ban add {} 1 year".format ( player.steamid ) )

    def lkp_output_parser ( self, lkp_matches : tuple ):
        """
        This method's goal is to receive data from a line of lkp output, and feed that info (along some default values) to the player database - if there is no player info about this player already there.

        Parameters:

        * lkp_matches : tuple
            Containing the results of a re matcher. It should be a tuple with the following content (all strings):
            ( name, playerid, steamid, online, ip, playtime minutes, seen year, seen month, seen day, seen hour, seen minute )
        """
        self.log.debug ( "lkp_matches = {}".format ( lkp_matches ) )
        player = self.get_player ( int ( lkp_matches [ 2 ] ) )
        if player:
            self.log.debug ( "Player '{}' is known to mod, ignoring lkp output.".format ( player.name_sane ) )
            return

        self.log.info ( "Updating player db with lkp info for '{}'.".format ( lkp_matches [ 0 ] ) )
        ip = lkp_matches [ 4 ]
        if ip == "":
            ip = "8.8.8.8"
        self.player_info_update ( 
            1,
            lkp_matches [ 3 ],
            int ( lkp_matches [ 1 ] ),
            lkp_matches [ 0 ],
            0,
            0,
            0,
            0,
            ip,
            0,
            0,
            0,
            0,
            int ( lkp_matches [ 2 ] ) )

    def parse_gmsg ( self, match ):
        player = self.get_player ( match [ 8 ] )
            
        if not player:
            self.log.warning ( "No player '{}' exists.".format ( match [ 8 ] ) )
            return
        self.log.debug ( match )
        msg = match [ 7 ]
        msg_splitted = msg.split ( ":" )

        if len ( msg_splitted ) == 2:
            msg_origin = msg_splitted [ 0 ]
            msg_content = msg_splitted [ 1 ] [ 1 : ]
        else:
            msg_origin = None
            if msg_splitted [ 0 ] == "Server":
                msg_origin = "Server"
                msg_content = msg [ 8 : ]
            for steamid in self.players_info.keys ( ):
                player = self.players_info [ steamid ]
                if player.name == msg [ : len ( player.name ) ]:
                    msg_origin = player.name
                    msg_content = msg [ len ( player.name ) + 2 : ]
                
            if not msg_origin:
                self.log.error ( "Possible injection attempt, ignoring gmsg '{}'.".format ( msg ) )
                return

        if msg_origin != "Server":
            self.log.info ( "CONS %s: %s" % ( msg_origin, msg_content ) )
        else:
            self.log.info ( "CHAT %s: %s" % ( msg_origin, msg_content ) )

        if len ( msg_content ) > 2:
            if msg_content [ 0 : 1 ] == "/":
                # chat message started with "/"
                # so it is possibly a command.
                self.log.debug ( "Possible command: '{}'.".format ( msg_content ) )
                for key in self.commands.keys ( ):
                    if msg_content [ 1 : len ( key ) + 1 ] == key:
                        self.log.debug ( "server command" )
                        self.commands [ key ] [ 0 ] ( msg_origin, msg_content )
                        return
                for mod_key in self.framework.mods:
                    mod = self.framework.mods [ mod_key ] [ 'reference' ]
                    if not mod.enabled:
                        continue
                    for key in mod.commands.keys ( ):
                        if msg_content [ 1 : len ( key ) + 1 ] == key:
                            self.log.info ( "mod {} command".format ( key ) )
                            try:
                                mod.commands [ key ] [ 0 ] ( msg_origin, msg_content )
                                return
                            except Exception as e:
                                self.log.error ( "During mod.commands {}: {}".format ( 
                                        key, framework.output_exception ( e ) ) )
                for external_command in self.external_commands:
                    if msg_content [ 1 : ] == external_command:
                        return
                self.framework.console.pm ( player, "Syntax error: %s." % msg_content [ 1 : ] )
            else:
                self.log.debug ( "Going for a translation." )
                if 'translator'  in self.framework.mods.keys ( ):
                    translator = self.framework.mods [ 'translator' ] [ 'reference' ]
                    if translator.enabled:
                        translator.translate ( msg_origin, msg_content )
                else:
                    self.log.info ( "translate not working" )

    def player_info_update ( self,
                             level,
                             online,
                             playerid,
                             name,
                             pos_x,
                             pos_y,
                             pos_z,
                             health,
                             ip,
                             deaths,
                             zombies,
                             players,
                             score,
                             steamid ):

        events = [ ]
        
        self.framework.get_db_lock ( )
        if steamid in self.players_info.keys ( ):
            now = time.time ( )
            player = self.players_info [ steamid ]

            # old
            # fixing some Nones
            if player.cash == None:
                player.cash = 0
            if player.karma == None:
                player.karma = 0    
            old_level = player.level
            old_online = player.online
            old_playerid = player.playerid
            old_name = player.name
            old_pos_x = player.pos_x
            old_pos_y = player.pos_y
            old_pos_z = player.pos_z
            old_health = player.health
            old_ip = player.ip
            old_deaths = player.deaths
            old_zombies = player.zombies
            old_players = player.players
            old_score = player.score
            old_steamid = player.steamid
            old_timestamp = player.timestamp_latest_update
            old_online_time = player.online_time
            old_zombies = player.zombies

            if isinstance ( old_timestamp, float ):
                added_time = 0
                time_difference = now - old_timestamp
                if time_difference < self.framework.preferences.loop_wait * 10:
                    added_time = time_difference
                total_time = player.online_time
                if isinstance ( total_time, float ):
                    new_total_time = total_time + added_time
                else:
                    new_total_time = added_time
                player.online_time = new_total_time

                # event
                old_minutes = math.floor ( total_time / 3600 )
                new_minutes = math.floor ( new_total_time / 3600 )
                if ( new_minutes > old_minutes ):
                    self.log.info ( "%s played for %d hours." %
                                    ( player.name_sane,
                                      new_minutes ) )
                    events.append ( self.framework.game_events.player_played_one_hour )
                if old_minutes == 4 and new_minutes == 5:
                    events.append ( self.framework.game_events.player_can_vote )
                if old_minutes == 9 and new_minutes == 10:
                    events.append ( self.framework.game_events.player_can_propose )
                    
            else:
                player.online_time = 0

            player.deaths = deaths
            player.health = health
            player.ip = ip
            player.level = level
            player.name = name
            if player.name != old_name:
                events.append ( self.framework.game_events.player_changed_name )
                if not player.attributes:
                    player.attributes = { }
                    if 'old names' not in player.attributes.keys ( ):
                        player.attributes [ 'old names' ] = [ ]
                    player.attributes [ 'old names' ].append ( old_name )
                
            player.name_sane = self.sanitize ( name )
            player.online = online
            player.playerid = playerid
            player.pos_x = pos_x
            player.pos_y = pos_y
            player.pos_z = pos_z
            player_positions = player.positions
            if not isinstance ( player_positions, list ):
                player_positions = [ ]
            player_positions.append ( ( int ( round ( pos_x ) ),
                                        int ( round ( pos_y ) ),
                                        int ( round ( pos_z ) ) ) )
            if len ( player_positions ) > 24 * 60 * 60 / self.framework.preferences.loop_wait:
                del ( player_positions [ 0 ] )
            player.positions = player_positions
            #player.rot = rot
            #player.remote = remote
            player.timestamp_latest_update = now
            player.score = int ( score )

            try:
                unaccounted_zombies = zombies - player.accounted_zombies
                if unaccounted_zombies > 100:
                    events.append ( self.framework.game_events.player_killed_100_zombies )
                    player.accounted_zombies += 100
            except Exception as e:
                self.log.error ( "While parsing player {:s}: {:s}.".format (
                    player.name_sane, str ( e ) ) )
                unaccounted_zombies = 0
                player.accounted_zombies = zombies
                
            player.zombies = zombies
                
            if ( old_pos_x != pos_x or
                 old_pos_y != pos_y or
                 old_pos_z != pos_z ):
                events.append ( self.framework.game_events.player_position_changed )

            if ( not old_online ) and online:
                events.append ( self.framework.game_events.player_detected )
                
            #todo: event
            player.players = players
            if old_players < player.players:
                self.log.info ( "Player %s has killed another player!" %
                                player.name_sane )

        else:
            new_player_info = player_info ( health = health,
                                            ip = ip,
                                            name = name,
                                            playerid = playerid,
                                            pos_x = pos_x,
                                            pos_y = pos_y,
                                            pos_z = pos_z,
                                            deaths = deaths,
                                            zombies = int ( zombies ),
                                            players = players,
                                            score = score,
                                            level = level,
                                            steamid = steamid )
            new_player_info.accounted_zombies = zombies
            new_player_info.cash = 0
            new_player_info.home_invitees = [ ]
            new_player_info.inventory_tracker = [ ]
            new_player_info.karma = 0
            new_player_info.name_sane = self.sanitize ( name )
            new_player_info.online = True
            new_player_info.online_time = 0
            new_player_info.player_kills_explanations = [ ]
            new_player_info.positions = [ ( pos_x, pos_y, pos_z ) ]
            new_player_info.timestamp_latest_update = time.time ( )
            
            player = new_player_info
            self.players_info [ steamid ] = player
            
        self.framework.let_db_lock ( )

        for event_function in events:
            event_function ( player )

    def random_online_player ( self ):
        possibilities = [ ]
        for key in self.players_info.keys ( ):
            if self.players_info [ key ].online == True:
                possibilities.append ( key )
        if possibilities == [ ]:
            return None
        random_index = random.randint ( 0, len ( possibilities ) - 1 )
        return self.get_player ( possibilities [ random_index ] )                
    
    def sanitize ( self, original ):
        result = original.replace ( '"', '_' )
        result = result.replace ( "'", '_' )
        return result
                
    def scout_distance ( self, player, entity_id ):
        """
        Will indicate to player how far he is from entity.
        """
        ent_position = None
        self.wait_entities ( )
        #self.framework.get_ent_lock ( )
        if entity_id in self.entities.keys ( ):
            ent_position = ( self.entities [ entity_id ].pos_x,
                             self.entities [ entity_id ].pos_y,
                             self.entities [ entity_id ].pos_z )
        #self.framework.let_ent_lock ( )
        if not ent_position:
            self.log.info ( "{} not in self.entities".format ( entity_id ) )
            return -1
        distance = self.framework.utils.calculate_distance ( self.framework.utils.get_coordinates ( player ),
                                                             ent_position )
        #if distance > 500:
        #    return -1
        bearing = self.framework.utils.calculate_bearings ( ( player.pos_x, player.pos_y ),
                                                            ( ent_position [ 0 ], ent_position [ 1 ] ) )
        self.framework.console.pm ( player, "{:.1f}m {} (height: {:.1f}m)".format ( distance,
                                                                                    bearing,
                                                                                    player.pos_z - ent_position [ 2 ] ) )
        return distance
            
    def show_inventory ( self, player ):
        msg = "showinventory " + str ( player )
        self.framework.console.send ( msg )

    def set_steamid_online ( self, matches ):
        self.log.warning ( " deprecated call to server.set_steamid_online {}".format ( matches [ 7 ] ) )
        if int ( matches [ 7 ] ) in self.players_info.keys ( ):
            player = self.players_info [ int ( matches [ 7 ] ) ]
            player.online = True
            self.log.info ( "Player {} set as online.".format ( player.name ) )
            self.framework.console.pm ( player, "Welcome back {}!".format ( player.name ), can_fail = True )
        
    def sos ( self, msg_origin, msg_contents ):
        origin = self.get_player ( msg_origin )
        for key in self.players_info.keys ( ):
            if ( self.players_info [ key ].online == True and
                 key != origin.steamid ):
                helper = self.get_player ( key )
                bearings = self.calculate_bearings ( origin, helper )
                msg = 'pm %s "Go %.1fm in direction %d degrees (N is zero ) to help %s if you can!"'
                self.framework.console.send ( msg % ( helper.name_sane,
                                                      bearings [ 0 ],
                                                      bearings [ 1 ],
                                                      origin.name_sane ) )

    def spawn_player_stuff ( self,
                             steamid,
                             stuff ):
        msg = 'se ' + steamid + ' ' + str ( stuff )
        self.log.debug ( msg )
        self.framework.console.send ( msg )

    def stop ( self ):
        self.shutdown = True
        
    def teleport ( self, player_info, where_to ):
        """
        The where_to argument expects a tuple with coordinates ( +E/-W, +N/-S, height ).
        """
        player = self.get_player ( player_info )
        if player == None:
            self.log.error ( "teleport received None from get_player." )
            return
        
        if player != None:
            msg = 'teleportplayer ' + str ( player.steamid ) + ' '
        else:
            msg = 'teleportplayer ' + str ( player_info ) + ' '
        if isinstance ( where_to, str ):
            msg += where_to
        elif isinstance ( where_to, tuple ):
            msg += str ( int ( where_to [ 0 ] ) ) + " " + \
                   str ( int ( where_to [ 2 ] ) ) + " " + \
                   str ( int ( where_to [ 1 ] ) )
        self.framework.console.send ( msg )

    def preteleport ( self, player, where_to ):
        """
        Adds teleportation event to teleport queue.
        """
        self.lock_preteleport_queue ( )
        self.preteleport_queue.append ( ( player, where_to ) )
        self.unlock_preteleport_queue ( )

    def process_preteleport ( self, player, where_to ):
        """
        The where_to argument expects a tuple with coordinates ( +E/-W, +N/-S, height ).
        """
        if not isinstance ( player, player_info ):
            self.log.warning ( "pretele called with playerid" )
            player = self.get_player ( player_info )
            if player == None:
                self.log.error ( "teleport received None from get_player." )
                return

        # If the player has been recently teled to the same position, this is a fluke.
        if player.latest_teleport:
            if 'timestamp' in player.latest_teleport.keys ( ):
                if ( player.latest_teleport [ 'position' ] == where_to and
                     time.time ( ) - player.latest_teleport [ 'timestamp' ] < 2 * self.framework.preferences.loop_wait ):
                    self.log.info ( "Teleport cooldown for {}.".format ( player.name_sane ) )
            
        msg = 'teleportplayer ' + str ( player.steamid ) + ' '
        premsg = msg
        if isinstance ( where_to, tuple ):
            msg += str ( int ( where_to [ 0 ] ) ) + " " + \
                   str ( int ( where_to [ 2 ] ) + 1 ) + " " + \
                   str ( int ( where_to [ 1 ] ) )
            logmsg = str ( int ( where_to [ 0 ] ) ) + " " + \
                     str ( int ( where_to [ 2 ] ) + 1 ) + " " + \
                     str ( int ( where_to [ 1 ] ) )
            premsg += str ( int ( where_to [ 0 ] ) ) + " " + \
                      str ( int ( where_to [ 2 ] ) - 500 ) + " " + \
                      str ( int ( where_to [ 1 ] ) )
            prelogmsg = str ( int ( where_to [ 0 ] ) ) + " " + \
                str ( int ( where_to [ 2 ] ) - 500 ) + " " + \
                str ( int ( where_to [ 1 ] ) )
        self.log.info ( "Preteleport {} ({}) from ({} {} {}).".format ( 
                player.name_sane, prelogmsg, player.pos_x, player.pos_y, player.pos_z ) )
        try:
            self.framework.console.send ( premsg )
        except Exception as e:
            self.log.error ( "Exception during console.send: {}".format ( premsg ) )
            return

        counter = 0
        distance_threshold = 20
        distance = distance_threshold + 1
        try:
            while ( distance > distance_threshold ):
                self.log.debug ( "b4 distance calc: player = {}".format ( player ) )
                distance = self.framework.utils.calculate_distance ( 
                    ( player.pos_x, player.pos_y ), ( where_to [ 0 ], where_to [ 1 ] ) )
                self.log.debug ( "Preteleport sleeping due distance {:.1f} from {} to {}.".format ( 
                        distance, self.framework.utils.get_coordinates ( player ), where_to ) )
                time.sleep ( 1 )
                counter += 1
                if counter > 60:
                    self.log.warning ( "Preteleport broke after timeout." )
                    break
                if not player.online:
                    self.log.warning ( "Preteleport broke because of player going offline." )
                    break
        except Exception as e:
            self.log.error ( "Error during preteleport: {}".format ( e ) )

        self.log.info ( "   teleport {} ({})".format ( player.name_sane, logmsg ) )
        self.framework.console.send ( msg )
        player.latest_teleport = { }
        player.latest_teleport [ 'timestamp' ] = time.time ( )
        player.latest_teleport [ 'position' ] = where_to

    def lock_preteleport_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.preteleport_queue_lock
        now = time.time ( )
        
        while ( lock [ 'callee' ] ):
            if ( now - lock [ 'timestamp' ] > lock [ 'timeout' ] ):
                self.log.error ( "Breaking lock due to timeout!" )
                break
            time.sleep ( 0.1 )
              
        lock [ 'callee'    ] = callee_function
        lock [ 'timestamp' ] = now

    def unlock_preteleport_queue ( self ):
        callee_function = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
        lock = self.preteleport_queue_lock
        
        if lock [ 'callee' ] != callee_function:
            self.log.error ( "Lock being freed by another function than callee!" )
        lock [ 'callee'    ] = None
        lock [ 'timestamp' ] = None

    def enqueue_preteleport ( self, preteleport_data ):
        self.log.debug ( "enqueue_preteleport: {}.".format ( preteleport_data.name ) )
        self.lock_preteleport_queue ( )
        self.preteleport_queue.append ( preteleport_data )
        self.unlock_preteleport_queue ( )

    def dequeue_preteleport ( self ):
        self.lock_preteleport_queue ( )
        preteleport_data = None
        if len ( self.preteleport_queue ) > 0:
            preteleport_data = self.preteleport_queue.pop ( )
        self.unlock_preteleport_queue ( )
        if preteleport_data:
            self.log.debug ( "Dequeue preteleport for {}.".format ( preteleport_data [ 0 ].name_sane ) )
            self.process_preteleport ( preteleport_data [ 0 ], preteleport_data [ 1 ] )

    def update_id ( self, id_fields ):
        #self.latest_id_parse_call = time.time ( )

        playerid = int ( id_fields [ 0 ] )
        playername =     id_fields [ 1 ]
        pos_x  = float ( id_fields [ 2 ] )
        pos_y  = float ( id_fields [ 4 ] )
        pos_z  = float ( id_fields [ 3 ] )
        rot_x  = float ( id_fields [ 5 ] )
        rot_y  = float ( id_fields [ 7 ] )
        rot_z  = float ( id_fields [ 6 ] )
        remote   =       id_fields [ 8 ]
        health   = int ( id_fields [ 9 ] )
        deaths   = int ( id_fields [ 10 ] )
        zombies  = int ( id_fields [ 11 ] )
        players  = int ( id_fields [ 12 ] )
        score    = int ( id_fields [ 13 ] )
        level    = int ( id_fields [ 14 ] )
        steamid  = int ( id_fields [ 15 ] )
        ip       =       id_fields [ 16 ]
        ping     = int ( id_fields [ 17 ] )
        
        country = self.geoip.country_code_by_addr ( ip ) #todo: move this to a conn event

        self.player_info_update ( level = level,
                                  name = playername,
                                  online = True,
                                  playerid = playerid,
                                  pos_x = pos_x,
                                  pos_y = pos_y,
                                  pos_z = pos_z,
                                  health = health,
                                  ip = ip,
                                  deaths = deaths,
                                  zombies = zombies,
                                  players = players,
                                  score = score,
                                  steamid = steamid )

        last_save_timestamp = self.player_db_save_timestamp
        
        now = time.time ( )
        if now - last_save_timestamp > 60:
            self.player_db_save_timestamp = now
            pickle_file = open ( self.player_info_file, 'wb' )
            self.log.info ( "Saving player db." )
            pickle.dump ( self.players_info, pickle_file, pickle.HIGHEST_PROTOCOL )

        if ( now - self.latest_player_db_backup > 24 * 3600 ):
            self.latest_player_db_backup = now
            backup_file_name = self.player_info_file + "_" + time.strftime ( "%Y-%m-%d_%Hh%M.pickle" )
            backup_file = open ( backup_file_name, 'wb' )
            self.log.info ( "Saving player db backup." )
            pickle.dump ( self.players_info, backup_file, pickle.HIGHEST_PROTOCOL )
            self.log.info ( "Cleaning up positions." )
            self.remove_old_positions ( )

    def update_le ( self, matches ):
        self.log.debug ( matches )
        le_id = int ( matches [ 0 ] )
        le_type = matches [ 1 ]
        if le_type not in self.entity_db.keys ( ):
            return
        pos_x  = float ( matches [ 2 ] )
        pos_y  = float ( matches [ 4 ] )
        pos_z  = float ( matches [ 3 ] )
        rot_x  = float ( matches [ 5 ] )
        rot_y  = float ( matches [ 7 ] )
        rot_z  = float ( matches [ 6 ] )
        lifetime = matches [ 8 ]
        remote = matches [ 9 ]
        dead = matches [ 10 ]
        health = int ( matches [ 11 ] )

        #self.framework.get_ent_lock ( ) 
        if le_id in self.framework.server.entities.keys ( ):
            entity = self.framework.server.entities [ le_id ]
        else:
            entity = framework.entity_info ( )
        entity.entity_id = le_id
        entity.entity_type = le_type
        entity.pos_x = pos_x
        entity.pos_y = pos_y
        entity.pos_z = pos_z
        entity.rot_x = rot_x
        entity.rot_z = rot_z
        entity.lifetime = lifetime
        entity.remote = remote
        entity.dead = dead
        entity.health = health

        entity.timestamp = time.time ( )
        
        self.framework.server.entities [ le_id ] = entity
        #self.framework.let_ent_lock ( ) 

    def update_players_pickle ( self ):
        import framework
        new_players_info = { }
        for key in self.players_info.keys ( ):
            player = self.get_player ( key )
            if player != None:
                new_player = None
                a_key = list ( self.players_info.keys ( ) ) [ 0 ]
                
                if self.players_info [ a_key ].__class__.__name__ == 'player_info_v1':
                    new_player = framework.player_info.player_info_v2 ( deaths = player.deaths,
                                                                        health = player.health,
                                                                        home = player.home,
                                                                        ip = player.ip,
                                                                        level = player.level,
                                                                        name = player.name,
                                                                        online = player.online,
                                                                        playerid = player.playerid,
                                                                        players = player.players,
                                                                        pos_x = player.pos_x,
                                                                        pos_y = player.pos_y,
                                                                        pos_z = player.pos_z,
                                                                        score = player.score,
                                                                        steamid = player.steamid,
                                                                        zombies = player.zombies )
                    new_player.home_invasion_beacon = player.home_invasion_beacon
                    new_player.home_invitees = player.home_invitees
                    new_player.language_preferred = player.language_preferred
                    new_player.languages_spoken = player.languages_spoken
                    new_player.map_limit_beacon = player.map_limit_beacon
                    new_player.name_sane = self.sanitize ( player.name )
                    new_player.attributes = player.attributes
                    # New attribute:
                    new_player.camp = None
                    
                if self.players_info [ a_key ].__class__.__name__ == 'player_info_v2':
                    new_player = framework.player_info.player_info_v3 ( deaths = player.deaths,
                                                                        health = player.health,
                                                                        home = player.home,
                                                                        ip = player.ip,
                                                                        level = player.level,
                                                                        name = player.name,
                                                                        online = player.online,
                                                                        playerid = player.playerid,
                                                                        players = player.players,
                                                                        pos_x = player.pos_x,
                                                                        pos_y = player.pos_y,
                                                                        pos_z = player.pos_z,
                                                                        score = player.score,
                                                                        steamid = player.steamid,
                                                                        zombies = player.zombies )
                    new_player.home_invasion_beacon = player.home_invasion_beacon
                    new_player.home_invitees = player.home_invitees
                    new_player.language_preferred = player.language_preferred
                    new_player.languages_spoken = player.languages_spoken
                    new_player.map_limit_beacon = player.map_limit_beacon
                    new_player.name_sane = self.sanitize ( player.name )
                    new_player.attributes = player.attributes
                    new_player.camp = player.camp
                    # new
                    new_player.online_time = 0
                    new_player.player_kills_explanations = [ ]

                if self.players_info [ a_key ].__class__.__name__ == 'player_info_v3':
                    new_player = framework.player_info.player_info_v4 ( deaths = player.deaths,
                                                                        health = player.health,
                                                                        home = player.home,
                                                                        ip = player.ip,
                                                                        level = player.level,
                                                                        name = player.name,
                                                                        online = player.online,
                                                                        playerid = player.playerid,
                                                                        players = player.players,
                                                                        pos_x = player.pos_x,
                                                                        pos_y = player.pos_y,
                                                                        pos_z = player.pos_z,
                                                                        score = player.score,
                                                                        steamid = player.steamid,
                                                                        zombies = player.zombies )
                    new_player.attributes = player.attributes
                    new_player.camp = player.camp
                    new_player.cash = player.cash
                    new_player.home_invasion_beacon = player.home_invasion_beacon
                    new_player.home_invitees = player.home_invitees
                    new_player.karma = player.karma
                    new_player.language_preferred = player.language_preferred
                    new_player.languages_spoken = player.languages_spoken
                    new_player.map_limit_beacon = player.map_limit_beacon
                    new_player.name_sane = self.sanitize ( player.name )
                    new_player.online_time = player.online_time
                    new_player.player_kills_explanations = player.player_kills_exaplanations
                    new_player.timestamp_latest_update = player.timestamp_latest_update

                    #new
                    new_player.accounted_zombies = player.zombies

                if self.players_info [ a_key ].__class__.__name__ == 'player_info_v4':
                    new_player = framework.player_info.player_info_v5 ( deaths = player.deaths,
                                                                        health = player.health,
                                                                        home = player.home,
                                                                        ip = player.ip,
                                                                        level = player.level,
                                                                        name = player.name,
                                                                        online = player.online,
                                                                        playerid = player.playerid,
                                                                        players = player.players,
                                                                        pos_x = player.pos_x,
                                                                        pos_y = player.pos_y,
                                                                        pos_z = player.pos_z,
                                                                        score = player.score,
                                                                        steamid = player.steamid,
                                                                        zombies = player.zombies )
                    new_player.accounted_zombies = player.zombies
                    new_player.attributes = player.attributes
                    new_player.camp = player.camp
                    new_player.cash = player.cash
                    new_player.home_invasion_beacon = player.home_invasion_beacon
                    new_player.home_invitees = player.home_invitees
                    new_player.inventory_tracker = copy.copy ( player.inventory_tracker )
                    new_player.karma = player.karma
                    new_player.language_preferred = player.language_preferred
                    new_player.languages_spoken = player.languages_spoken
                    new_player.map_limit_beacon = player.map_limit_beacon
                    new_player.name_sane = self.sanitize ( player.name )
                    new_player.online_time = player.online_time
                    new_player.permissions = player.permissions
                    new_player.player_kills_explanations = copy.copy ( player.player_kills_explanations )
                    new_player.positions = copy.copy ( player.positions )
                    new_player.timestamp_latest_update = player.timestamp_latest_update

                    # new
                    new_player.home_invasions = { }
                    new_player.latest_teleport = { }
                    new_player.new_since_last_update = { }

                if self.players_info [ a_key ].__class__.__name__ == 'player_info_v5':
                    new_player = framework.player_info.player_info_v6 ( deaths = player.deaths,
                                                                        health = player.health,
                                                                        home = player.home,
                                                                        ip = player.ip,
                                                                        level = player.level,
                                                                        name = player.name,
                                                                        online = player.online,
                                                                        ping = player.ping, #new in v6
                                                                        playerid = player.playerid,
                                                                        players = player.players,
                                                                        pos_x = player.pos_x,
                                                                        pos_y = player.pos_y,
                                                                        pos_z = player.pos_z,
                                                                        score = player.score,
                                                                        steamid = player.steamid,
                                                                        zombies = player.zombies )
                    new_player.accounted_zombies = player.zombies
                    new_player.attributes = player.attributes
                    new_player.camp = player.camp
                    new_player.cash = player.cash
                    new_player.home_invasion_beacon = player.home_invasion_beacon
                    new_player.home_invasions = { }
                    new_player.home_invitees = player.home_invitees
                    new_player.inventory_tracker = copy.copy ( player.inventory_tracker )
                    new_player.karma = player.karma
                    new_player.language_preferred = player.language_preferred
                    new_player.languages_spoken = player.languages_spoken
                    new_player.latest_teleport = { }
                    new_player.map_limit_beacon = player.map_limit_beacon
                    new_player.name_sane = self.sanitize ( player.name )
                    new_player.new_since_last_update = { }
                    new_player.online_time = player.online_time
                    new_player.permissions = player.permissions
                    new_player.player_kills_explanations = copy.copy ( player.player_kills_explanations )
                    new_player.positions = copy.copy ( player.positions )
                    new_player.timestamp_latest_update = player.timestamp_latest_update

                    # new
                    new_player.countries = [ ]
                    new_player.old_names = [ ]
                    new_player.ping = ping

                if new_player == None:
                    self.log.error ( "new_player == None!" )
                    self.log.info ( "self.players_info [ a_key ].__class__.__name__ = %s." %
                                    self.players_info.__class__.__name__ )
                    return
                new_players_info [ new_player.steamid ] = new_player

        self.log.info ( "Creating new player info file." )
        pickle_file = open ( self.player_info_file, 'wb' )
        self.log.info ( "Saving player db." )
        pickle.dump ( new_players_info, pickle_file, pickle.HIGHEST_PROTOCOL )
        self.log.info ( "Resetting pointer." )
        self.players_info = new_players_info

    def update_server_time ( self, matches ):
        self.log.debug ( "update_server_time ( {} )".format ( matches ) )
        old_uptime = self.server_uptime
        old_hours = math.floor ( old_uptime / 3600 )
        self.server_uptime = float ( matches [ 6 ] )
        new_hours = math.floor ( self.server_uptime / 3600 )
        self.log.debug ( "self.server_uptime = {}".format ( self.server_uptime ) )

        if old_hours != new_hours:
            self.log.info ( "Server has been online for {} hours.".format ( new_hours ) )
        if old_hours == 22 and new_hours == 23:
            self.log.info ( "Server will be restarted in about 1 hour." )
        if new_hours >= 24:
            if not self.shutdown_warning:
                self.shutdown_warning = time.time ( )
                self.framework.console.say ( "Server is online for more than 24h: triggering restart sequence." )
                return
            warning_interval = time.time ( ) - self.shutdown_warning
            countdown = 601 - warning_interval
            if countdown > 60:
                if math.ceil ( countdown / 60 ) != self.shutdown_warning_minute:
                    self.shutdown_warning_minute = math.ceil ( countdown / 60 )
                    self.framework.console.say ( "{} minutes until restart.".format ( 
                            self.shutdown_warning_minute ) )
                return
            if countdown > 0:
                self.framework.console.say ( "{} seconds until restart.".format ( round ( countdown ) ) )
                return
            if not self.shutdown_triggered:
                self.shutdown_triggered = True
                self.framework.console.send ( "kickall restart" )
                self.framework.console.send ( "sa" )
                time.sleep ( 5 )
                #self.framework.console.send ( "shutdown" )

    def wait_entities ( self ):
        for counter in range ( 100 ):
            if self.entities == { }:
                time.sleep ( self.framework.preferences.loop_wait / 10 )
                continue
            break

    def cleanup_db ( self ):
        """
        Remove entries that have non-steamid indexes.
        Reindex entries to have them right.
        Remove "positions" that are older than 24h.
        """
        now = time.time ( )
        self.framework.get_db_lock()
        pinfo = {}
        keys_list = list ( self.players_info.keys ( ) )
        for key in keys_list:
            player = self.players_info [ key ]

            a = len ( player.player_kills_explanations )
            #self.log.info ( "From key={}, steamid={}, len={}". format (
            #    key, player.steamid, a ) )
            new_player = framework.player_info.player_info_v5 ( deaths = player.deaths,
                                                                health = player.health,
                                                                home = player.home,
                                                                ip = player.ip,
                                                                level = player.level,
                                                                name = player.name,
                                                                online = player.online,
                                                                playerid = player.playerid,
                                                                players = player.players,
                                                                pos_x = player.pos_x,
                                                                pos_y = player.pos_y,
                                                                pos_z = player.pos_z,
                                                                score = player.score,
                                                                steamid = player.steamid,
                                                                zombies = player.zombies )
            new_player.accounted_zombies = player.zombies
            new_player.attributes = player.attributes
            new_player.camp = player.camp
            new_player.cash = player.cash
            new_player.home_invasion_beacon = player.home_invasion_beacon
            new_player.home_invasions = player.home_invasions
            new_player.home_invitees = player.home_invitees
            new_player.inventory_tracker = player.inventory_tracker
            new_player.karma = player.karma
            new_player.language_preferred = player.language_preferred
            new_player.languages_spoken = player.languages_spoken
            new_player.latest_teleport = player.latest_teleport
            new_player.map_limit_beacon = player.map_limit_beacon
            new_player.name_sane = self.sanitize ( player.name )
            new_player.new_since_last_update = { }
            new_player.online_time = player.online_time
            new_player.permissions = player.permissions
            new_player.player_kills_explanations = copy.copy ( player.player_kills_explanations )
            new_player.timestamp_latest_update = player.timestamp_latest_update
            
            if new_player.timestamp_latest_update:
                if now - new_player.timestamp_latest_update > 24 * 3600:
                    new_player.positions = [ ]
                else:
                    new_player.positions = player.positions

            b = len ( new_player.player_kills_explanations )
            #self.log.info ( "To   key={}, steamid={}, len={}". format (
            #    new_player.steamid, new_player.steamid, b ) )

            if new_player.steamid in pinfo.keys ( ):
                self.log.error (
                    "steamid {} for both {} and {}!".format ( new_player.steamid,
                                                              new_player.name,
                                                              pinfo [ new_player.steamid ].name, ) )
                self.framework.let_db_lock()
                return
            pinfo [ new_player.steamid ] = new_player
            #del ( self.players_info [ key ] )

            c = len ( new_player.player_kills_explanations )
            #self.log.info ( "To   key={}, steamid={}, len={}". format (
            #    new_player.steamid, new_player.steamid, c ) )

            if a != b or a != c:
                self.log.error ( "***************just above*" )

        pickle_file = open ( "cleaned_db", 'wb' )
        self.log.info ( "Saving player db." )
        pickle.dump ( pinfo, pickle_file, pickle.HIGHEST_PROTOCOL )
        
        self.framework.let_db_lock()

    def remove_old_positions ( self ):
        now = time.time ( )
        self.framework.get_db_lock()

        for steamid in self.players_info.keys ( ):
            if self.players_info [ steamid ].positions == [ ]:
                continue
            self.log.debug ( "{} has non-empty positions.".format ( self.players_info [ steamid ].name_sane ) )
            if self.players_info [ steamid ].timestamp_latest_update > now - 24 * 3600:
                continue
            self.log.info ( "{} has not logged in in 24h. Cleaning positions.".format (
                self.players_info [ steamid ].name_sane ) )
            self.players_info [ steamid ].positions = [ ]
        
        self.framework.let_db_lock()

    def little_inferno ( self, player, waves ):
        for count in range ( waves ):
            rythm = 2
            self.framework.console.se ( player, 'zombiedog', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'hornet', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'zombiecrawler', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'fatzombiecop', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'zombiedog', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'zombieferal', 1 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'spiderzombie', 3 )

    def little_swarm ( self, player, waves ):
        for count in range ( waves ):
            rythm = 3
            self.framework.console.se ( player, 'hornet', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'hornet', 2 )
            time.sleep ( rythm )
            self.framework.console.se ( player, 'hornet', 2 )
            if count != waves - 1:
                time.sleep ( rythm )

    def whiner ( self, player ):
        player.cash  = round ( player.cash * 0.9 )
        player.karma = round ( player.karma * 0.9 )
        self.framework.console.pm ( player, "You have been fined 10% of you cash and karma for whining." )
