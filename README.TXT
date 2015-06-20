7 Days to Die Server Mod Framework
----------------------------------

Initial design by Benjamin Keller, 2015.

Maintainer: Renato Borges.

This project is a Python 3 package that provides:

- An API to command the server.
- A game event handler.
- Common functionalities for third-party mods, such as a player database.

The vision for this project is that there is a need for a wide scope of features that many "flavored" mods require. For example, any "quest" mod will require a player database. Instead of each "quest" mod deploying its own, the use of a common framework would allow faster development and possible interplay of these mods (enhancing the game experience for everyone :)

The source code and documentation contained herein is free software, as specified in the GPLv3.0.

How to use
----------

Edit the file "preferences.cfg" and use the values correct for your server. In special, the server telnet address and password must be correct.

The path where the mod framework has been copied must be in yout PYTHONPATH.

Start your favorite Python 3 interpreter.

Import the framework. Start the framework by passing the path of configuration file:

>>> <framework>.config ( "/home/example/example_path.cfg" )

If the configuration is correct and the telnet is accessible, you now have access to the console using <framework>.console:

>>> <framework>.console ( "lp" )

And other functions and classes under <framework>. It is recommended to read the code or use ipython and check the online documentation.

Please notice that the output from the game server will not be display directly on your session; for instance, the return from "lp" won't echo on the interpreter. All output from the server is parsed through a parser module, and events are generated accordingly. Therefore, the result from the "lp" command being sent is that the players database will be updated with the latest info.

How to use mods with the framework
----------------------------------

To add a mod, these are required:

1 - The mod is a copy of the template_mod.py file contained in the framework, and it resides in a directory that is in your PYTHONPATH.

2 - The python module name for this mod, and the class name for this mod, are the same. (For example, the file "place_protection.py" contains the class "place_protection".

3 - Your preferences file contains an entry for that mod. For example:

place_protection = mod
place_protection_enabled = True
place_protection_module = place_protection

(The "place_protection-module" variable must equal the name of the python module / class specified in #2).

How it works
------------

Each module, and the framework itself, are threads ran by the Python interpreter. When you add the correct configuration for a mod, it will be dynamically loaded by the framework when it is initialized.

At every "loop_wait" interval, the framework will refresh its data, and the mods (unless changed) will re-run themselves.

This means that each mod runs in parallel; so actions taken by them could interefere with one another, it is up to the developers to ensure this is done properly or not at all.

When the mod ends, its thread is closed. Also, when the framework is shutdown, each mod is stopped.

A simple example
----------------

Make sure you can run the framework as-is. Verify that the log files show that the framework gets information from the server, and that you can give console commands through the Python interpreter.

Copy the template_mod.py file into a new file.

Edit this new file, and rename the "template" class with the same name as the file (and therefore, this name should be a valid Python identifier - no spaces, no special characters).

In the area of this file indicated as being safe for adding the mod code, add some code to be run, as a first draft of your mod.

Edit your configurations file and add your mod information, as specified above.

Save all files, and restart the framework. Your code should now be run as one of the mods within the framework.
