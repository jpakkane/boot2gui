#!/usr/bin/env python3

#  Copyright (C) 2017 Jussi Pakkanen.
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of version 3, or (at your option) any later version,
# of the GNU General Public License as published
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, subprocess, shutil

class ImageCreator:
    
    def __init__(self):
        self.chrootdir = 'rootdir'
        self.basetar = 'baseroot'
        self.basetarfname = 'baseroot.tar.xz'
        self.distro = 'stretch'

    def build_base_image(self):
        if os.path.exists(self.basetarfname):
            return
        if os.path.exists(self.chrootdir):
            shutil.rmtree(self.chrootdir)
        os.mkdir(self.chrootdir)
        subprocess.check_call(['debootstrap', self.distro, self.chrootdir, 'http://ftp.fi.debian.org/debian'])
        shutil.make_archive(self.basetar, 'xztar', '.', self.chrootdir)

if __name__ == '__main__':
    ic = ImageCreator()
    if os.getuid() != 0:
        sys.exit('This script must be run with root privileges.')
    ic.build_base_image()
