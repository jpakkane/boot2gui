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

# Builds a bootable USB stick from scratch.
# http://willhaley.com/blog/create-a-custom-debian-stretch-live-environment-ubuntu-17-zesty/

import os, sys, subprocess, shutil
from glob import glob

isolinux_cfg = '''UI menu.c32

prompt 0
menu title Debian Live

timeout 300

label Debian Live 4.9.0-3-686
menu label ^Debian Live 4.9.0-3-686
menu default
kernel /live/vmlinuz1
append initrd=/live/initrd1 boot=live

label hdt
menu label ^Hardware Detection Tool (HDT)
kernel hdt.c32
text help
HDT displays low-level information about the systems hardware.
endtext

label memtest86+
menu label ^Memory Failure Detection (memtest86+)
kernel /live/memtest
'''


class ImageCreator:
    
    def __init__(self):
        self.chrootdir = 'rootdir'
        self.basetar = 'baseroot'
        self.basetarfname = 'baseroot.tar.gz'
        self.installedtar = 'installed'
        self.installedtarfname = 'installed.tar.gz'
        self.distro = 'stretch'
        self.imagedir = 'image'
        self.livedir = 'image/live'
        self.isolinuxdir = 'image/isolinux'

    def build_base_image(self):
        if os.path.exists(self.basetarfname):
            return
        if os.path.exists(self.chrootdir):
            shutil.rmtree(self.chrootdir)
        os.mkdir(self.chrootdir)
        subprocess.check_call(['debootstrap', self.distro, self.chrootdir, 'http://ftp.fi.debian.org/debian'])
        shutil.make_archive(self.basetar, 'gztar', '.', self.chrootdir)

    def install_deps(self):
        if os.path.exists(self.installedtarfname):
            return
        if os.path.exists(self.chrootdir):
            shutil.rmtree(self.chrootdir)
        shutil.unpack_archive(self.basetarfname)
        assert(os.path.exists(self.chrootdir))
        open(os.path.join(self.chrootdir, 'etc/hostname'), 'w').write('boot2gui')
        self.chroot_run(['apt-get', 'update'])
        self.chroot_run(['apt-get', 'install', '--no-install-recommends',
                         '--yes', '--force-yes', 'linux-image-amd64',
                         'live-boot', 'systemd-sysv'])
        self.chroot_run(['apt-get', 'install', '--no-install-recommends',
                         '--yes', '--force-yes', 'network-manager', 'xserver-xorg-core',
                         'xserver-xorg', 'xinit', 'xterm', 'nano'])
        pc = subprocess.Popen(['chroot', self.chrootdir, 'passwd'], universal_newlines=True,
                              stdin=subprocess.PIPE)
        pc.communicate('root\nroot\n')
        assert(pc.returncode == 0)
        shutil.make_archive(self.installedtar, 'gztar', '.', self.chrootdir)

    def chroot_run(self, cmd):
        subprocess.check_call(['chroot', self.chrootdir] + cmd)

    def create_live_image(self):
        if os.path.exists(self.imagedir):
            shutil.rmtree(self.imagedir)
        if os.path.exists(self.chrootdir):
            shutil.rmtree(self.chrootdir)
        shutil.unpack_archive(self.installedtarfname)
        os.makedirs(self.livedir, exist_ok=True)
        os.makedirs(self.isolinuxdir, exist_ok=True)
        subprocess.check_call(['mksquashfs', self.chrootdir,
                               os.path.join(self.livedir, 'filesystem.squashfs'),
                               '-e', 'boot'])
        a = glob(os.path.join(self.chrootdir, 'boot/vmlinuz*'))
        assert(len(a) == 1)
        kernel = a[0]
        a = glob(os.path.join(self.chrootdir, 'boot/initrd*'))
        assert(len(a) == 1)
        initrd = a[0]
        shutil.copy2(kernel, os.path.join(self.livedir, 'vmlinuz1'))
        shutil.copy2(initrd, os.path.join(self.livedir, 'initrd1'))
        open(os.path.join(self.isolinuxdir, 'isolinux.cfg'), 'w').write(isolinux_cfg)

if __name__ == '__main__':
    
    ic = ImageCreator()
    if shutil.which('syslinux') is None:
        sys.exit('syslinux not installed')
    if os.getuid() != 0:
        sys.exit('This script must be run with root privileges.')
    ic.build_base_image()
    #ic.install_deps()
    ic.create_live_image()
