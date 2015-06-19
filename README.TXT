7 Days to Die Server Mod Framework
----------------------------------

Initial design by Benjamin Keller, 2015.

Maintainer: Renato Borges.

This project is a Python 3 package that provides:

- An API to command the server.
- A game event handler.
- Common functionalities for third-party mods, such as a player database.

The vision for this project is that there is a need for a wide scope of features that many "flavored" mods require. For example, a "quest" mod will require a player database. Instead of each "quest" mod deploying its own, the use of a common framework would allow faster development and possible interplay of these mods (enhancing the game experience for everyone :)

The source code and documentation contained herein is free software, as specified in the GPLv3.0.

How to use
----------

Edit the file "preferences.cfg" and use the values correct for your server. In special, the server telnet address and password must be correct.

The path where the mod framework has been copied must be in yout PYTHONPATH.

Start your favorite Python 3 interpreter.

Import the framework.

You now have access to the console using <framework>.console:

>>> <framework>.console ( "lp" )

And other functions and classes under <framework>. It is recommended to read the code or use ipython and check the online documentation.
