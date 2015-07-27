import framework
import logging
import pymysql
import sys
import threading
import time

class database ( threading.Thread ):
    def __init__ ( self, framework_instance ):
        super ( self.__class__, self ).__init__ ( )
        self.__version__ = "0.2.5"
        self.changelog = {
            '0.2.5'  : "Better logging",
            '0.2.4'  : "Added cursor.close to exceptions also.",
            '0.2.3'  : "Calling cursor.close and framework.output_exception when appropriate.",
            '0.2.2'  : "Return all rows when more than one match.",
            '0.2.1'  : "Support for where_dict on update record.",
            '0.2.0'  : "Refactored version."
        }
        self.framework = framework_instance
        self.log = logging.getLogger ( __name__ )
        self.log_level = logging.INFO
        self.daemon = True
        self.shutdown = False

        self.connection = None
        self.expected_tables = {
            'players' : "( steamid bigint primary key,"
                        "name varchar ( 30 ) )",
            'fear'    : "( steamid bigint primary key,"
                        " fear float,"
                        " latest_check_timestamp double,"
                        " latest_fear_timestamp double,"
                        " latest_fear_warning int,"
                        " latest_state varchar ( 10 ),"
                        " latest_state_timestamp double )",
            'friends' : "( steamid bigint,"
                        "friend bigint )",
            'portals' : "( steamid bigint,"
                        "name varchar ( 30 ),"
                        "position_x int,"
                        "position_y int,"
                        "position_z int )"
        }
        self.queue = [ ]
        self.queue_lock = framework.lock ( )

    def __del__ ( self ):
        self.stop ( )

    def run ( self ):
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )
                             
        # Check database connection is up.
        if not self.check_mysql_connection ( ):
            # Try to up it.
            self.open_mysql_connection ( )
            # Check again.
            if not self.check_mysql_connection ( ):
                self.log.error ( "Could not open MySQL connection, aborting." )
                #self.stop ( )
                return

        # Check config is good.
        if not self.check_tables ( ):
            # Try to reconfigure.
            self.configure_tables ( )
            # check again.
            if not self.check_tables ( ):
                self.log.error ( "Could not configure db tables." )
                self.stop ( )
                return

        while not self.shutdown:
            self.log.debug ( "Starting database loop." )
            time.sleep ( 1 )

            if not self.connection:
                self.log.warning ( "Connection became None during runtime." )
                #self.stop ( )

            self.log.setLevel ( self.log_level )

            self.dequeue ( )

        self.close_mysql_connection ( )
            
        self.log.debug ( "<%s>" % ( sys._getframe ( ).f_code.co_name ) )

    def stop ( self ):
        self.shutdown = True
        self.close_mysql_connection ( )

    # Connection methods.

    def check_mysql_connection ( self ):
        if not self.connection:
            return False
        return True

    def close_mysql_connection ( self ):
        if self.check_mysql_connection ( ):
            self.connection.close ( )
            self.connection = None

    def open_mysql_connection ( self ):
        try:
            self.connection = pymysql.connect ( host = 'localhost',
                                                user = self.framework.preferences.mysql_user_name,
                                                passwd = self.framework.preferences.mysql_user_password,
                                                db = self.framework.preferences.mysql_db_name,
                                                charset = 'utf8mb4',
                                                cursorclass = pymysql.cursors.DictCursor )
        except Exception as e:
            self.log.error ( framework.output_exception ( e ) )
            self.connection = None
        self.log.debug ( "MySQL connection opened." )

    # Config methods. They suppose connection is fine.

    def check_tables ( self ):
        try:
            cursor = self.connection.cursor ( )
            cursor.execute ( "show tables" )
            self.connection.commit ( )
            result = cursor.fetchall ( )
            cursor.close ( )
        except Exception as e:
            self.log.error ( framework.output_exception ( e ) )
            cursor.close ( )
        result_tables = [ ]
        for entry in result:
            for key in entry.keys ( ):
                result_tables.append ( entry [ key ] )
        expected_tables = list ( self.expected_tables.keys ( ) )
        if sorted ( result_tables ) != sorted ( expected_tables ):
            self.log.debug ( "Tables in db '{}' differ from the expected '{}'!".format ( result,
                                                                                         expected_tables ) )
            return False
        return True

    def configure_tables ( self ):
        """
        If the db is empty, populate it with a structure defined in self.expected_tables.
        """
        try:
            cursor = self.connection.cursor ( )
            cursor.execute ( "show tables" )
            self.connection.commit ( )
            result = cursor.fetchall ( )
            cursor.close ( )
        except Exception as e:
            self.log.error ( framework.output_exception ( e ) )
            cursor.close ( )
            return
            
        if result != ( ):
            self.log.error ( "Database '{}' is not empty AND is different from expected!".format ( result ) )
            return

        for table in self.expected_tables.keys ( ):
            try:
                cursor = self.connection.cursor ( )
                cursor.execute ( "create table {} {}".format ( table, self.expected_tables [ table ] ) )
                self.connection.commit ( )
                cursor.close ( )
            except Exception as e:
                self.log.error ( framework.output_exception ( e ) )
                cursor.close ( )

    # Data methods. They suppose connection and tables are valid.

    def delete_record ( self, table, columns_values ):
        """
        Enqueues request to delete_record_processor.
        """
        self.enqueue ( { 'function' : self.delete_record_processor,
                         'args' : ( table, columns_values ),
                         'kwargs' : { } } )
        
    def delete_record_processor ( self, table, columns_values ):
        """
        columns_values must be a dict with columns as keys.
        """
        for key in columns_values.keys ( ):
            try:
                where_string += " and {} = '{}'".format ( key, columns_values [ key ] )
            except UnboundLocalError:
                where_string = "{} = '{}'".format ( key, columns_values [ key ] )
                continue
            sql = "delete from {} where {}".format ( table, 
                                                     where_string )
        try:
            cursor = self.connection.cursor ( )
            self.log.debug ( "sql = '{}'.".format ( sql ) )
            cursor.execute ( sql )
            self.connection.commit ( )
            cursor.close ( )
        except Exception as e:
            self.log.error ( framework.output_exception ( e ) )
            cursor.close ( )

    def insert_record ( self, table, columns_values ):
        """
        Enqueues request to insert_record_processor.
        """
        self.enqueue ( { 'function' : self.insert_record_processor,
                         'args' : ( table, columns_values ),
                         'kwargs' : { } } )
        
    def insert_record_processor ( self, table, columns_values ):
        """
        columns_values must be a dict with columns as keys.
        """
        columns_string = "( "
        for column in columns_values.keys ( ):
            if columns_string != "( ":
                columns_string += ", "
            columns_string += str ( column )
        columns_string += " )"
        self.log.debug ( "columns_string = '{}'.".format ( columns_string ) )

        for key in columns_values.keys ( ):
            entry = columns_values [ key ]
            try:
                values_string += ", '{}'".format ( entry )
            except UnboundLocalError:
                values_string = "'{}'".format ( entry )
        values_string = "( " + values_string + " )"
        self.log.debug ( "values_string = '{}'.".format ( values_string ) )
        sql = "insert into {} {} values {}".format ( table, 
                                                     columns_string,
                                                     values_string )
        try:
            cursor = self.connection.cursor ( )
            self.log.debug ( "sql = '{}'.".format ( sql ) )
            cursor.execute ( sql )
            self.connection.commit ( )
            cursor.close ( )
        except Exception as e:
            self.log.error ( framework.output_exception ( e ) )
            cursor.close ( )
        
    def select_record ( self, table, columns_values ):
        """
        columns_values must be a dict with columns as keys.
        """
        for key in columns_values.keys ( ):
            try:
                where_string += " and {} = '{}'".format ( key, columns_values [ key ] )
            except UnboundLocalError:
                where_string = "{} = '{}'".format ( key, columns_values [ key ] )
                continue
        sql = "select * from {} where {}".format ( table, 
                                                   where_string )
        try:
            cursor = self.connection.cursor ( )
            self.log.debug ( "sql = '{}'.".format ( sql ) )
            cursor.execute ( sql )
            self.connection.commit ( )
            res = cursor.fetchall ( )
            cursor.close ( )
            self.log.debug ( "res = {}".format ( res ) )
            return res
        except Exception as e:
            self.log.error ( "select_record with sql = '{}' exception: {}".format ( 
                    sql, framework.output_exception ( e ) ) )
            cursor.close ( )
            return None

    def update_record ( self, table, columns_values ):
        """
        Enqueues request to update_record_processor.
        """
        self.enqueue ( { 'function' : self.update_record_processor,
                         'args' : ( table, columns_values ),
                         'kwargs' : { } } )
        
    def update_record_processor ( self, table, columns_values, where_dict = None ):
        """
        columns_values must be a dict with columns as keys.
        """
        for key in columns_values.keys ( ):
            if key == "steamid":
                continue
            try:
                update_string += ", {} = '{}'".format ( key, columns_values [ key ] )
            except UnboundLocalError:
                update_string = "{} = '{}'".format ( key, columns_values [ key ] )
                continue

        if not where_dict:
            where_string = "steamid = '{}'".format ( columns_values [ 'steamid' ] )
        else:
            for key in where_dict.keys ( ):
                try:
                    where_string += ", {} = '{}'".format ( key, where_dict [ key ] )
                except UnboundLocalError:
                    where_string  =   "{} = '{}'".format ( key, where_dict [ key ] )
                    continue
        sql = "update {} set {} where {}".format ( table, 
                                                   update_string,
                                                   where_string )
        try:
            cursor = self.connection.cursor ( )
            self.log.debug ( "sql = '{}'.".format ( sql ) )
            cursor.execute ( sql )
            self.connection.commit ( )
            cursor.close ( )
        except Exception as e:
            self.log.error ( framework.output_exception ( e ) )
            cursor.close ( )

    # queue
           
    def enqueue ( self, data ):
        self.log.debug ( "enqueue: {}.".format ( data ) )
        self.queue_lock.get ( )
        self.queue.append ( data )
        self.queue_lock.let ( )

    def dequeue ( self ):
        self.queue_lock.get ( )
        data = None
        if len ( self.queue ) > 0:
            data = self.queue.pop ( )
        self.queue_lock.let ( )
        if data:
            self.log.debug ( "dequeue: {}.".format ( data ) )
            self.process ( data )

    def process ( self, data ):
        data [ 'function' ] ( *data [ 'args' ], **data [ 'kwargs' ] )
