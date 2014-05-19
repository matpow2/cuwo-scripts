from cuwo.script import ServerScript, ConnectionScript, command, admin
from cuwo.types import MultikeyDict
from cuwo.packet import ServerChatMessage, write_packet

SETTINGS_FILE = "chat_settings"


class SettingException(Exception):
    def __init__(self, message):
        self.message = message


def create_message(message, entity_id=0):
    packet = ServerChatMessage()
    packet.entity_id = entity_id
    packet.value = message
    return write_packet(packet)


def process_setting(setting_type, value=None):
    setting_type = setting_type.lower()
    if setting_type == 'boolean':
        if not value:
            raise SettingException('A value must be provided')
        value = value.lower()
        if value == 'true' or value == '1':
            return True
        elif value == 'false' or value == '0':
            return False
        else:
            raise SettingException('Unknown value for boolean setting (True/False)')
    elif setting_type == 'string':
        if not value:
            raise SettingException('A value must be provided')
        return value
    elif setting_type == 'string_none':
        return value
    raise SettingException('Unknown setting type')


class Channel(object):
    def __init__(self, settings):
        self.name = settings['name']
        self.default = settings['default']
        self.password = settings['password']
        self.silent_join = settings['silent_join']
        self.can_leave = settings['can_leave']
        self.players = MultikeyDict()

    def add_player(self, player, suppress=False):
        entity_id = player.entity_id
        if entity_id not in self.players:
            self.players[(entity_id,)] = player
            if suppress:
                return
            if not self.silent_join:
                self.send_message('%s has joined the channel %s' % (
                                  player.name, self.name))
            else:
                player.send_chat('You\'ve joined the channel %s' % self.name)

    def remove_player(self, player):
        if player in self.players:
            del self.players[player]
            if self.default:
                return
            if not self.silent_join:
                self.send_message('%s has left the channel %s' % (
                                  player.name, self.name))
            else:
                player.send_chat('You\'ve left the channel %s' % self.name)

    def send_message(self, message, entity=None):
        if not message or len(message) < 1:
            return
        entity_id = 0
        if entity:
            entity_id = entity.entity_id
        message = '<%s> %s' % (self.name, message)
        data = create_message(message, entity_id)
        for player in self.players.values():
            player.transport.write(data)
        print '%s: %s' % (entity.name, message)


class ChatConnection(ConnectionScript):
    def on_join(self, event):
        self.parent.join_default(self.connection)

    def on_unload(self):
        self.parent.leave_all(self.connection)

    def on_chat(self, event):
        return self.parent.send_message(self.connection, event.message)


class ChatServer(ServerScript):
    connection_class = ChatConnection

    def on_load(self):
        self.active_channels = {}
        self.channels = {}

        channels = self.server.load_data(SETTINGS_FILE, [])
        for channel in channels:
            self.add_channel(Channel(channel))

    def has_channel(self, name):
        name = name.lower()
        return name in self.channels

    def add_channel(self, channel):
        self.channels[channel.name.lower()] = channel

    def remove_channel(self, name):
        if self.has_channel(name):
            del self.channels[name]

    def leave_all(self, player):
        if player.entity_id in self.active_channels:
            del self.active_channels[player.entity_id]
        for channel in self.channels.values():
            channel.remove_player(player)

    def join_default(self, player):
        for channel in self.channels.values():
            if channel.default:
                channel.add_player(player, True)

    def set_active_channel(self, player, name):
        self.active_channels[player.entity_id] = name

    def send_message(self, player, message):
        if player.entity_id in self.active_channels:
            name = self.active_channels[player.entity_id]
            if name:
                if self.has_channel(name):
                    channel = self.channels[name.lower()]
                    channel.send_message(message, player)
                    return False
        return message

    def save_channels(self):
        channels = []
        for channel in self.channels.values():
            channels.append({'name': channel.name,
                             'default': channel.default,
                             'silent_join': channel.silent_join,
                             'password': channel.password,
                             'can_leave': channel.can_leave})
        self.server.save_data(SETTINGS_FILE, channels)


def get_class():
    return ChatServer


@command
@admin
def create_channel(script, name, password=None):
    server = script.parent
    if not server.has_channel(name):
        server.add_channel(Channel({'name': name,
                                    'default': False,
                                    'silent_join': False,
                                    'password': password,
                                    'can_leave': True}))
        server.save_channels()
        return 'The channel %s has been created' % name
    return 'The channel %s does already exist' % name


@command
@admin
def delete_channel(script, name):
    server = script.parent
    if server.has_channel(name):
        server.remove_channel(name)
        server.save_channels()
        return 'The channel %s has been deleted' % name
    return 'The channel %s doesn\'t exist' % name


allowed_settings = {'default': 'boolean',
                    'password': 'string_none',
                    'silent_join': 'boolean',
                    'can_leave': 'boolean'}


@command
@admin
def modify_channel(script, name, setting, value=None):
    server = script.parent
    if not server.has_channel(name):
        return 'The channel %s doesn\'t exist' % name
    setting = setting.lower()
    if not setting in allowed_settings:
        return 'Unknown setting %s (%s)' % (setting,
                                            ', '.join(allowed_settings.keys()))
    setting_type = allowed_settings[setting]
    try:
        result = process_setting(setting_type, value)
    except SettingException as e:
        return e.message
    channel = server.channels[name.lower()]
    setattr(channel, setting, result)
    server.save_channels()
    return "The setting %s of channel %s has been changed to %s" % (
        setting, name, result)


@command
@admin
def list_channels(script):
    server = script.parent
    return 'Channels: %s' % ', '.join(server.channels.keys())


@command
def join(script, name, password=None):
    server = script.parent
    player = script.connection
    if not server.has_channel(name):
        return 'The channel %s doesn\'t exist' % name
    channel = server.channels[name.lower()]
    if player.entity_id in channel.players:
        return 'You\'ve already joined the channel %s' % name
    if channel.password and channel.password != password:
        return 'The channel %s doesn\'t exist' % name
    channel.add_player(player)


@command
def leave(script, name):
    server = script.parent
    player = script.connection
    if not server.has_channel(name):
        return 'The channel %s doesn\'t exist' % name
    channel = server.channels[name.lower()]
    if player.entity_id not in channel.players:
        return 'You aren\'t in the channel %s' % name
    if not channel.can_leave:
        return 'You can\'t leave the channel %s' % name
    channel.remove_player(player)


@command
def channels(script):
    server = script.parent
    player = script.connection
    channels = []
    for channel in server.channels.values():
        if player in channel.players:
            channels.append(channel.name)
    return 'Joined channels: %s' % ', '.join(channels)


@command
def channel(script, name=None):
    server = script.parent
    player = script.connection
    if name and not server.has_channel(name):
        return 'The channel %s doesn\'t exist' % name
    channel = server.channels[name.lower()]
    if player not in channel.players:
        return 'The channel %s doesn\'t exist' % name
    server.set_active_channel(player, name)
    return 'Your messages will be written to the channel %s' % name
