import json

from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

from twisted.web import static
from twisted.web.server import Site
from twisted.web.static import File
from cuwo.script import (ServerScript, ConnectionScript, get_player)
from txws import WebSocketFactory


class WebProtocol(Protocol):
    def __init__(self, factory):
        #WebFactory
        self.factory = factory

    def connectionMade(self):
        self.factory.connections.append(self)

    def dataReceived(self, data):
        data = json.loads(data)

        if data['want'] == 'players':
            self.transport.write(self.factory.get_players())
        elif data['want'] == 'Ban':
            if data['reason'] == '':
                self.factory.web_server.ban_player(data['name'])
                return
            self.factory.web_server.ban_player(data['name'],
                                               data['reason'])
            return
        elif data['want'] == 'Kick':
            self.factory.web_server.kick_player(data['name'])
            return
        else:
            self.transport.write(
                json.dumps({'response': "This shit got serious"}))
            return

    def connectionLost(self, reason="No reason"):
        self.factory.connections.remove(self)


class WebFactory(Factory):
    def __init__(self, server):
        self.connections = []
        self.web_server = server

    def get_players(self):
        ##player_data = [names[],levels[],class[],specialization[], hp_multp[]]
        player_data = [[], [], [], [], []]
        for connection in self.web_server.server.connections.values():
            player_data[0].append(connection.entity_data.name)
            player_data[1].append(connection.entity_data.character_level)
            player_data[2].append(connection.entity_data.class_type)
            player_data[3].append(connection.entity_data.specialization)
            player_data[4].append(connection.entity_data.max_hp_multiplier)
        players = {
            'response': 'players', 'names': player_data[0],
            'levels': player_data[1], 'klass': player_data[2],
                'specialz': player_data[3], 'health_mult': player_data[4]
        }
        return json.dumps(players)

    def buildProtocol(self, addr):
        return WebProtocol(self)


class WebScriptProtocol(ConnectionScript):
    def on_join(self):
        self.parent.update_web("players")
        return True

    def on_unload(self):
        self.parent.update_web("players")
        return True


class WebScriptFactory(ServerScript):
    connection_class = WebScriptProtocol

    def on_load(self):
        from configs import web
        with open('./web/js/init.js', 'w') as f:
            f.write('var server_port = "%s"' % web.web_interface_port2)

        root = File('./web')
        root.indexNames = ['index.html']
        root.putChild('css', static.File("./web/css"))
        root.putChild('js', static.File("./web/js"))
        root.putChild('img', static.File("./web/img"))

        reactor.listenTCP(web.web_interface_port1, Site(root))
        self.web_factory = WebFactory(self)
        reactor.listenTCP(web.web_interface_port2,
                          WebSocketFactory(self.web_factory))

    def update_web(self, entity):
        if entity == "players":
            for connection in self.web_factory.connections:
                connection.transport.write(self.web_factory.get_players())
            return
        pass

    def kick_player(self, name):
        player = get_player(self.server, name)
        player.kick()

    def ban_player(self, name, *args):
        player = get_player(self.server, name)
        reason = ' '.join(args) or "No reason specified"
        self.server.call_scripts('ban', player.address.host, reason)


def get_class():
    return WebScriptFactory