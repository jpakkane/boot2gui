#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

window = Gtk.Window(title="Standalone app")
label = Gtk.Label("This is a sample GUI application")
window.add(label)
window.show_all()
window.connect("destroy", Gtk.main_quit)
Gtk.main()