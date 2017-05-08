# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent
## Simple Imager
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
import errno
import logging
import signal
import socket
import sys

# Simple Imager
from SimpleImager.Monitor import \
    SI_Monitor_Daemon, \
    SI_Monitor_Flask


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class SI_Monitor_DaemonRestful(SI_Monitor_Daemon):
    """
    Simple Imager Monitor daemon; RESTful interface (using Flask/Werkzeug)

    This provides a simple daemon based on Flask built-in (Werkzeug) server,
    without any form of encryption/authentication. If you need those features,
    please setup your own WSGI server for the 'SI_Monitor_Flask' application.
    """


    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self):
        """
        Constructor.
        """

        # Parent
        SI_Monitor_Daemon.__init__(self)


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    # Initialization
    #------------------------------------------------------------------------------

    def _initArgumentParser(self):
        """
        Creates the arguments parser (and help generator).
        """

        # Parent
        SI_Monitor_Daemon._initArgumentParser(self)

        # Add arguments to parser

        # ... bind address
        self._oArgumentParser.add_argument(
            '-B', '--bind', type=str,
            metavar='<bind-address>',
            default='*',
            help='Specific IP address to bind the daemon to (default:*)')

        # ... port
        self._oArgumentParser.add_argument(
            '-P', '--port', type=int,
            metavar='<tcp-port>',
            default=8080,
            help='TCP port to have the daemon listen on (default:8080)')


    # Service
    #------------------------------------------------------------------------------

    def _run(self):
        """
        Run the (daemon/foreground) service; returns a non-zero exit code in case of failure.
        """

        # Parent
        iReturn = SI_Monitor_Daemon._run(self)
        if iReturn:
            return iReturn

        # Create and run the RESTful (Flask/Werkzeug) service
        try:
            if self._oArguments.bind=='*':
                self._oArguments.bind = ''

            # We must let Flask/Werkzeug deal with those
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)

            # Configure and run the Flask application using its built-in (Werkzeug) server
            # ... make Werkzeug a little less noisy
            if not self._oArguments.debug:
                logging.getLogger('werkzeug').setLevel(logging.WARNING)
            # ... configure the Flask application with the command-line arguments
            SI_Monitor_Flask.config.update(dict(
                SI_MONITOR_DATABASE_FILE = self._oArguments.database,
                SI_MONITOR_HOOKS_DIR = self._oArguments.hooks,
                SI_MONITOR_LOG_REDIRECT = False,
                SI_MONITOR_BACKEND_GLOBAL = True
            ))
            # ... use our own logging handler(s)
            del SI_Monitor_Flask.logger.handlers[:]
            for oHandler in self._oLogger.handlers if self._oLogger.handlers else logging.getLogger('si_monitor').handlers:
                SI_Monitor_Flask.logger.addHandler(oHandler)
            # ... let's Rock and let's Roll!
            SI_Monitor_Flask.run(host=self._oArguments.bind, port=self._oArguments.port, threaded=True, debug=(self._oArguments.foreground and self._oArguments.debug))
        except Exception as e:
            sys.stderr.write('ERROR: Failed to start the RESTful service; %s\n' % str(e))
            return errno.EIO

        # Done
        sys.stderr.write('INFO: Done\n')
        return 0
