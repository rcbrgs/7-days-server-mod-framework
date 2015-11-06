import framework
import logging
import math
import pickle
import sys
import threading
import time

class shop ( threading.Thread ):
    def __init__ ( self, framework):
        super ( self.__class__, self ).__init__ ( )
        self.log = framework.log
        self.__version__ = "0.8.11"
        self.changelog = {
            '0.8.11' : "Only announce best sell / best buy when shop is enabled.",
            '0.8.10' : "When command_buy has syntax error, abort function.",
            '0.8.9'  : "Added helpful hint when invoking /buy with no arguments.",
            '0.8.8'  : "Removed karma cost for /sell.",
            '0.8.7'  : "Added second order price scaling accfording to stock value.",
            '0.8.6'  : "Made best sell/buy messages direct so players dont have to think so much. The poor things.",
            '0.8.5'  : "Fixed best buy logic.",
            '0.8.4'  : "Fixed best sale logic.",
            '0.8.3'  : "Added best_sell function.",
            '0.8.2'  : "Added best_buy function.",
            '0.8.1'  : "Made prices more inertial during increase_stock, so they do not skyrocket/plummet so much.",
            '0.8.0'  : "Shop can now trade karma. Experimental! Try /sellkarma to sell, /buy karma to buy.",
            }
        
        self.framework = framework
        self.daemon = True
        self.shutdown = False

        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]

        # To have a new command for players to use, it must be placed in the dict below.
        # The commented example adds the command "/suicide" and have the mod run the function "kill_player ( )".
        # All player chat commands receive two strings as arguments. The first contains the player name (unsanitized) and the second contains the string typed by the player (also unsanitized).
        self.commands = {
            # 'suicide' : ( self.kill_player, " /suicide will kill your character." )
            'buy'        : ( self.command_buy,  " /buy <item> <quantity> will purchase the item, if you can afford. NO REFUNDS." ),
            #'firescouts' : ( self.command_firescouts, " /firescouts will fire your scouts." ),
            'list'       : ( self.command_list, " /list will name buyable items, /list <item> will describe it." ),
            'sell'       : ( self.command_sell, " /sell WILL TP YOU TO THE SKY. This put you in 'sell mode' where items you drop are sent to the shop. Then use /sell again to be TPd back to surface and receive cash. Experimental feature - NO REFUNDS. Costs 1 karma." ),
            'sellkarma'  : ( self.command_sellkarma, " /sellkarma <quantity> will sell your unused karma points." )
        }

        self.players_in_sell_mode = { }
        self.scouts_distance = [ ]
        self.sell_mode_cooloff = { }
        self.default_stock = {

#            'airFilter'  : { 'alternate_names' : [ ],
#                             'cash_price'      : 10,
#                             'description'     : "Step on it!",
#                             'in stock'        : 0,
#                             'karma_price'     : 0,
#                             'li_key'          : 'airFilter',
#                             'real_price'      : 10 },
            
            'bookcase'     : { 'description'     : "Don't worry, you don't _have_ to read any book.",
                               'li_key'          : 'bookcase',
                               'cash_price'      : 200,
                               'real_price'      : 200,
                               'karma_price'     : 0,
                               'alternate_names' : [ ],
                               'in stock'        : 1 },
            
            
            'cashRegister' : { 'description'     : "Math is needed even after the apocalypse.",
                               'li_key'          : 'cashRegister',
                               'cash_price'      : 200,
                               'real_price'      : 200,
                               'karma_price'     : 0,
                               'alternate_names' : [ ],
                               'in stock'        : 1 },

            'karma'        : { 'description'     : "Your very essence.",
                               'li_key'          : 'karma',
                               'cash_price'      : 1000,
                               'real_price'      : 1000,
                               'karma_price'     : -1,
                               'alternate_names' : [ ],
                               'in stock'         : 1 },
            
            'keystone'     : { 'description'     : "Claim part of the world as yours. Let 'em grifers come!",
                               'li_key'          : 'keystone',
                               'cash_price'      : 200,
                               'real_price'      : 200,
                               'karma_price'     : 1,
                               'alternate_names' : [ 'claimstone', 'claimblock', 'claim' ],
                               'in stock'        : 0 },
            
            'leatherBootsSchematic' : { 'description'     : "Wrap your feet with skin from the dead.",
                                        'li_key'          : 'leatherBootsSchematic',
                                        'cash_price'      : 50,
                                        'real_price'      : 50,
                                        'karma_price'     : 1,
                                        'alternate_names' : [ ],
                                        'in stock'        : 0 },

            'leatherHatSchematic' : { 'description'     : "Stylish. Smelly, but stylish.",
                                      'li_key'          : 'leatherBootsSchematic',
                                      'cash_price'      : 50,
                                      'real_price'      : 50,
                                      'karma_price'     : 1,
                                      'alternate_names' : [ ],
                                      'in stock'        : 0 },

            'leatherJacketSchematic' : { 'description'     : "Who knew knitting was so fun?",
                                         'li_key'          : 'leatherJacketSchematic',
                                         'cash_price'      : 50,
                                         'real_price'      : 50,
                                         'karma_price'     : 1,
                                         'alternate_names' : [ 'jacketSchematic' ],
                                         'in stock'        : 0 },

            'leatherPantsSchematic' : { 'description'     : "You were born naked but its really gross.",
                                        'li_key'          : 'leatherPantsSchematic',
                                        'cash_price'      : 50,
                                        'real_price'      : 50,
                                        'karma_price'     : 1,
                                        'alternate_names' : [ ],
                                        'in stock'        : 0 },

            'leatherTanning' : { 'description'     : "Yay! Roman skirts for all!",
                                 'li_key'          : 'leatherTanning',
                                 'cash_price'      : 50,
                                 'real_price'      : 50,
                                 'karma_price'     : 1,
                                 'alternate_names' : [ ],
                                 'in stock'        : 0 },
            
            'minibikesForDumbshits'      : { 'description'     : "Hell's Angels' prayer book.",
                                             'li_key'          : 'minibikesForDumbshits',
                                             'cash_price'      : 100,
                                             'real_price'      : 100,
                                             'karma_price'     : 1,
                                             'alternate_names' : [ ],
                                             'in stock'        : 0 },
            
            'pistolBook'   : { 'description'     : "Oooh, you have to point the thing THAT way.",
                               'li_key'          : 'pistolBook',
                               'cash_price'      : 50,
                               'real_price'      : 50,
                               'karma_price'     : 1,
                               'alternate_names' : [ 'pistolSchematic', 'pistolSchematics' ],
                               'in stock'        : 0 },
            
            'pumpShotgunSchematic'   : { 'description'     : "How to make bada-bum?",
                                         'li_key'          : 'pumpShotgunSchematic',
                                         'cash_price'      : 50,
                                         'real_price'      : 50,
                                         'karma_price'     : 1,
                                         'alternate_names' : [ 'shotgunschematic', 'pumpshotgunschematic' ],
                                         'in stock'        : 0 },
            
            'sawedoffPumpShotgunSchematic' : { 'description'     : "Learn to miss shots at close range.",
                                               'li_key'          : 'sawedoffPumpShotgunSchematic',
                                               'cash_price'      : 50,
                                               'real_price'      : 50,
                                               'karma_price'     : 1,
                                               'alternate_names' : [ ],
                                               'in stock'        : 0 },
            
            'scout'        : { 'description'     : "A scout will search the nearest animal.",
                               'li_key'          : 'scout',
                               'cash_price'      : 1,
                               'real_price'      : 1,
                               'karma_price'     : 0,
                               'alternate_names' : [ ],
                               'in stock'        : 2 },

            'steelArrowHead' : { 'description'     : "Made by 'SAKIS Greek Smelters Co'.",
                                 'li_key'          : 'steelArrowHead',
                                 'cash_price'      : 5,
                                 'real_price'      : 5,
                                 'karma_price'     : 0,
                                 'alternate_names' : [ ],
                                 'in stock'        : 5 },
            
            'toilet01'     : { 'description'     : "A toilet with white plastic lid.",
                               'li_key'          : 'toilet01',
                               'cash_price'      : 50,
                               'real_price'      : 50,
                               'karma_price'     : 0,
                               'alternate_names' : [ 'toilet' ],
                               'in stock'        : 2 },
            
            'toilet02'     : { 'description'     : "A toilet with wooden lid.",
                               'li_key'          : 'toilet02',
                               'cash_price'      : 50,
                               'real_price'      : 50,
                               'karma_price'     : 0,
                               'alternate_names' : [ ],
                               'in stock'        : 2 },
            
            'toilet03'     : { 'description'     : "A commercial lidless toilet.",
                               'li_key'          : 'toilet03',
                               'cash_price'      : 50,
                               'real_price'      : 50,
                               'karma_price'     : 0,
                               'alternate_names' : [ ],
                               'in stock'        : 2 },            
        }
        self.stock = None

    def __del__ ( self ):
        if not self.shutdown:
            self.log.error ( "Deleting shop without stopping first!" )
            self.stop ( )

    def greet ( self ):
        self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                    self.__version__ ) )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        try:
            stock_file = open ( self.framework.preferences.mods [ 'shop' ] [ 'stock_file' ], 'rb' )
        except Exception as e:
            self.log.warning ( "Stock file read exception {}, generating from scratch.".format ( e ) )
            stock_file = None
            
        if stock_file:
            try:
                self.stock = pickle.load ( stock_file )
            except Exception as e:
                self.log.error ( "While loading stock prices: {}.".format ( e ) )
                self.stock = self.default_stock
        else:
            self.stock = self.default_stock

        self.update_pickle_from_default ( )
        self.fix_negative_prices ( )
            
        while ( self.shutdown == False ):
            time.sleep ( self.framework.preferences.loop_wait )
            if not self.enabled:
                continue

            # STARTMOD

            deletables = [ ]
            for scout in self.scouts_distance:
                now = time.time ( )
                if 'entity_id' not in scout.keys ( ):
                    scout [ 'entity_id' ], scout [ 'entity_type' ] = self.framework.server.get_nearest_animal ( scout [ 'player' ] )
                    scout [ 'timestamp' ] = now

                interval = now - scout [ 'timestamp' ]
                if interval < 15:
                    continue
                scout [ 'timestamp' ] = now
                
                distance = self.framework.server.scout_distance ( scout [ 'player' ],
                                                                  scout [ 'entity_id' ] )
                if distance == -1:
                    self.framework.console.pm ( scout [ 'player' ],
                                                "Your scout is trying to find an animal track." )

                    scout [ 'entity_id' ], scout [ 'entity_type' ] = self.framework.server.get_nearest_animal ( scout [ 'player' ] )
                elif distance < 11:
                    self.framework.console.pm ( scout [ 'player' ],
                                                "The scout points to {} and leaves.".format (
                        scout [ 'entity_type' ] ) )
                    deletables.append ( scout )
                    
            for deletable in deletables:
                self.scouts_distance.remove ( deletable )

            self.eject_sell_mode_hideout ( )

            if 'shamSandwich' in list ( self.stock.keys ( ) ):
                if self.stock [ 'shamSandwich' ] [ 'in stock' ] >= 1000:
                    self.stock [ 'shamSandwich' ] [ 'in stock' ] -= 1000
                    self.stock [ 'keystone' ] [ 'in stock' ] += 1

            for key in self.stock.keys ( ):
                self.appraise_item ( self.stock [ key ] )
            
            # ENDMOD
        try:
            stock_file = open ( self.framework.preferences.mods [ 'shop' ] [ 'stock_file' ], 'wb' )
            pickle.dump ( self.stock, stock_file, pickle.HIGHEST_PROTOCOL )
        except Exception as e:
            self.log.info ( "while saving stocks: {}".format ( e ) )
            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        players_to_exit = list ( self.players_in_sell_mode.keys ( ) )
        for steamid in players_to_exit:
            self.exit_sell_mode ( self.framework.server.get_player ( steamid ) )
        self.shutdown = True

    def command_buy ( self, origin, msg ):
        player = self.framework.server.get_player ( origin )
        if len ( msg [ len ( "/buy " ) : ] ) == 0:
            self.framework.console.pm ( player, "Please specify an item to buy. (Try the /list command)." )
            return
        mixed = msg [ len ( "/buy " ) : ].strip ( )
        if len ( mixed.split ( " " ) ) == 1:
            name = mixed
            quantity = 1
        elif len ( mixed.split ( " " ) ) == 2:
            name = mixed.split ( " " ) [ 0 ] 
            try:
                quantity = int ( mixed.split ( " " ) [ 1 ] )
            except Exception as e:
                #self.log.error ( "when fidning quantity: {}". format ( e ) )
                self.framework.console.pm ( player, "'{}' is not a valid quantity!".format (
                    mixed.split ( " "  ) [ 1 ] ) )
                return
        else:
            self.framework.console.pm ( player, "Syntax error: '{}'.".format ( msg ) )
            return

        item = self.get_item ( name )
        if not item:
            #if player.cash > 1:
            #    player.cash -= 1
            #    self.framework.console.pm ( player, "You spent 1$ to know the store doesn't have {}.".format (
            #            name ) )
            self.framework.console.pm ( player, "That ain't for sale!" )
            return
            
        if item [ 'in stock' ] < quantity:
            #if player.cash > 1:
            #    player.cash -= 1
            #    self.framework.console.pm ( player, "You spent 1$ to know the store doesn't have that many {}.".format (
            #            item [ 'li_key' ] ) )
            self.framework.console.pm ( player, "I don't have that many {} to sell!".format ( item [ 'li_key' ] ) )
            return

        #price = self.appraise_goods ( item, 1 )
        if player.cash < item [ 'cash_price' ] * quantity:
            self.log.info ( "Warning player {} about cash price.".format ( player.name_sane ) )
            self.warn_price ( player, item )
            #self.inflate_price ( item, 1.01 )
            return
            
        if player.karma < item [ 'karma_price' ] * quantity:
            self.log.info ( "Warning player {} about karma price.".format ( player.name_sane ) )
            self.warn_price ( player, item )
            #self.inflate_price ( item, 1.01 )
            return

        if item == "scout":
            self.log.info ( "Giving player {} a scout.".format ( player.name_sane ) )
            self.scouts_distance.append ( { 'player'    : player,
                                            'timestamp' : time.time ( ) } )
            return

        # Everything should be ok from here to the end.
        
        item [ 'in stock'   ] -= quantity
        self.framework.server.give_player_stuff ( player, item [ 'li_key' ], quantity )
        player.cash -= int ( item [ 'cash_price' ] * quantity )
        player.karma -= item [ 'karma_price' ] * quantity
        self.framework.console.pm ( player, "You spent {}$+{}k to buy {} {}.". format (
            item [ 'cash_price'  ] * quantity,
            item [ 'karma_price' ] * quantity,
            quantity,
            item [ 'li_key' ] ) )
        #old_price = item [ 'real_price' ]
        #self.inflate_price ( item, 1.01 )
        #self.inflate_turnover_time ( item )
        #self.inflate_stock_depletion ( item, quantity )
        #price = self.appraise_goods ( item, 0 )
        #self.log.info ( "{} inflated from {:.1f} to {:.1f} ({:.0f}%).".format (
        #    item [ 'li_key' ],
        #    old_price,
        #    item [ 'real_price' ],
        #    100 * item [ 'real_price' ] / old_price ) )

    def command_list ( self, origin, msg ):
        self.log.debug ( "list ( {}, {} )".format ( origin, msg ) )
        player = self.framework.server.get_player ( origin )
        if not player:
            return

        #if player.cash < 1:
        #    self.framework.console.pm ( player, "You need 1 cash to list items!" )
        #    return

        #player.cash -= 1
        #self.framework.console.pm ( player, "You spent 1$ to list items." )

        argument = msg [ len ( "/list " ) : ]
        if argument == "":
            sellables = [ ]
            for key in self.stock.keys ( ):
                if self.stock [ key ] [ 'in stock' ] > 0:
                    sellables.append ( key )
            list_string = ""
            sorted_sellables = sorted ( sellables )
            for stuff in sorted_sellables:
                if list_string != "":
                    list_string += " "
                list_string += stuff
            self.framework.console.pm ( player, list_string )
            return
            
        self.log.debug ( "argument = {}".format ( argument ) )
        item = self.get_item ( argument )
        if not item:
            self.framework.console.pm ( player, "I don't sell {}!".format ( argument ) )                        
            return
        
        description = item [ 'description' ]
        if description == "Caveat emptor.":
            description = ""

        self.framework.console.pm ( player, "{}: {} {}$+{}k. {} in stock.".format (
            item [ 'li_key' ],
            description,
            item [ 'cash_price' ],
            item [ 'karma_price' ],
            item [ 'in stock' ] ) )
                
    def command_firescouts ( self, origin, msg ):
        player = self.framework.server.get_player ( origin )
        deletables = [ ]
        for scout in self.scouts_distance:
            if scout [ 'player' ] == player:
                deletables.append ( scout )
        for deletable in deletables:
            self.scouts_distance.remove ( deletable )
        self.framework.console.pm ( player, "You fired your scouts." )

    def command_sell ( self, origin, message ):
        player = self.framework.server.get_player ( origin )
        if player.steamid in list ( self.players_in_sell_mode.keys ( ) ):
            self.exit_sell_mode ( player )
        else:
            self.enter_sell_mode ( player )

    def command_sellkarma ( self, origin, message ):
        """
        Player command to sell karma and put it in the shop.
        """
        player = self.framework.server.get_player ( origin )
        if not player:
            self.log.warning ( "command_sellkarma: player '{}' unrecognized.".format ( origin ) )
            return
        try:
            quantity = int ( message [ len ( "/sellkarma " ) : ] )
        except Exception as e:
            self.log.warning ( "command_sellkarma int ( ) exception '{}'.".format ( e ) )
            return
        if player.karma < quantity:
            self.framework.console.pm ( player, "You don't have that many karma to sell!" )
            return

        self.effectuate_sale ( player, "karma", quantity )
                
    def warn_price ( self, player, item ):
        self.framework.console.pm ( player, "A {} costs {}$+{}k!".format (
            item [ 'li_key' ], item [ 'cash_price' ], item [ 'karma_price' ] ) )

    # /commands

    def append_new_item_to_stock ( self, item_kind, amount ):
        self.log.info ( "appending {} to stock.".format ( item_kind ) )
        self.stock [ item_kind ] = { 
            'alternate_names' : [ ],
            'cash_price'      : 2,
            'description'     : "Caveat emptor.",
            'in stock'        : amount,
            'karma_price'     : 0,
            'li_key'          : item_kind,
            'max stock'       : 0,
            'old stock'       : 0,
            'real_price'      : 2,
            'timestamp_sell'  : time.time ( ) }
        
        self.log.info ( self.stock [ item_kind ] )

    def appraise_item ( self, item ):
        target_stock_value = 5000
        if 'max stock' not in list ( item.keys ( ) ):
            item [ 'max stock' ] = 0
        if 'old stock' not in list ( item.keys ( ) ):
            item [ 'old stock' ] = 0

        old_stock = item [ 'old stock' ]
        item [ 'old stock' ] = item [ 'in stock' ]
        old_max_stock = item [ 'max stock' ]
        item [ 'max stock' ] = max ( item [ 'in stock' ], item [ 'max stock' ] ) 
        old_real_price = item [ 'real_price' ]

        if ( old_stock == item [ 'in stock' ] ):
            return

        ratio = item [ 'in stock' ] / max ( old_stock, 1 )
        self.log.info ( "{} stock {} (x{:.2f}) -> {}.".format ( item [ 'li_key' ], 
                                                                old_stock,
                                                                ratio,
                                                                item [ 'in stock' ] ) )
        try:
            adjustment = ratio ** ( -1 )
        except ZeroDivisionError:
            adjustment = 1.1
        self.log.debug ( "raw adjustment = {}".format ( adjustment ) )
        if adjustment < 0.9:
            adjustment = 0.9
        if adjustment > 1.1:
            adjustement = 1.1
        self.log.debug ( "    adjustment = {}".format ( adjustment ) )
        
        # scale the price according to max stock
        current_stock_value = item [ 'real_price' ] * item [ 'in stock' ]
        self.log.info ( "{} current stock value = {}".format ( item [ 'li_key' ], current_stock_value ) )
        target_stock_value = 5000
        if current_stock_value > target_stock_value:
            adjustment -= 0.05
        if current_stock_value < target_stock_value:
            adjustment += 0.05

        item [ 'real_price' ] *= adjustment
        self.log.info ( "{} price {:.2f} (x{:.2f}) -> {:.2f}.".format ( item [ 'li_key' ], 
                                                                        old_real_price,
                                                                        adjustment,
                                                                        item [ 'real_price' ] ) )
        item [ 'cash_price' ] = round ( item [ 'real_price' ] )

    def best_buy ( self ):
        """
        Will chat the best item to buy at the moment.
        """
        best_key = None
        best_value = None
        for key in self.stock.keys ( ):
            if self.stock [ key ] [ 'in stock' ] < 1:
                continue
            if not best_key:
                best_key = key
                best_value = self.stock [ key ] [ 'cash_price' ]
            if self.stock [ key ] [ 'cash_price' ] < best_value:
                best_value = self.stock [ key ] [ 'cash_price' ]
                best_key = key

        if not best_key:
            return
        item = self.stock [ best_key ]
        if self.enabled:
            self.framework.console.say ( "Cheapest item: {} is {}$+{}k and there is {} in stock!".format (
                    best_key, item [ 'cash_price' ], item [ 'karma_price' ], item [ 'in stock' ] ) )

    def best_sell ( self ):
        """
        Will chat the best item to sell at the moment.
        """
        best_key = None
        best_value = None
        for key in self.stock.keys ( ):
            if not best_key:
                best_key = key
                best_value = self.stock [ key ] [ 'cash_price' ]
            if self.stock [ key ] [ 'cash_price' ] > best_value:
                best_value = self.stock [ key ] [ 'cash_price' ]
                best_key = key

        if not best_key:
            return
        item = self.stock [ best_key ]
        if self.enabled:
            self.framework.console.say ( "Most expensive item: {} is {}$+{}k!".format (
                    best_key, item [ 'cash_price' ], item [ 'karma_price' ] ) )

    def diff_inventories ( self, before, after ):
        self.log.info ( "before: {}".format ( before ) )
        self.log.info ( " after: {}".format ( after  ) )

        belt = { }
        backpack = { }

        for count in range ( 8 ):
            belt     [ count ] = ( ( None, None ), ( None, None ) )

        for count in range ( 32 ):
            backpack [ count ] = ( ( None, None ), ( None, None ) )

        self.log.info ( "parsing before" )
        for string_index in before.keys ( ):
            if string_index == 'checking' or string_index == 'storage':
                continue
            slot_before = before [ string_index ]
            self.log.debug ( "slot_before = {} ".format ( slot_before ) )
            if slot_before [ 0 ] == 'Belt':
                belt [ int ( slot_before [ 1 ] ) ] = ( 
                    ( slot_before [ 3 ], int ( slot_before [ 2 ] ) ), ( None, None ) )
            else:
                backpack [ int ( slot_before [ 1 ] ) ] = ( 
                    ( slot_before [ 3 ], int ( slot_before [ 2 ] ) ), ( None, None ) )

        self.log.info ( "parsing after" )
        for string_index in after.keys ( ):
            if string_index == 'checking' or string_index == 'storage':
                continue
            slot_after = after [ string_index ]
            if slot_after [ 0 ] == 'Belt':
                belt [ int ( slot_after [ 1 ] ) ] = ( belt [ int ( slot_after [ 1 ] ) ] [ 0 ],
                                                      ( slot_after [ 3 ], int ( slot_after [ 2 ] ) ) )
            else:
                backpack [ int ( slot_after [ 1 ] ) ] = ( backpack [ int ( slot_after [ 1 ] ) ] [ 0 ],
                                                             ( slot_after [ 3 ], int ( slot_after [ 2 ] ) ) )

        self.log.info ( "Belt diff:" )
        for count in range ( 8 ):
            if belt [ count ] [ 0 ] != belt [ count ] [ 1 ]:
                self.log.info ( belt [ count ] )
            else:
                self.log.debug ( "slot {} equal".format ( count ) )

        self.log.info ( "Bag  diff:" )
        for count in range ( 32 ):
            if backpack [ count ] [ 0 ] != backpack [ count ] [ 1 ]:
                self.log.info ( backpack [ count ] )       
            else:
                self.log.debug ( "slot {} equal".format ( count ) )
       
        self.log.debug ( "about to return" )
        return ( belt, backpack )

    def calculate_pay ( self, player, spawns ):
        account = { }
        before = self.players_in_sell_mode [ player.steamid ] [ 'before' ]
        after = self.players_in_sell_mode [ player.steamid ] [ 'after' ]
        diff_account = [ ]
        try:
            belt_diff, backpack_diff = self.diff_inventories ( before, after )
            for entry in belt_diff.keys ( ):
                if belt_diff [ entry ] [ 0 ] != belt_diff [ entry ] [ 1 ]:
                    self.log.info ( "To account: {}.".format ( belt_diff [ entry ] ) )
                    diff_account.append ( belt_diff [ entry ] )
            for entry in backpack_diff.keys ( ):
                if backpack_diff [ entry ] [ 0 ] != backpack_diff [ entry ] [ 1 ]:
                    self.log.info ( "To account: {}.".format ( backpack_diff [ entry ] ) )
                    diff_account.append ( backpack_diff [ entry ] )
        except Exception as e:
            self.log.error ( "Exception at diff_inventories: {}".format ( e ) )

        item_kinds = [ ]
        spawns_expected = 0
        for entry in diff_account:
            if entry [ 1 ] != ( None, None ):
                self.log.info ( "Inventory differed into non-empty slot: {}.".format ( entry ) )
            else:
                if entry [ 0 ] [ 0 ] not in item_kinds:
                    item_kinds.append ( entry [ 0 ] [ 0 ] )
                spawns_expected += 1
        self.log.info ( "item_kinds ({}) = {}.".format ( len ( item_kinds ), item_kinds ) )
        self.log.info ( "spawns = {}, expected {}".format ( spawns, spawns_expected ) )

        self.log.debug ( "before = {}".format ( before ) )
        for key in before.keys ( ):
            if key == 'checking' or key == 'storage':
                continue

            before_entry = before [ key ]
            self.log.debug ( "before_entry = {}".format ( before_entry ) )

            if before_entry [ 3 ] not in ( account.keys ( ) ):
                account [ before_entry [ 3 ] ] = 0

            account  [ before_entry [ 3 ] ] += before_entry [ 2 ]

        for key in account.keys ( ):
            self.log.debug ( "account {} = {}".format ( key, account [ key ] ) )

        for key in after.keys ( ):
            if key == 'checking' or key == 'storage':
                continue

            after_entry = after [ key ]
            self.log.debug ( "after_entry = {}".format ( after_entry ) )

            if after_entry [ 3 ] not in ( account.keys ( ) ):
                account [ after_entry [ 3 ] ] = 0

            account  [ after_entry [ 3 ] ] -= after_entry [ 2 ]
            
        should_spawn = 0
        for key in account.keys ( ):
            if account [ key ] < 0:
                self.log.info ( "Sale cheating: account {} = {}".format ( key, account [ key ] ) )
                self.framework.console.pm ( player, "You crafted inside the shop, sale is aborted." )
                return
            elif account [ key ] != 0:
                should_spawn += 1
        
        self.log.info ( "should_spawn = {}, len ( item kinds ) = {}".format ( 
                should_spawn, len ( item_kinds ) ) )
        if len ( item_kinds ) != should_spawn:
            self.framework.console.pm ( player, "You moved items without dropping them. Sale aborted." )
            return
    
        for key in account.keys ( ):            
            if account [ key ] != 0:
                self.log.info ( "{} sold {} {}.".format ( player.name_sane,
                                                          account [ key ],
                                                          key ) )
                if account [ key ] > 0:
                    self.effectuate_sale ( player, key, account [ key ] )
                

    def effectuate_sale ( self, player, item_kind, amount ):
        if item_kind in list ( self.stock.keys ( ) ):
            value = self.stock [ item_kind ] [ 'cash_price' ] / 2
            amount_to_pay = value * amount
            player.cash += max ( 0, round ( amount_to_pay ) )
        
            self.framework.console.pm ( player, "You sold {} {} for {:.0f}!".format (
                amount, item_kind, amount_to_pay ) )
            old_stock = self.stock [ item_kind ] [ 'in stock' ]
            self.stock [ item_kind ] [ 'in stock'   ] += amount
            if old_stock < 1:
                self.framework.console.say ( "Shop now has {} {} in stock!".format ( 
                        self.stock [ item_kind ] [ 'in stock' ], 
                        self.stock [ item_kind ] [ 'li_key' ], ) )
            self.stock [ item_kind ] [ 'timestamp_sell' ] = time.time ( )
        else:
            self.framework.console.pm ( player, "The shop doesn't trade {}. Buying for 1 cash a piece.".format ( item_kind ) )
            self.append_new_item_to_stock ( item_kind, amount )
            self.framework.console.say ( "Shop now has {} {} in stock!".format ( 
                    self.stock [ item_kind ] [ 'in stock' ], 
                    self.stock [ item_kind ] [ 'li_key' ], ) )

    def eject_sell_mode_hideout ( self ):
        now = time.time ( )
        ejectees = [ ]
        for steamid in self.players_in_sell_mode.keys ( ):
            if 'timestamp'  in list ( self.players_in_sell_mode [ steamid ].keys ( ) ):
                if now - self.players_in_sell_mode [ steamid ] [ 'timestamp' ] > 30:
                    ejectees.append ( steamid )
        for steamid in ejectees:
            self.framework.console.pm ( self.framework.server.get_player ( steamid ),
                                        "Ejecting you from sell mode after 30 seconds." )
            self.exit_sell_mode ( self.framework.server.get_player ( self.framework.server.get_player ( 
                        steamid ) ) )
            
    def enter_sell_mode ( self, player ):
        now = time.time ( )
        if player.steamid in list ( self.sell_mode_cooloff.keys ( ) ):
            if now - self.sell_mode_cooloff [ player.steamid ] < 300:
                remaining = now - self.sell_mode_cooloff [ player.steamid ]
                self.framework.console.pm ( player, "Sell mode cooloff still in effect ({:d}s).".format ( round ( remaining ) ) )
                return
        #if player.karma < 1:
        #    self.framework.console.pm ( player, "You need 1 karma to enter sell mode!" )
        #    return
        #player.karma -= 1
        #self.framework.console.pm ( player, "You spent 1 karma to enter sell mode." )

        self.players_in_sell_mode [ player.steamid ] = { }
        self.players_in_sell_mode [ player.steamid ] [ 'before'   ] = self.framework.world_state.blocking_get_inventory ( player )
        self.players_in_sell_mode [ player.steamid ] [ 'position' ] = ( player.pos_x, player.pos_y, player.pos_z )
        self.players_in_sell_mode [ player.steamid ] [ 'timestamp' ] = time.time ( )
        self.players_in_sell_mode [ player.steamid ] [ 'exiting' ] = False
        self.framework.server.teleport ( player.name, ( player.pos_x, player.pos_y, player.pos_z - 5000 ) )

    def exit_sell_mode ( self,  player ):
        if player.steamid not in list ( self.players_in_sell_mode.keys ( ) ):
            self.log.info ( "steamid not in keys." )
            return
        if self.players_in_sell_mode [ player.steamid ] [ 'exiting' ]:
            self.log.warning ( "Player {} already exiting sell mode.".format ( player.name_sane ) )
            return
        self.players_in_sell_mode [ player.steamid ] [ 'exiting' ] = True
        self.sell_mode_cooloff [ player.steamid ] = time.time ( )
        try:
            self.framework.server.teleport ( player.name, self.players_in_sell_mode [ player.steamid ] [ 'position' ] )
            self.players_in_sell_mode [ player.steamid ] [ 'after' ] = self.framework.world_state.blocking_get_inventory ( player )
            wrong_spawns = [ ]
            for position in self.framework.world_state.inventory_wrong_spawns:
                if self.framework.utils.calculate_distance ( ( position [ 0 ], position [ 1 ] ),
                                                             ( player.pos_x, player.pos_y ) ) < 10:
                    wrong_spawns.append ( position )
            spawns = len ( wrong_spawns )
            for wrong in wrong_spawns:
                self.framework.world_state.inventory_wrong_spawns.remove ( wrong )

        except Exception as e:
            self.log.error ( "exit sell mode: {} ".format ( e ) )
            return
        self.calculate_pay ( player, spawns )
        try:
            del ( self.players_in_sell_mode [ player.steamid ] )
        except KeyError:
            self.log.warning ( "Tried to delete steamid from {} already not in players_in_sell_mode.".format ( 
                    player.name_sane ) )

    def get_item ( self, item_string ):
        self.log.debug ( "get_item ( {} )".format ( item_string ) )

        if item_string in list ( self.stock.keys ( ) ):
            self.log.debug ( "item_string is a key for {}".format ( self.stock [ item_string ] ) )
            return self.stock [ item_string ]
        self.log.debug ( "not a key" )
            
        for stock_key in self.stock.keys ( ):
            if item_string in list ( self.stock [ stock_key ] [ 'alternate_names' ] ):
                self.log.info ( "an alternate" )
                return self.stock [ stock_key ]
        self.log.debug ( "not an alternate" )

        for stock_key in list ( self.stock.keys ( ) ):
            if item_string.lower ( ) == stock_key.lower ( ):
                self.log.info ( "a case mismatched key" )
                return self.stock [ stock_key ]
        self.log.debug ( "not a case mismatched key" ) 
 
        for stock_key in self.stock.keys ( ):
            alternates = list ( self.stock [ stock_key ] [ 'alternate_names' ] )
            for alternate in alternates:
                if item_string.lower ( ) == alternate.lower ( ): 
                    self.log.info ( "a case mismatched alternate" )
                    return self.stock [ stock_key ]
        self.log.debug ( "not a case mismatched alternate" ) 

        for stock_key in self.stock.keys ( ):
            if item_string.lower ( ) in stock_key.lower ( ):
                self.log.info ( "partial key" )
                return self.stock [ stock_key ]
        self.log.debug ( "not a partial key" )

        for stock_key in self.stock.keys ( ):
            alternates = list ( self.stock [ stock_key ] [ 'alternate_names' ] )
            for alternate in alternates:
                if item_string.lower ( ) == alternate.lower ( ): 
                    self.log.info ( "partial alternate" )
                    return self.stock [ stock_key ]
        self.log.debug ( "not a partial alternate" ) 

        self.log.info ( "Unable to find item {}.".format ( item_string ) )
        return None
                
    def inflate_price ( self, item, rate ):
        self.log.debug ( "Inflating {} by {}.".format ( item [ 'li_key' ], rate ) )
        item [ 'real_price' ] *= rate
        item [ 'cash_price' ] = max ( 0, int ( round ( item [ 'real_price' ] ) ) )

    def inflate_turnover_time ( self, item ):
        if 'timestamp_sell' in list ( item.keys ( ) ):
            interval = time.time ( ) - item [ 'timestamp_sell' ]
            one_day_percentage = interval / ( 24 * 3600 )
            if one_day_percentage >= 1:
                item [ 'real_price' ] *= 1.05
                item [ 'cash_price' ] = round ( item [ 'real_price' ] )
                return
            rate = 2.05 - one_day_percentage
            item [ 'real_price' ] *= rate
            item [ 'cash_price' ] = round ( item [ 'real_price' ] )
            return

    def inflate_stock_depletion ( self, item, quantity ):
        """
        If player buys X % of stock, X % of price inflation occurs.
        """
        percentage = quantity / ( item [ 'in stock' ] + quantity )
        item [ 'real_price' ] *= ( 1 + percentage )
        item [ 'cash_price' ] = round ( item [ 'real_price' ] )
        
    def increase_stock ( self ):
        if not self.enabled:
            return
        for item in self.stock.keys ( ):
            self.log.debug ( "Considering item {}".format ( item ) )
            if self.stock [ item ] [ 'in stock' ] > 0:
                self.log.debug ( "increase_stock: {} still in stock.".format ( item ) )
                old_price = self.stock [ item ] [ 'real_price' ]
                self.inflate_price ( self.stock [ item ], 0.99 )
                self.log.info ( "Decreasing price of {}: {:.1f} -> {:.1f}.".format (
                    item, old_price, self.stock [ item ] [ 'real_price' ] ) )
            else:
                old_price = self.stock [ item ] [ 'real_price' ]
                self.inflate_price ( self.stock [ item ], 1.01 )
                self.log.info ( "Increasing price of {}: {:.1f} -> {:.1f}.".format (
                    item, old_price, self.stock [ item ] [ 'real_price' ] ) )
            if item not in list ( self.default_stock.keys ( ) ):
                self.log.debug ( "increase_stock: {} not in stock, but not default.".format ( item ) )
                continue
            if self.stock [ item ] [ 'in stock' ] < self.default_stock [ item ] [ 'in stock' ]:
                self.log.info ( "increase_stock: {} default item not in stock.".format ( item ) )
                old_stock = self.stock [ item ] [ 'in stock' ]
                self.stock [ item ] [ 'in stock' ] += math.ceil ( 0.1 * self.default_stock [ item ] [ 'in stock' ] )
                if old_stock == 0 and self.stock [ item ] [ 'in stock' ] != 0:
                    self.framework.console.say ( "{} {} now in stock!".format ( self.stock [ item ] [ 'in stock' ],
                                                                                item ) )


    def fix_negative_prices ( self ):
        for item in self.stock.keys ( ):
            if self.stock [ item ] [ 'real_price' ] <= 0:
                self.log.info ( "Fixing non-positive price of {}".format ( key ) )
                self.stock [ item ] [ 'real_price' ] = 0.1
            if self.stock [ item ] [ 'cash_price' ] <= 0:
                self.stock [ item ] [ 'cash_price' ] = round ( self.stock [ item ] [ 'real_price' ] )
        
    def update_pickle_from_default ( self ):
        for item in list ( self.default_stock.keys ( ) ):
            if item in list ( self.stock.keys ( )  ):
                continue
            self.log.info ( "+{}".format ( item ) )
            self.stock [ item ] = self.default_stock [ item ]
            self.framework.console.say ( "We now trade {}!".format ( item ) )
            
