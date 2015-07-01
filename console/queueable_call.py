import threading
import time

class queueable_call ( threading.Thread ):
    def __init__ ( self ):
        super ( self.__class__, self ).__init__ ( )
        
        self.timestamp_creation  = time.time ( )
        self.timestamp_begun     = 0
        self.timestamp_execution = 0
        self.timestamp_finish    = 0
        self.function            = self.nop
        self.function_args       = [ ]
        self.function_kwargs     = { }
        self.kill_timer          = float ( "inf" )
        self.lock_key_pairs      = [ ]
        self.loop_wait           = 0.1
        self.prerequisites       = [ ]
        self.retirement_age      = float ( "inf" )

    def run ( self ):
        while not self.become_executable ( ):
            time.sleep ( self.loop_wait )
        self.execute ( )
        
    def become_executable ( self ):
        now = time.time ( )
        if now - self.timestamp_creation > self.retirement_age:
            return False

        conditions = True
        for requisite in self.prerequisites:
            if requisite.timestamp_finish == 0:
                conditions = False
                break
        if not conditions:
            return False
            
        return self.get_all_locks ( )

    def destroyable ( self ):       
        now = time.time ( )
        if now - self.timestamp_creation > self.retirement_age:
            return True
        if ( self.timestamp_execution != 0 and
             now - self.timestamp_execution > self.kill_timer ):
            return True
        return False

    def get_all_locks ( self ):
        for lock_key_pair in self.lock_key_pairs:
            if self != lock_key_pair [ 0 ] ( self ):
                self.let_all_locks ( )
                return False
        return True

    def let_all_locks ( self ):
        for lock_key_pair in self.lock_key_pairs:
            lock_key_pair [ 1 ] ( self )
                    
    def nop ( self ):
        return

    def execute ( self ):
        self.get_all_locks ( )
        self.timestamp_execution = time.time ( )
        self.function ( *self.function_args, **self.function_kwargs )
        self.timestamp_finish = time.time ( )
        self.let_all_locks ( )
