import framework
#import google_translate_api
import goslate
import logging
import sys
import threading
import time

class translator ( threading.Thread ):
    pass
    def __init__ ( self, framework_instance ):
        super ( self.__class__, self ).__init__ ( )
        self.log = logging.getLogger ( "framework.{}".format ( __name__ ) )
        self.log_level = logging.INFO
        self.log.setLevel ( self.log_level )
        self.daemon = True
        
        self.__version__ = '0.1.25'
        self.changelog = {
            '0.1.25' : "Use better logging system.",
            '0.1.24' : "Avoid translating empty messages.",
            '0.1.23' : "Fixed call to detect_languages since goslate only returns one language string, not a list.",
            '0.1.22' : "Fixed syntax error on loggin en trans.",
            '0.1.21' : "Refactored from google_translation_api to goslate.",
            '0.1.20' : "Added hook to more dynamic loglevel set.",
            '0.1.19' : "Refactored exception handling through framework.outpu_exception.",
            '0.1.18' : "Added desemoticon function to clean up messages before translation.",
            '0.1.17' : "Silencing log.info -> log.debug.",
            '0.1.16' : "Fixed syntax error when calling console.pm.",
            '0.1.15' : "Even more logging...",
            '0.1.14' : "More verbose logging of translations.",
            '0.1.13' : "Fixed /addlanguage misinterpreting codes.",
            '0.1.12' : "Fixed language codes taking 3 instead of 2 characters.",
            '0.1.11' : "Fixed commands choping last char.",
            '0.1.10' : "Refactored with new console.pm. Added Albanian.",
            '0.1.9'  : "Added gaelic.",
            '0.1.8'  : "Lowered threshold to guess language.",
            '0.1.7'  : "Added Lithuanian. Silenced chat about setting mother language.",
            '0.1.6'  : "Added estonian.",
            '0.1.5'  : "Silenced guessing new language. Added japanese mapping.",
            '0.1.4'  : "Silencing mother language guess.",
            '0.1.3'  : "Added mapping country KR : language KO (Korean)." }
        self.framework = framework_instance
        self.shutdown = False
        self.enabled = self.framework.preferences.mods [ self.__class__.__name__ ] [ 'enabled' ]
        self.commands = { 'addlanguage' : ( self.command_add_language, " /addlanguage <language code> will mark a language you DO speak." ),
                          'motherlanguage' : ( self.command_set_language, " /motherlanguage <language code> will set the language TO which you want translations." ),
                          'resetlanguage' : ( self.command_reset_language, " /resetlanguage <language code> will unset your language and mother language to the machine-guessed values, based on coutry code." )
        }
        self.language_codes = [ 'ch',
                                'cz',
                                'da',
                                'de',
                                'el',
                                'es',
                                'en',
                                'fi',
                                'fr',
                                'hr',
                                'hu',
                                'it',
                                'lt',
                                'nl',
                                'no',
                                'pl',
                                'pt',
                                'ro',
                                'ru',
                                'sk',
                                'sv',
                                'tr' ]

        #self.translator = google_translate_api.TranslateService ( )
        self.translator = goslate.Goslate ( ) 

        self.player_unregistered_language_counter = { }

    def __del__ ( self ):
        self.stop ( )
        
    def greet ( self ):
        if self.enabled == True:
            self.framework.console.say ( "%s mod version %s loaded." % ( self.__class__.__name__,
                                                                        self.__version__ ) )

    # commands

    def command_add_language ( self, msg_origin, msg_content ):
        possible_code = msg_content [ len ( "/addlanguage " ) : ]
        if possible_code.lower ( ) in self.language_codes:
            player = self.framework.server.get_player ( msg_origin )
            if player:
                if possible_code not in player.languages_spoken:
                    player.languages_spoken.append ( possible_code )
            self.framework.console.say ( 'Languages spoken by %s = %s.' % ( msg_origin,
                                                                           str ( player.languages_spoken ) ) )
        else:
            self.framework.console.say ( 'Language code %s not recognized.' % ( possible_code ) )

    def command_set_language ( self, msg_origin, msg_content ):
        if msg_content [ -2 : ].lower ( ) in self.language_codes:
            player = self.framework.server.get_player ( msg_origin )
            if player:
                player.language_preferred = msg_content [ -2 : ]
                self.framework.console.say ( "%s now receives translations in %s." % ( msg_origin,
                                                                                      msg_content [ -2 : ] ) )
        else:
            self.framework.console.pm ( self.framework.server.get_player (
                msg_origin ), "Language code {} not recognized.".format ( msg_content [ -2 : ] ) )

    def command_reset_language ( self, origin, message ):
        player = self.framework.server.get_player ( origin )
        player.languages_spoken = [ ]
        player.language_preferred = None
        self.guess_language ( player )
            
    # /commands

    def desemoticon ( self, message ):
        """
        Since translation mangles emoticons, its best to remove them altogether.
        """
        result = message
        emoticons = [
            ":D",
            ":P",
            "o/",
            ]
        for emoticon in emoticons:
            if " {} ".format ( emoticon ) in result:
                result.replace ( " {} ".format ( emoticon ), " " )
            if "{}".format ( emoticon ) == result:
                return ""

        return result

    def guess_language ( self, player ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        possible_language = self.framework.server.geoip.country_code_by_addr ( player.ip ).lower ( )
        if possible_language in self.language_codes:
            self.log.info ( "Setting player %s mother language as %s." % ( player.name, possible_language ) )
            player.languages_spoken = [ possible_language ]
            player.language_preferred = possible_language
            return

        exceptional_languages = { 'al' : 'sq',
                                  'at' : 'de',
                                  'be' : 'nl',
                                  'ca' : 'en',
                                  'ch' : 'de',
                                  'cn' : 'zh',
                                  'dk' : 'da',
                                  'ee' : 'et',
                                  'gb' : 'en',
                                  'gr' : 'el',
                                  'hk' : 'zh',
                                  'ie' : 'ga',
                                  'jp' : 'ja',
                                  'kr' : 'ko',
                                  'kz' : 'kk',
                                  'se' : 'sv',
                                  'ua' : 'ukr',
                                  'us' : 'en'
                                  }

        for country in exceptional_languages.keys ( ):
            language = exceptional_languages [ country ]
            if possible_language == country:
                player.languages_spoken = [ language ]
                player.language_preferred = language
                return
        
        self.log.error ( "Impossible to determine language for player %s"
                         " from country code %s." % ( player.name,
                                                      possible_language.upper ( ) ) )
        
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def player_spoke_unregistered_language ( self, player, language ):
        self.log.info ( "%s spoke 10+ chars in %s, which is not in %s" % ( player.name_sane,
                                                                           language,
                                                                           str ( player.languages_spoken ) ) )
        
        if player.steamid in self.player_unregistered_language_counter.keys ( ):
            if language in self.player_unregistered_language_counter [ player.steamid ].keys ( ):
                self.player_unregistered_language_counter [ player.steamid ] [ language ] += 1
                if self.player_unregistered_language_counter [ player.steamid ] [ language ] > 0:
                    self.log.info ( "Guessing that player %s speaks %s." % ( player.name_sane,
                                                                             language ) )
                    player.languages_spoken.append ( language )
            else:
                self.player_unregistered_language_counter [ player.steamid ] [ language ] = 1
        else:
            self.player_unregistered_language_counter [ player.steamid ] = { language : 1 }
                    
    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        
        while self.shutdown == False:
            time.sleep ( self.framework.preferences.loop_wait )
            self.log.setLevel ( self.log_level )
            if not self.enabled:
                continue
            
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
            
    def translate ( self, origin, message ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
        self.log.debug ( "translate: origin = '{}', message = '{}'".format ( origin, message ) )

        if not self.enabled:
            return
        
        if origin == "Server":
            return

        if message == "":
            return

        origin_player = self.framework.server.get_player ( origin )

        if origin_player == None:
            return

        if ( origin_player.languages_spoken == [ ] ):
            self.guess_language ( origin_player )

        try:
            detected_languages = self.translator.detect ( message )
            self.log.debug ( "detected_languages = '{}'.".format ( detected_languages ) )
        except Exception as e:
            self.log.error ( "{}\n  message = '{}'.".format ( framework.output_exception ( e ), message ) )
            return

        #most_probable_language = None
        #most_probable_ratio = 0
        #for language in detected_languages.keys ( ):
        #    if detected_languages [ language ] > most_probable_ratio:
        #        most_probable_language = language
        #        most_probable_ratio = detected_languages [ language ]
        most_probable_language = detected_languages

        self.log.debug ( "most_probable_language = {}".format ( most_probable_language ) )
        if ( most_probable_language == 'un' ):
            return

        if origin_player.languages_spoken is None:
            origin_player.languages_spoken = [ ]
                
        if ( most_probable_language not in origin_player.languages_spoken ):
            self.log.debug ( "{} spoke {}, which is not know to him/her {}".format ( 
                    origin_player.name_sane,
                    most_probable_language,
                    str ( origin_player.languages_spoken ) ) )
            if len ( message ) > 10:
                self.player_spoke_unregistered_language ( origin_player, most_probable_language )
            return
        else:
            self.log.debug ( "%s in %s" % ( most_probable_language,
                                            str ( origin_player.languages_spoken ) ) )

        translations_performed = { }

        self.log.debug ( "Checking if online players need translating." )
        for online_player in self.framework.server.get_online_players ( ):
            player = self.framework.server.get_player ( online_player )
            if ( player.languages_spoken == None or
                 player.languages_spoken == [ ] or
                 player.language_preferred == None or
                 isinstance ( player.language_preferred, list ) ):
                self.guess_language ( player )
                if not player.languages_spoken:
                    self.log.error ( "Cannot guess language for player {:s}.".format (
                        player.name_sane ) )
                    continue

            self.log.debug ( "Checking %s" % player.name_sane )
                
            if most_probable_language not in player.languages_spoken:
                self.log.debug ( "%s spoke %s, which is not in %s %s" % ( origin_player.name_sane,
                                                                          most_probable_language,
                                                                          player.name_sane,
                                                                          str ( player.languages_spoken ) ) )
                try:
                    self.log.debug ( "Translating from {} to {}: '{}'.".format ( most_probable_language,
                                                                                 player.language_preferred,
                                                                                 message ) )
                    #translation = self.translator.trans_sentence ( most_probable_language,
                    #                                               player.language_preferred,
                    #                                               self.desemoticon ( message ) )
                    translation = self.translator.translate ( self.desemoticon ( message ),
                                                              player.language_preferred,
                                                              most_probable_language )
                                                                   
                    self.log.debug ( "Translation is: '{}'.".format ( translation ) )
                except Exception as e:
                    self.log.error ( framework.output_exception ( e ) )
                    return

                self.framework.console.pm ( player, "({}) {}: {}".format (
                        most_probable_language,
                        origin_player.name_sane,
                        translation ),
                                            can_fail = False, loglevel = "DEBUG" )

                if player.language_preferred in translations_performed.keys ( ):
                    translations_performed [ player.language_preferred ] [ 1 ].append ( player.steamid )
                else:
                    translations_performed [ player.language_preferred ] = ( translation, [ player.steamid ] )

        self.log.debug ( "Logging effectuated translations." )
        for key in translations_performed.keys ( ):
            self.log.debug ( "message translated to {}".format ( key ) )
            player_names = ""
            for steamid in translations_performed [ key ] [ 1 ]:
                if player_names != "":
                    player_names += ", "
                player_names += self.framework.server.get_player ( steamid ).name_sane
            self.log.info( "CHAT %s (%s->%s): %s (To: %s)" % ( origin,
                                                               most_probable_language,
                                                               key,
                                                               translations_performed [ key ] [ 0 ],
                                                               player_names ) )

        if ( most_probable_language != 'en' and
             'en' not in translations_performed.keys ( ) ):
            self.log.info ( "CHAT %s (%s->en): %s" % ( origin,
                                                       most_probable_language,
                                                       #self.translator.trans_sentence ( most_probable_language,
                                                       #                                 'en',
                                                       #                                 self.desemoticon ( message ) ) ) )
                                                       self.translator.translate ( self.desemoticon ( message ),
                                                                                   'en',
                                                                                   most_probable_language ) ) )

            
        self.log.debug ( "</%s>" % ( sys._getframe ( ).f_code.co_name ) )

