# Boot to GUI USB disk creator

This is a script that creates from scratch a Debian stable image that
boots, starts up X and launches a single GUI application. There is no
shutdown.

To create an image insert a USB disk, check what its device name is
(`/dev/sdd` assumed below) and then run:

    sudo ./createimage.py /dev/sdd

Boot a computer with the USB stick to use it.

This script probably only works on Debian and its derivatives like
Ubuntu.

The application is run as root.

The application is implemented in Gtk+ 3 and Python 3. If you want
some other framework, you need to change the dependency list and the
application's install command.
