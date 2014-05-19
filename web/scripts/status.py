from cuwo.script import ServerScript
from twisted.internet import defer, reactor
from twisted.internet.error import AlreadyCalled
from twisted.internet.protocol import ClientCreator
from twisted.internet.task import LoopingCall
from twisted.protocols.basic import FileSender
from twisted.protocols.ftp import FTPClient
from twisted.python import log as tlog
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

import json
import os
import time


def log(message):
    if len(tlog.theLogPublisher.observers) == 1:
        print '[status.py] %s' % message
    else:
        tlog.callWithLogger(StatusLogger, tlog.msg, message)


class StatusLogger(object):
    @staticmethod
    def logPrefix():
        return 'status.py'


class Updater(object):
    update_rate = None
    call = None

    def __init__(self, server, config):
        self._server = server
        if 'update_rate' in config:
            self.update_rate = config['update_rate']
        self.loop = LoopingCall(self.do_update)

    def start(self):
        if self.is_running:
            return
        self.do_update()

    def stop(self):
        if not self.is_running:
            return
        try:
            self.call.cancel()
        except AlreadyCalled:
            pass
        self.call = None

    def do_update(self):
        self.update(self.generate_content())
        self.call = reactor.callLater(self.update_rate, self.do_update)

    def generate_content(self):
        server = self._server
        config = server.config.base
        data = {
            'name': config.server_name,
            'max': config.max_players,
            'players': len(server.players),
            'mode': server.get_mode() or 'default',
            'last_update': int(time.time())
        }
        return json.dumps(data)

    def update(self, content):
        pass

    @property
    def is_running(self):
        return self.call is not None

    @staticmethod
    def factory(server, config, update_rate=60):
        global updaters
        type = config['type'].lower()
        cls = updaters.get(type, None)
        if not cls:
            log('Invalid updater type: %s' % type)
            return
        updater = cls(server, config)
        if not updater.update_rate:
            updater.update_rate = update_rate
        return updater


class LocalUpdater(Updater):
    def __init__(self, server, config):
        Updater.__init__(self, server, config)
        self.path = config['path']

    def update(self, content):
        path = os.path.realpath(self.path)
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(path, 'wb') as f:
            f.write(content)


class FTPUpdater(Updater):
    client = None

    def __init__(self, server, config):
        Updater.__init__(self, server, config)
        self.server = config['server']
        self.port = config['port']
        self.username = config['username']
        self.password = config['password']
        path = config['path']
        self.folder = os.path.dirname(path)
        self.filename = os.path.basename(path)
        self.passive = config.get('passive', True)

    def do_update(self):
        self.update()

    def update(self):
        creator = ClientCreator(reactor, FTPClient, self.username,
                                self.password, passive=self.passive)
        creator.connectTCP(self.server, self.port).addCallbacks(
            self.connection_made, self.on_error)

    def disconnect(self):
        self.client.quit().addCallbacks(self.on_quit, self.on_error)

    def connection_made(self, client):
        self.client = client
        if self.folder != '':
            self.client.changeDirectory(self.folder).addCallbacks(
                self.on_folder_changed, self.on_error)
        else:
            self.upload_status()

    def upload_status(self):
        d, _ = self.client.storeFile(self.filename)
        d.addCallbacks(self.on_write_status, self.on_error)

    def on_folder_changed(self, changed):
        self.upload_status()

    def on_write_status(self, consumer):
        content = self.generate_content()
        buffer = StringIO(content)
        sender = FileSender()
        d = sender.beginFileTransfer(buffer, consumer)
        d.addCallbacks(lambda _: self.on_write_completed(consumer),
                       self.on_error)
        return d

    def on_write_completed(self, consumer):
        consumer.finish()
        self.disconnect()

    def on_error(self, error):
        error_type = error.type.__name__
        if error_type == 'ConnectError':
            log_message = 'Failed to connect to ftp (%s)' % (
                error.getErrorMessage())
        else:
            log_message = 'Failure (%s)' % error
        if log_message != '':
            log('[FTPUpdater, %s:%s, %s] %s' % (self.server, self.port,
                self.username, log_message))
        if self.client:
            self.client.quit().addCallbacks(self.on_quit, callbackArgs=(True,))
        else:
            self.stop()

    def on_quit(self, message, failed=False):
        self.client = None
        if failed:
            self.stop()
        else:
            self.call = reactor.callLater(self.update_rate, self.do_update)


updaters = {
    'local': LocalUpdater,
    'ftp': FTPUpdater
}


class StatusServer(ServerScript):
    connection_class = None
    ftp = None
    updaters = []

    def on_load(self):
        config = self.server.config.status
        update_rate = config.global_update_rate
        entries = config.updaters
        for entry in entries:
            self.updaters.append(Updater.factory(self.server, entry,
                                                 update_rate))

        for updater in self.updaters:
            updater.start()

    def on_unload(self):
        for updater in self.updaters:
            updater.stop()
        self.updaters = []


def get_class():
    return StatusServer
