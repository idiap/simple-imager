# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent
## Simple Imager
# Copyright (C) 2017 Idiap Research Institute [SimpleImager]
# (please refer to the COPYRIGHT and CREDITS.* files for further information)


#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
import os
import socket

# Extra
# ... deb: python-flask
from flask import \
    Flask, \
    _app_ctx_stack, \
    abort, \
    jsonify, \
    request, \
    Response

# Simple Imager
from SimpleImager.Monitor import \
    SI_Monitor_Backend


#------------------------------------------------------------------------------
# FLASK
#------------------------------------------------------------------------------

# Application
#------------------------------------------------------------------------------

"""
Simple Imager Monitor Flask application.

Configuration parameters are:
  SI_MONITOR_DATABASE_FILE [REQUIRED]
    Path to (SQLite) database file
  SI_MONITOR_HOOKS_DIR [OPTIONAL]
    Path to hooks (scripts) directory
  SI_MONITOR_LOG_REDIRECT [OPTIONAL; default:True]
    Whether to redirect the monitoring backend log to the Flask logger
  SI_MONITOR_BACKEND_GLOBAL [OPTIONAL; default:False]
    Whether to use a global monitoring backend

Configuration may be set manually, using 'SI_Monitor_Flask.config.update(...)',
or by setting the SI_MONITOR_FLASK_CONFIG environment variable for use by
'SI_Monitor_Flask.config.from_ennvar(...)'.
"""
SI_Monitor_Flask = Flask(__name__)


# Configuration
#------------------------------------------------------------------------------

# From environment-defined configuration file
SI_Monitor_Flask.config.from_envvar('SI_MONITOR_FLASK_CONFIG', silent=True)
__SI_Monitor_Backend = None


# Backend
#------------------------------------------------------------------------------

def getBackend():
    """
    Retrieve a ready-to-use monitoring backend.
    """

    oFlaskAppContext = _app_ctx_stack.top
    oBackend = getattr(oFlaskAppContext, 'SI_Monitor_Backend', None)
    if oBackend is None:
        if 'SI_MONITOR_BACKEND_GLOBAL' in SI_Monitor_Flask.config and SI_Monitor_Flask.config['SI_MONITOR_BACKEND_GLOBAL']:
            global __SI_Monitor_Backend
            if __SI_Monitor_Backend is None:
                __SI_Monitor_Backend = SI_Monitor_Backend(
                    SI_Monitor_Flask.config['SI_MONITOR_DATABASE_FILE'],
                    SI_Monitor_Flask.config['SI_MONITOR_HOOKS_DIR'],
                    _bThreadSafe=True
                )
            oBackend = __SI_Monitor_Backend
        else:
            # NOTE: Flask application context is thread-local; backend need not be thread-safe
            oBackend = SI_Monitor_Backend(
                SI_Monitor_Flask.config['SI_MONITOR_DATABASE_FILE'],
                SI_Monitor_Flask.config['SI_MONITOR_HOOKS_DIR'],
                _bThreadSafe=False
            )
        if not 'SI_MONITOR_LOG_REDIRECT' in SI_Monitor_Flask.config or SI_Monitor_Flask.config['SI_MONITOR_LOG_REDIRECT']:
            oBackend.setLogger(SI_Monitor_Flask.logger)
        oFlaskAppContext.SI_Monitor_Backend = oBackend
    return oBackend


# API
#------------------------------------------------------------------------------

@SI_Monitor_Flask.route('/update', methods=['POST'])
def update():
    """
    Update target status; returns an 'HTTP 400/Bad Request' in case of failure,
    'HTTP 200/OK' otherwise.
    """

    sClient = '%s:n/a' % request.remote_addr
    SI_Monitor_Flask.logger.debug('[%s(update)] Processing client request' % sClient)

    # Validation
    if not request.json:
        SI_Monitor_Flask.logger.error('[%s] Invalid data (no JSON)' % sClient)
        abort(400)
    dData = request.json
    if not 'mac' in dData or not dData['mac']:
        SI_Monitor_Flask.logger.error('[%s] Missing/empty MAC address' % sClient)
        abort(400)
    if not 'status' in dData or not dData['status']:
        SI_Monitor_Flask.logger.error('[%s] Missing/empty status' % sClient)
        abort(400)

    # Parse data
    try:
        sMAC = dData['mac']
        sIP = request.remote_addr
        try:
            sHost = socket.gethostbyaddr(sIP)[0]
        except Exception as e:
            sHost = 'n/a'
        sStatus = dData['status']
        sMessage = dData['message'] if 'message' in dData else ''
        iProgress = -1
        iSpeed = -1
        if sStatus=='init':
            pass
        elif sStatus=='start':
            pass
        elif sStatus=='pre-install':
            if 'progress' in dData:
                iProgress = int(dData['progress'])
        elif sStatus=='download':
            if 'progress' in dData:
                iProgress = int(dData['progress'])
            if 'speed' in dData:
                iSpeed = int(dData['speed'])
        elif sStatus=='install':
            if 'progress' in dData:
                iProgress = int(dData['progress'])
        elif sStatus=='post-install':
            if 'progress' in dData:
                iProgress = int(dData['progress'])
        elif sStatus=='complete':
            pass
        elif sStatus=='error':
            if 'errno' in dData:
                if len(sMessage): sMessage += ' '
                sMessage += '[%d]' % int(dData['errno'])
        else:
            raise RuntimeError('Invalid status (%s)\n' % sStatus)
            abort(400)
    except Exception as e:
        SI_Monitor_Flask.logger.error('[%s] Invalid data (parsing error); Data=%s; %s' % (sClient, str(dData).strip('\n'), str(e)))
        abort(400)
    SI_Monitor_Flask.logger.debug('[%s] Data parsed; MAC=%s, IP=%s, Host=%s, Status=%s, Message=%s, Progress=%d, Speed=%d' % (sClient, sMAC, sIP, sHost, sStatus, sMessage, iProgress, iSpeed))

    # Update backend
    try:
        oBackend = getBackend()
        oBackend.update(sMAC, sIP, sHost, sStatus, sMessage, iProgress, iSpeed, sClient)
    except Exception as e:
        abort(400)

    # Done
    return ''


