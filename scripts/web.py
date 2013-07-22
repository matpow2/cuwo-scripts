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

    def __init__(self, factory):
        #WebFactory
        self.factory = factory

    def connectionMade(self):
        self.factory.connections.append(self)

    def dataReceived(self, data):
        data = json.loads(data)
        response = getattr(self.factory, data['request'], False)(data)
        if response:
            self.transport.write(response)
            return
        self.transport.write({'response': 'Unknown request'})

    def connectionLost(self, reason="No reason"):
        self.factory.connections.remove(self)


class WebFactory(Factory):
    noisy = False

    def __init__(self, server):
        self.connections = []
        self.web_server = server

    def get_players(self, *args):
        ##player_data = [name,level,class,specialization]
        player_data = {'name': '', 'level': '', 'klass': '', 'specialz': ''}
        players = {'response': 'get_players'}
        for connection in self.web_server.server.connections.values():
            player_id = connection.entity_id
            player_data['name'] = connection.entity_data.name
            player_data['level'] = connection.entity_data.level
            player_data['klass'] = connection.entity_data.class_type
            player_data['specialz'] = connection.entity_data.specialization
            players[player_id] = player_data
        return json.dumps(players)

    def command_kick(self, data):
        player_id = data['id']
        return self.web_server.kick_player("#" + player_id)

    def command_ban(self, data):
        player_id = data['id']
        if data['reason'] != "":
            return self.web_server.ban_player("#" + player_id, data['reason'])
        return self.web_server.ban_player("#" + player_id)

    def buildProtocol(self, addr):
        return WebProtocol(self)


class WebScriptProtocol(ConnectionScript):
    def on_join(self):
        self.parent.update_web("players")
        return True

    def on_unload(self):
        self.parent.update_web("players")
        return True


class SiteOverride(Site):
    noisy = False

    def log(self, request):
        pass


class WebScriptFactory(ServerScript):
    connection_class = WebScriptProtocol

    def on_load(self):
        self.config = self.server.config.web
        with open('./web/js/init.js', 'w') as f:
            f.write('var server_port = "%s"' % self.config.web_interface_port2)

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

        auth = resource.Resource()
        auth.putChild("", protected_resource)
        site = SiteOverride(auth)

        reactor.listenTCP(self.config.web_interface_port1, site)
        self.web_factory = WebFactory(self)
        reactor.listenTCP(self.config.web_interface_port2,
                          WebSocketFactory(self.web_factory))

    def update_web(self, entity):
        if entity == "players":
            for connection in self.web_factory.connections:
                connection.transport.write(self.web_factory.get_players())
            return
        pass

    def kick_player(self, player_id):
        player = get_player(self.server, player_id)
        player.kick()
        return "Success"


    def ban_player(self, player_id, *args):
        player = get_player(self.server, player_id)
        reason = ' '.join(args) or "No reason specified"
        self.server.call_scripts('ban', player.address.host, reason)
        return "Success"


def get_class():
    return WebScriptFactory
