"""
Module scope: handle exceptions' side effects.
"""

import inspect
import sys
import traceback

def output_exception ( error ):
    """
    Print information about the error raised as exception.
    """
    __version__ = '0.1.0'
    changelog = {
        '0.1.0'  : "Changed tabs to spaces to mimic better ipython's traceback."
        }
    callee = inspect.stack ( ) [ 1 ] [ 0 ].f_code.co_name
    exception_info = sys.exc_info ( )
    message = "{} detected exception {}. From sys.exc_info ( ), its type is {}, value is {} and its traceback is: {}".format ( callee, error, exception_info [ 0 ], exception_info [ 1 ], exception_info [ 2 ] )
    tracebacks = traceback.extract_tb ( exception_info [ 2 ] )
    for entry in tracebacks:
        message += "\n  File '{}', line {}, in {}\n    {}".format ( entry [ 0 ], entry [ 1 ], entry [ 2 ], entry [ 3 ] )
    return message