@SI_Monitor_Flask.route('/query/html', methods=['GET'])
@SI_Monitor_Flask.route('/query/html/<string:_sKey>/<string:_sValue>', methods=['GET'])
def queryHTML(_sKey=None, _sValue=None):
    """
    Query target(s) status; returns an 'HTTP 400/Bad Request' in case of failure,
    'HTTP 200/OK' along (HTML) status data otherwise.
    """
    
    sClient = '%s:n/a' % request.remote_addr
    SI_Monitor_Flask.logger.debug('[%s(queryHTML)] Processing client request' % sClient)

    # Query backend
    from six import string_types
    from cgi import escape
    try:
        oBackend = getBackend()
        tFields = ('mac', 'ip', 'host', 'status', 'change', 'message', 'progress', 'speed', 'heartbeat', 'elapsed')
        sHTML = '<TABLE>\n'
        sHTML += '<TR><TH>'+'</TH><TH>'.join(tFields)+'</TH></TR>\n'
        for dStatus in oBackend.query(_sKey, _sValue, sClient):
            sHTML += '<TR><TD>'+'</TD><TD>'.join(escape(dStatus[k]) if isinstance(dStatus[k], string_types) else str(dStatus[k]) for k in tFields)+'</TD></TR>\n'
        sHTML += '</TABLE>\n'
        return Response(sHTML, mimetype='text/html')
    except Exception as e:
        abort(400)


@SI_Monitor_Flask.route('/query/json', methods=['GET'])
@SI_Monitor_Flask.route('/query/json/<string:_sKey>/<string:_sValue>', methods=['GET'])
def queryJSON(_sKey=None, _sValue=None):
    """
    Query target(s) status; returns an 'HTTP 400/Bad Request' in case of failure,
    'HTTP 200/OK' along (JSON) status data otherwise.
    """
    
    sClient = '%s:n/a' % request.remote_addr
    SI_Monitor_Flask.logger.debug('[%s(queryJSON)] Processing client request' % sClient)

    # Query backend
    try:
        oBackend = getBackend()
        return jsonify({'si_monitor': oBackend.query(_sKey, _sValue, sClient)})
    except Exception as e:
        abort(400)


@SI_Monitor_Flask.route('/query/csv', methods=['GET'])
@SI_Monitor_Flask.route('/query/csv/<string:_sKey>/<string:_sValue>', methods=['GET'])
@SI_Monitor_Flask.route('/query/csv/<string:_sKey>/<string:_sValue>/<string:_sSeparator>', methods=['GET'])
def queryCSV(_sKey=None, _sValue=None, _sSeparator=','):
    """
    Query target(s) status; returns an 'HTTP 400/Bad Request' in case of failure,
    'HTTP 200/OK' along (CSV) status data otherwise.
    """
    
    sClient = '%s:n/a' % request.remote_addr
    SI_Monitor_Flask.logger.debug('[%s(queryCSV)] Processing client request' % sClient)

    # Magic
    if _sKey=='_': _sKey=None
    if _sValue=='_': _sValue=None

    # Query backend
    from six import string_types
    try:
        oBackend = getBackend()
        tFields = ('mac', 'ip', 'host', 'status', 'change', 'message', 'progress', 'speed', 'heartbeat', 'elapsed')
        sCSV = ''
        for dStatus in oBackend.query(_sKey, _sValue, sClient):
            sCSV += _sSeparator.join('"%s"' % dStatus[k].replace('"', '""') if isinstance(dStatus[k], string_types) else str(dStatus[k]) for k in tFields)+'\n'
        return Response(sCSV, mimetype='text/csv')
    except Exception as e:
        abort(400)


# Main
#------------------------------------------------------------------------------

if __name__=='__main__':
    # Update the config using the OS environment
    if not 'SI_MONITOR_FLASK_CONFIG' in os.environ:
        SI_Monitor_Flask.config.update(dict(
            SI_MONITOR_DATABASE_FILE = os.getenv('SI_MONITOR_DATABASE_FILE', '/var/lib/simple-imager/si_monitor.sqlite'),
            SI_MONITOR_HOOKS_DIR = os.getenv('SI_MONITOR_HOOKS_DIR', '/etc/simple-imager/si_monitor.hooks.d')
        ))

    # Run the Flask application using its internal (Werkzeug) server
    sBind = os.getenv('SI_MONITOR_BIND', '*')
    if sBind=='*': sBind = ''
    SI_Monitor_Flask.run(
        host = sBind,
        port = os.getenv('SI_MONITOR_PORT', 8080),
        debug = True
    )
