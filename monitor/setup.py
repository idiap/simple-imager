#!/usr/bin/env python3
# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent

# Modules
from distutils.core import setup
import os

# Setup
setup(
    name = 'SI_Monitor',
    description = 'Simple Imager monitor service',
    long_description = \
"""
The Simple Imager monitor service allows to keep track of ongoing target hosts
installation and run ad-hoc hooks (scripts) for each significant step (start,
download, install, complete and error).
""",
    version = os.getenv('VERSION'),
    author = 'Cedric Dufour',
    author_email = 'http://cedric.dufour.name',
    license = 'GPL-2',
    url = 'https://github.com/cedric-dufour/simple-imager',
    download_url = 'https://github.com/cedric-dufour/simple-imager',
    package_dir = { '': 'src' },
    packages = [ 'SimpleImager', 'SimpleImager.Monitor' ],
    requires = [ 'daemon', 'flask' ],
    scripts = [ 'src/si_monitor.legacy', 'src/si_monitor.restful' ],
    )

