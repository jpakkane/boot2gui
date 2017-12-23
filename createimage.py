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

import parted

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
    
    def __init__(self, usb_device_name):
        self.chrootdir = 'rootdir'
        self.basetar = 'baseroot'
        self.basetarfname = 'baseroot.tar.gz'
        self.installedtar = 'installed'
        self.installedtarfname = 'installed.tar.gz'
        self.distro = 'stretch'
        self.imagedir = 'image'
        self.livedir = 'image/live'
        self.isolinuxdir = 'image/isolinux'
        self.usb_mount_dir = 'usbmount'
        self.usb_device_name = usb_device_name
        self.usb_partition = usb_device + '1'
        self.isolinux_cfg_file = os.path.join(self.isolinuxdir, 'isolinux.cfg')

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
        self.chroot_run(['apt-get', 'clean'])
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
        open(self.isolinux_cfg_file, 'w').write(isolinux_cfg)

    def create_usb_partitions(self):
        # Code earlier hase verified that usb drive is unmounted.
        with open(self.usb_device_name, 'wb') as p:
            p.write(bytearray(1024))
        subprocess.check_call('sync')
        device = parted.getDevice(self.usb_device_name)
        disk = parted.freshDisk(device, 'msdos')
        geometry = parted.Geometry(device=device,
                                   start=1,
                                   length=device.getLength() - 1)
        filesystem = parted.FileSystem(type='fat32', geometry=geometry)
        partition = parted.Partition(disk=disk,
                                     type=parted.PARTITION_NORMAL,
                                     fs=filesystem,
                                     geometry=geometry)
        disk.addPartition(partition=partition,
                          constraint=device.optimalAlignedConstraint)
        partition.setFlag(parted.PARTITION_BOOT)
        disk.commit()
        subprocess.check_call('sync')

    def create_disk(self):
        subprocess.check_call(['syslinux', '-i', self.usb_partition])
        subprocess.check_call(['dd',
                               'if=/usr/lib/syslinux/mbr/mbr.bin',
                               'of=' + self.usb_device_name,
                               'conv=notrunc',
                               'bs=440',
                               'count=1'])
        os.makedirs(self.usb_mount_dir, exist_ok=True)
        import time
        time.sleep(3) # The kernel seems to take a while to detect new partitions.
        subprocess.check_call(['mount', self.usb_partition, self.usb_mount_dir])
        try:
            self._copy_files_to_usb()
        finally:
            subprocess.call(['umount', self.usb_mount_dir])
            shutil.rmtree(self.usb_mount_dir, ignore_errors=True)

    def _copy_files_to_usb(self):
        for f in glob('/usr/lib/syslinux/modules/bios/*.c32'):
            shutil.copy2(f, self.usb_mount_dir)
        shutil.copy2('/boot/memtest86+.bin',
                     os.path.join(self.usb_mount_dir, 'memtest'))
        shutil.copy2(self.isolinux_cfg_file,
                     os.path.join(self.usb_mount_dir, 'syslinux.cfg'))
        shutil.copy2('/usr/share/misc/pci.ids', self.usb_mount_dir)
        for f in glob(os.path.join(self.livedir, '*')):
            shutil.copy2(f, self.usb_mount_dir)

def check_system_requirements(usb_device):
    if not usb_device.startswith('/dev/'):
        sys.exit('Invalid usb stick device: ' + usb_device)
    for line in subprocess.check_output('mount', universal_newlines=True).split('\n'):
        if line.startswith(usb_device):
            sys.exit('Partition %s on device %s is mounted.' % (line.split()[0], usb_device))
    try:
        open(usb_device, 'rb').close()
    except OSError:
        sys.exit('Could not open device %s for reading.' % usb_device)
    if shutil.which('mksquashfs') is None:
        sys.exit('mksquashfs not installed.') 
    if shutil.which('syslinux') is None:
        sys.exit('syslinux not installed.')
    if os.getuid() != 0:
        sys.exit('This script must be run with root privileges.')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit('%s <usb stick device name e.g. /dev/sdd')
    usb_device = sys.argv[1]
    check_system_requirements(usb_device)
    ic = ImageCreator(usb_device)
    ic.build_base_image()
    ic.install_deps()
    ic.create_live_image()
    ic.create_usb_partitions()
    ic.create_disk()
