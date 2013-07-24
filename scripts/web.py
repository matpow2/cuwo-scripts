import json

from zope.interface import implements
from twisted.cred import portal, checkers, credentials, error as credError
from twisted.internet import defer, reactor
from twisted.web import static, resource
from twisted.web.resource import IResource
from twisted.web.guard import HTTPAuthSessionWrapper
from twisted.web.guard import DigestCredentialFactory
from twisted.internet.protocol import Protocol, Factory

from twisted.web.server import Site
from twisted.web.static import File
from cuwo.script import (ServerScript, ConnectionScript, get_player)
from txws import WebSocketFactory


class PasswordDictChecker:
    implements(checkers.ICredentialsChecker)
    credentialInterfaces = (credentials.IUsernamePassword,
                            credentials.IUsernameHashedPassword)

    def __init__(self, config):
        self.passwords = config.passwords

    def requestAvatarId(self, credentials):
        username = credentials.username
        if username in self.passwords:
            # if credentials.password == self.passwords[username]:
            if credentials.checkPassword(self.passwords[username]):
                return defer.succeed(username)
            else:
                return defer.fail(
                    credError.UnauthorizedLogin("Bad password"))
        else:
            return defer.fail(
                credError.UnauthorizedLogin("No such user"))


class HttpPasswordRealm(object):
    implements(portal.IRealm)

    def __init__(self, myresource):
        self.myresource = myresource

    def requestAvatar(self, user, mind, *interfaces):
        if IResource in interfaces:
            # myresource is passed on regardless of user
            return IResource, self.myresource, lambda: None
        raise NotImplementedError()


class WebProtocol(Protocol):
    noisy = False
    auth = False
    auth_attempt = 0

    def __init__(self, factory):
        #WebFactory
        self.factory = factory

    def connectionMade(self):
        self.factory.connections.append(self)
        self.timeout_call = reactor.callLater(5.0, self.disconnect)

    def dataReceived(self, data):
        data = json.loads(data)
        if not self.auth:
            if data['request'] == 'auth':
                return self.transport.write(self.factory.auth(self, data))
            else:
                self.auth_attempt += 1
                return self.transport.write(json.dumps({'response': 'Unknown'}))
        response = getattr(self.factory, data['request'], False)(self, data)
        if response and self.auth:
            self.transport.write(response)
            return
        self.transport.write(json.dumps({'response': 'Unknown request'}))

    def connectionLost(self, reason="No reason"):
        self.factory.connections.remove(self)

    def disconnect(self):
        self.transport.loseConnection()
        self.factory.connectionLost("Disconnected")


class WebFactory(Factory):
    noisy = False

    def __init__(self, server):
        self.connections = []
        self.bad_entries = []
        #WebScriptFactory
        self.web_server = server
        self.auth_key = self.web_server.config.auth_key

    def get_players(self, *args):
        ##player_data = [name,level,class,specialization]
        player_data = {'name': '', 'level': '', 'klass': '', 'specialz': ''}
        players = {'response': 'get_players'}
        for player in self.web_server.server.players.values():
            player_id = player.entity_id
            player_data['name'] = player.entity_data.name
            player_data['level'] = player.entity_data.level
            player_data['klass'] = player.entity_data.class_type
            player_data['specialz'] = player.entity_data.specialization
            players[player_id] = player_data
        return json.dumps(players)

    def command_kick(self, ws_connect, data):
        player_id = data['id']
        return self.web_server.kick_player(player_id)

    def command_ban(self, ws_connect, data):
        player_id = data['id']
        if data['reason'] != "":
            return self.web_server.ban_player(player_id, data['reason'])
        return self.web_server.ban_player(player_id)

    def send_message(self, ws_connect, data):
        message = data['message']
        self.web_server.server.send_chat(message)
        return json.dumps({"response": "Success"})

    #Connection handlers
    def auth(self, ws_connect, data):
        if self.auth_key == data['key']:
            ws_connect.timeout_call.cancel()
            ws_connect.auth = True
            return json.dumps({"response": "Success"})
        elif ws_connect.auth_attempt == 5:
            self.bad_entries.append(ws_connect.host)
            ws_connect.disconnect()
        ws_connect.auth_attempt += 1

    def check_connections(self, addr):
        if addr.host in self.bad_entries:
            return False
        return True

    def buildProtocol(self, addr):
        check = self.check_connections(addr)
        if check is False:
            return None
        return WebProtocol(self)


class WebScriptProtocol(ConnectionScript):
    def on_join(self, event):
        self.parent.update_players()

    def on_unload(self):
        self.parent.update_players()

    def on_chat(self, event):
        self.parent.update_chat(self.connection.entity_id, event.message)


class SiteOverride(Site):
    noisy = False

    def log(self, request):
        pass


class WebScriptFactory(ServerScript):
    connection_class = WebScriptProtocol

    def on_load(self):
        self.config = self.server.config.web
        with open('./web/js/init.js', 'w') as f:
            port = self.config.web_interface_port2
            auth = self.config.auth_key
            f.write('var server_port = "%s";\n var auth_key = "%s"' % (port,
                                                                       auth))
        root = File('./web')
        root.indexNames = ['index.html']
        root.putChild('css', static.File("./web/css"))
        root.putChild('js', static.File("./web/js"))
        root.putChild('img', static.File("./web/img"))

        checker = PasswordDictChecker(self.config)
        realm = HttpPasswordRealm(root)
        p = portal.Portal(realm, [checker])

        credentialFactory = DigestCredentialFactory("md5",
                                                    "Cuwo Interface Login")
        protected_resource = HTTPAuthSessionWrapper(p, [credentialFactory])

        auth_resource = resource.Resource()
        auth_resource.putChild("", protected_resource)
        site = SiteOverride(auth_resource)

        reactor.listenTCP(self.config.web_interface_port1, site)
        self.web_factory = WebFactory(self)
        reactor.listenTCP(self.config.web_interface_port2,
                          WebSocketFactory(self.web_factory))

    #Web handlers
    def update_players(self, ):
        for connection in self.web_factory.connections:
            connection.transport.write(self.web_factory.get_players())
        return

    def update_chat(self, player_id, message):
        response = {'response': 'chat', 'player_id': player_id,
                    'message': message}
        for connection in self.web_factory.connections:
            connection.transport.write(json.dumps(response))
        return

    def kick_player(self, player_id):
        player = get_player(self.server, "#" + player_id)
        player.kick()
        return json.dumps({"response": "Success"})

    def ban_player(self, player_id, *args):
        player = get_player(self.server, "#" + player_id)
        reason = ' '.join(args) or "No reason specified"
        self.server.call_scripts('ban', player.address.host, reason)
        return json.dumps({"response": "Success"})


def get_class():
    return WebScriptFactory
