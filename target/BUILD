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

