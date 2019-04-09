Simple Imager Target - Build Instructions
*****************************************

Step-by-Step
============

One MUST prepare a pristine build environment (chroot-ed or in a VM).

!!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!!

  In order to prevent nasty build failures, do NOT install any package
  that may conflict with the (latest-to-date) packages downloaded from
  upstream. Ideally, install ONLY the build tools (make, gcc, etc.).

!!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!!

Download all upstream resources:

  make download

Build everything (initrd and kernel):

  # WARNING: This takes time!
  make build

Install everything in the release directory (initrd and kernel):

  make release

Create a tarball with the initrd and kernel:

  make tarball

Get enlighted:

  make help


The Debian Way
==============

!!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!!

  Using fakeroot WILL lead to build failures!

!!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!! WARNING !!!

Using Debian packaking ad-hoc command:

  dpkg-buildpackage -us -uc -b


Cleaning Up
===========

The build tree:

  make clean
  # or
  dpkg-buildpackage -T clean

Including the downloaded resources (really?!):

  make distclean


The Developer Way
=================

In order to introspect/troubleshoot the build procedure, developers may want
to proceed step-by-step:

  # kernel
  make linux_firmware_download
  make linux_download
  make linux_configure
  make linux_build

  # initrd
  make initrd_mkdir
  # (look at the initrd.rul file for the *ordered* list of packages)
  for package in zlib gzip [...]; do
    make ${package}_download
    make ${package}_configure
    make ${package}_build
    make ${package}_install
  done

  # finalize
  make initrd_finalize
  make initrd_install
  make kernel_install
  make release

