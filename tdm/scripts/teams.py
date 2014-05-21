
"""
Teams script by Sarcen

This is a script to create teams of players for PvE and PvP purposes

It should not be used together with the PvP script, unless you want team
members to be able to kill each other.

This is intended as library script that should be imported into other scripts
see teamdeatmatch.py for example.
"""

from cuwo.script import ServerScript, ConnectionScript, command, admin
from cuwo.common import is_bit_set, set_bit
from cuwo.entity import EntityData, APPEARANCE_BIT
from cuwo.packet import EntityUpdate, HitPacket
from cuwo.vector import Vector3

import random
import math

entity_packet = EntityUpdate()


class TeamConnection(ConnectionScript):
    def on_load(self):
        self.assists = {}
        self.appearance_updated = False
        self.excluded = False
        self.last_hit_time = 0
        self.last_hit_by = None
        self.is_dead = False
        self.tag_duration = 5.0
        self.health = 0
        self.last_health = 0
        self.health_undefined = True

        self.team = None
        self.old_team = None

        self.first_update = True
        self.requires_team_update = False
        self.updated_hostile_type = False
        self.auto_balanced = False

        self.team_invites = []

    def on_join(self, event):
        self.parent.playerscripts[self.connection.entity_id] = self

    def silent_damage(self, damage):
        packet = HitPacket()
        packet.critical = 0
        packet.damage = damage
        packet.entity_id = self.connection.entity_id
        packet.target_id = self.connection.entity_id
        packet.hit_dir = Vector3()
        packet.pos = self.connection.entity_data.pos
        packet.hit_type = 2
        packet.show_light = 0
        packet.something8 = 0
        packet.stun_duration = 0
        packet.skill_hit = 0
        self.server.update_packet.player_hits.append(packet)

    def on_hit(self, event):
        return self.parent.on_hit(self, event)

    def on_unload(self):
        self.leave_team()
        self.parent.auto_rebalance_teams()
        if self.connection.entity_id in self.parent.playerscripts:
            del self.parent.playerscripts[self.connection.entity_id]

    def on_entity_update(self, event):
        entity_data = self.connection.entity_data
        entity_data.appearance.entity_flags = 32
        entity_data.hostile_type = self.parent.default_hostile_type
        entity_data.power_base = 4

        # means it was completely updated before this new update fired.
        mask_zero = entity_data.mask == 0

        if self.first_update:
            event.mask = set_bit(event.mask, 7, True)
            event.mask = set_bit(event.mask, 37, True)
            entity_data.mask |= event.mask
            self.updated_hostile_type = True
            self.requires_team_update = True
        else:
            # Suppress hostile_type and power_base
            event.mask = set_bit(event.mask, 7, False)
            event.mask = set_bit(event.mask, 37, False)
            entity_data.mask |= event.mask

        if is_bit_set(event.mask, 27):
            if self.health_undefined:
                self.health_undefined = False
                self.health = entity_data.hp

            self.healing_reductions()

            if entity_data.hp <= 0 and not self.is_dead:
                self.is_dead = True
                self.on_death()

            if entity_data.hp > 0 and self.is_dead:
                self.is_dead = False
                self.last_health = entity_data.hp
                self.health = entity_data.hp
                # self.on_revive()

        if (not self.first_update
                and not self.auto_balanced
                and not self.updated_hostile_type
                and not self.requires_team_update
                and mask_zero):
            self.auto_balanced = True
            self.parent.auto_balance_player(self)

        if (not mask_zero and self.auto_balanced
                and not self.appearance_updated):
            self.appearance_updated = True
            event.mask = set_bit(event.mask, APPEARANCE_BIT, True)
            entity_data.mask |= event.mask

        if self.requires_team_update and not self.updated_hostile_type:
            self.send_team_entity_updates()

        self.updated_hostile_type = False
        self.first_update = False

    def healing_reductions(self):
        entity_data = self.connection.entity_data
        self.last_health = self.health
        self.health = entity_data.hp
        health_gain = self.health - self.last_health
        if not self.is_dead and health_gain > 0:
            actual_health_gained = (health_gain *
                                    self.parent.selfheal_effectiveness)

            health_damage = health_gain - actual_health_gained
            # just suppress really minor differences
            if health_damage > 5:
                self.silent_damage(health_damage)
            self.health += actual_health_gained

    def send_team_entity_updates(self):
        self.requires_team_update = False

        if self.team is not None:
            # update the members from the new team
            self.update_team_members(self.team, 0, 0)

        if self.old_team is not None:
            # reset the members from the old team
            self.update_team_members(self.old_team,
                                     4,
                                     self.parent.default_hostile_type)
            self.old_team = None

    def update_team_members(self, team, power_base, hostile_type):
        entity = EntityData()
        entity.mask = 0
        entity.mask = set_bit(entity.mask, 7, True)
        entity.mask = set_bit(entity.mask, 37, True)

        entity.power_base = power_base
        entity.hostile_type = hostile_type
        for m in team.members:
            if m == self:
                continue
            entity_id = self.connection.entity_id
            entity_packet.set_entity(entity,
                                     entity_id,
                                     entity.mask)
            m.connection.send_packet(entity_packet)

            entity_id = m.connection.entity_id
            entity_packet.set_entity(entity,
                                     entity_id,
                                     entity.mask)
            self.connection.send_packet(entity_packet)

    def on_death(self):
        if self.team is not None:
            self.team.on_death(self, self.last_hit_by)

        if self.last_hit_by is None:
            return None

        if self.loop.time() - self.last_hit_time > self.tag_duration:
            return None

        if self.last_hit_by.team is not None:
            self.last_hit_by.team.on_kill(self, self.last_hit_by)

        self.last_hit_by.on_player_kill(self)

    def on_player_kill(self, player):
        if self.last_hit_by.team is not None:
            self.last_hit_by.team.on_kill(self, self.last_hit_by)

        killer = self.connection.name
        killed = player.connection.name
        self.server.send_chat('%s killed %s!' % (killer,
                                                 killed))

        killed.assists = {}

    def kick_team(self):
        self.leave_team()

    def invite_team(self, t):
        if t not in self.team_invites:
            self.team_invites.append(t)
            message = 'You have been invited to join team "%s".' % t.name
            self.connection.send_chat(message)

    def accept_team(self):
        if len(self.team_invites) > 0:
            t = self.team_invites[len(self.team_invites) - 1]
            self.join_team(t)

    def join_team(self, t, forced_join=False):
        if t == self.team:
            return

        is_invited = (t in self.team_invites)

        if self.team is not None:
            self.leave_team()

        if t.add(self, forced_join or is_invited):
            self.requires_team_update = True
            self.team = t

            # if somehow we ended up in the old team
            # make sure we clear it...
            if self.team == self.old_team:
                self.old_team = None

        if is_invited:
            self.team_invites.remove(t)

    def leave_team(self):
        if self.team is not None:
            self.team.remove(self)

            # if we havent updated yet and are changing team
            # then we dont need to be setting this
            if not self.requires_team_update:
                self.old_team = self.team
            self.team = None
            self.requires_team_update = True


class Team(object):

    def __init__(self, server, name):
        self.members = []
        self.server = server
        self.name = name
        self.invite_only = False
        self.leader = None

    def send_chat(self, message, exception=None, source=None):
        prefix = "[TEAM LEADER] " if source == self.leader else "[TEAM] "
        for m in self.members:
            if m == exception:
                continue
            m.connection.send_chat(prefix + message)

    def add(self, script, is_invited):
        if script in self.members:
            return True

        if self.invite_only and not is_invited:
            message = 'Team "%s" is invite only.' % self.name
            script.connection.send_chat(message)
            return False

        self.members.append(script)
        script.connection.send_chat('You have joined team "%s".' % self.name)
        message = '%s has joined your team.' % script.connection.name
        self.send_chat(message, script)

        self.promote_leader()
        return True

    def set_invite_only(self, invite_only):
        self.invite_only = invite_only
        message = 'invite only' if self.invite_only else 'open'
        return 'Team is now %s.' % message

    def promote_leader(self):
        if self.leader is None or self.leader not in self.members:
            if len(self.members) > 0:
                self.set_leader(self.members[0])

    def set_leader(self, leader):
        self.leader = leader
        message = 'You are now team leader of "%s".' % self.name
        self.leader.connection.send_chat(message)

        message = '%s is now team leader of "%s".' % (leader.connection.name,
                                                      self.name)
        self.send_chat(message, leader)

    def remove(self, script):
        if script not in self.members:
            return

        self.members.remove(script)
        script.connection.send_chat('You have left team "%s".' % self.name)
        message = '%s has left your team.' % script.connection.name
        self.send_chat(message, script)

        if len(self.members) == 0:
            self.server.on_team_empty(self)
            return

        self.promote_leader()

    def on_kill(self, killed, killer):
        pass

    def on_death(self, victim, killer=None):
        pass


class TeamServer(ServerScript):
    default_hostile_type = 1
    locked_teams = False
    auto_balance = False
    suppress_damage = False
    allow_join_when_locked = True
    destroy_empty_teams = True
    connection_class = TeamConnection
    team_class = Team
    pvp_damage_multiplier = [0.5, 0.5, 0.5, 0.5]
    pvp_stun_multiplier = 0.75
    selfheal_effectiveness = 0.33
    outgoing_healing_effectiveness = 0.50
    teams = {}

    playerscripts = {}

    def get_mode(self, event):
        return 'teams'

    def on_hit(self, script, event):
        if self.suppress_damage:
            return False

        # Suppress self packets..., I'm wondering if the vanilla server
        # even sends these..
        if event.packet.target_id == event.packet.entity_id:
            return False

        # None player entity id
        if event.packet.target_id not in self.playerscripts:
            return

        class_id = script.connection.entity_data.class_type
        playerscript = self.playerscripts[event.packet.target_id]

        if event.packet.damage > 0:
            event.packet.damage *= self.pvp_damage_multiplier[class_id-1]
            playerscript.last_hit_by = script
            playerscript.last_hit_time = self.loop.time()
            playerscript.assists[script] = self.loop.time()
        else:
            event.packet.damage *= self.outgoing_healing_effectiveness

        event.packet.stun_duration *= self.pvp_stun_multiplier

        playerscript.health -= event.packet.damage

    def get_team(self, name):
        lowername = name.lower()
        if lowername in self.teams:
            return self.teams[lowername]
        return None

    def on_team_empty(self, t):
        if self.destroy_empty_teams:
            self.destroy_team(t)

    def destroy_team(self, t):
        lowername = t.name.lower()
        if lowername in self.teams:
            del self.teams[lowername]

        for player in self.children:
            invite_list = player.team_invites
            if t in invite_list:
                invite_list.remove(t)

    def create_team(self, name):
        team = self.team_class(self, name)
        lowername = name.lower()
        self.teams[lowername] = team
        return team

    def balance_player(self, script):
        lowest_team = None
        lowest_member_count = -1

        for t in self.teams.values():
            member_count = len(t.members)
            if lowest_team is None or lowest_member_count > member_count:
                lowest_team = t
                lowest_member_count = member_count

        if lowest_team is not None:
            script.join_team(lowest_team, True)

    def shuffle_teams(self):
        all_players = []
        for m in self.children:
            if m.excluded:
                continue
            all_players.append(m)
            m.leave_team()
        random.shuffle(all_players)

        for player in all_players:
            self.balance_player(player)

    def balance_teams(self):
        unteamed = []
        player_count = 0
        for m in self.children:
            if m.excluded:
                continue
            player_count += 1

            if m.team is None:
                unteamed.append(m)

        for player in unteamed:
            self.balance_player(player)

        max_member_count = math.ceil(float(player_count) /
                                     float(len(self.teams)))

        for t in self.teams.values():
            while len(t.members) > max_member_count:
                member = t.members[len(t.members) - 1]
                self.balance_player(member)

    def auto_balance_player(self, script):
        if self.auto_balance:
            self.balance_player(script)

    def auto_rebalance_teams(self):
        if self.auto_balance:
            self.balance_teams()

    # Command implementations

    def team_list(self, script):
        message = '%s Team(s): ' % len(self.teams)

        teams_open = []
        teams_closed = []

        for name, t in self.teams.items():
            teaminfo = '"%s" %sM ' % (name, len(t.members))
            if t.leader is not None:
                teaminfo += '(%s)' % t.leader.connection.name
            if not t.invite_only:
                teams_open.append(teaminfo)
            else:
                teams_closed.append(teaminfo)

        teams_open.sort()
        teams_closed.sort()

        if len(teams_closed) > 0:
            message += ' Invite Only: ' + ', '.join(teams_closed)
        if len(teams_open) > 0:
            message += ' Open: ' + ', '.join(teams_open)

        return message

    def team_create(self, script, name):
        if self.locked_teams:
            return 'Teams are locked.'

        if name in self.teams:
            message = 'Team with name "%s" already exists.' % name
            return message

        team = self.create_team(name)

        if script is not None:
            script.join_team(team)

        return 'Team "%s" created.' % name

    def team_accept(self, script):
        script.accept_team()

    def team_join(self, script, name):
        if not self.allow_join_when_locked and self.locked_teams:
            return 'Teams are locked.'

        t = self.get_team(name)
        if t is None:
            return 'There is no team named "%s"' % name

        script.join_team(t)

    def team_leave(self, script):
        if self.locked_teams:
            return 'Teams are locked.'

        script.leave_team()

    def team_invite_only(self, script):
        if self.locked_teams:
            return 'Teams are locked.'

        if script.team is None:
            return 'You are not in a team'

        if script != script.team.leader:
            return 'You are not the team leader'

        return script.team.set_invite_only(not script.team.invite_only)

    def team_invite(self, script, player):
        if self.locked_teams:
            return 'Teams are locked.'

        if script.team is None:
            t = self.team_create(script, script.connection.name)
            if script.team is None:
                return t

        if script != script.team.leader:
            return 'You are not the team leader'

        message = '%s has been invited.' % player.name
        playerscript = self.playerscripts[player.entity_id]
        playerscript.invite_team(script.team)
        return message

    def team_leader(self, script, player):
        if self.locked_teams:
            return 'Teams are locked.'

        if script.team is None:
            return 'You are not in a team'

        if script != script.team.leader:
            return 'You are not the team leader'

        targetscript = self.playerscripts[player.entity_id]
        if targetscript in script.team.members:
            script.team.set_leader(targetscript)

    def team_kick(self, script, player):
        if self.locked_teams:
            return 'Teams are locked.'

        if script.team is None:
            return

        if script != script.team.leader:
            return

        targetscript = self.playerscripts[player.entity_id]
        if targetscript in script.team.members:
            targetscript.kick_team()

    def team_auto_balance(self, script):
        self.auto_balance = not self.auto_balance
        message = 'on' if self.auto_balance else 'off'
        print('Teams auto balance is now %s' % message)
        return 'Teams auto balance is now %s' % message

    def team_lock(self, script):
        self.locked_teams = not self.locked_teams
        message = 'locked' if self.locked_teams else 'unlocked'
        print('Teams are now %s' % message)
        return 'Teams are now %s' % message

    def team_chat(self, script, message):
        if script.team is None:
            return
        name = '%s: ' % script.connection.name
        script.team.send_chat(name + message, None, script)

    def team_info(self, script, team=None):
        if team is None:
            team = script.team
        else:
            team = self.get_team(team)

        if team is None:
            return 'Team not found'

        message = 'Team "%s": ' % team.name
        member_names = []
        for m in team.members:
            name = m.connection.name
            if m == team.leader:
                name += ' (Leader)'
            member_names.append(name)
        message += ', '.join(member_names)
        return message

    def team_exclude(self, script):
        script.excluded = not script.excluded
        message = 'excluded from' if script.excluded else 'included in'
        if script.excluded:
            script.leave_team()
            self.auto_rebalance_teams()
        else:
            self.auto_balance_player(script)

        return 'You are now %s teams.' % message

    def team_balance(self, script):
        self.balance_teams()
        return 'Teams balanced.'

    def team_shuffle(self, script):
        self.shuffle_teams()
        return 'Teams shuffled.'

    def team_move(self, script, player, name):
        t = self.get_team(name)
        if t is None:
            return 'There is no team named "%s"' % name

        playerscript = self.playerscripts[player.entity_id]

        if t == playerscript.team:
            msg = '%s is already in "%s"' % (playerscript.connection.name,
                                             name)
            return msg

        msg = 'Moving %s into team "%s"' % (playerscript.connection.name, name)
        playerscript.join_team(t, True)
        return msg


def get_class():
    return TeamServer


# Toggles team exclusion on for admins (allowing them to be not in a team)
# when teams are balanced or shuffled
@command
@admin
def team_exclude(script):
    """Exclude yourself from team balance and team shuffling."""
    return script.parent.team_exclude(script)


# Balance players across all existing teams
@command
@admin
def team_balance(script):
    """Balanced all players across all teams"""
    return script.parent.team_balance(script)


# Lock teams (makes players unable to leave\join teams)
@command
@admin
def team_auto_balance(script):
    """Toggle team automatic balance. Players will automatically join teams
    when they join the game. Teams will be balanced if players leave."""
    return script.parent.team_auto_balance(script)


# Balances and shuffles players across all existing teams
@command
@admin
def team_shuffle(script):
    """Shuffles all players across all teams"""
    return script.parent.team_shuffle(script)


# Move a player into a team
@command
@admin
def team_move(script, player_name, team_name):
    """Moves a player into a team"""
    player = script.get_player(player_name)
    return script.parent.team_move(script, player, team_name)


# Lock teams (makes players unable to leave\join teams)
@command
@admin
def team_lock(script):
    """Toggle team lock. Players cannot join/leave if teams are locked"""
    return script.parent.team_lock(script)


@command
def team_info(script, name=None):
    """Shows information of the team you are in or the one specified"""
    return script.parent.team_info(script, name)


@command
def team_list(script):
    """Shows a list of all teams"""
    return script.parent.team_list(script)


@command
def team_create(script, name):
    """Creates a team with desired name"""
    return script.parent.team_create(script, name)


@command
def team_invite_only(script):
    """Makes a team invite only. Must be team leader"""
    return script.parent.team_invite_only(script)


@command
def team_invite(script, name):
    """Invites a player to your team. Must be team leader"""
    player = script.get_player(name)
    return script.parent.team_invite(script, player)


@command
def team_kick(script, name):
    """Kick a player from your team. Must be team leader"""
    player = script.get_player(name)
    return script.parent.team_kick(script, player)


@command
def team_leader(script, name):
    """Appoint a new team leader. Must be team leader"""
    player = script.get_player(name)
    return script.parent.team_leader(script, player)


@command
def team_accept(script):
    """Accept the last team invite"""
    return script.parent.team_accept(script)


@command
def team_join(script, name):
    """Joins a open team, or one you have been invited to."""
    return script.parent.team_join(script, name)


@command
def team_leave(script):
    """Leaves your current team."""
    return script.parent.team_leave(script)


@command
def team_chat(script, *args):
    """Send a chat message to your team. /t for short"""
    message = ' '.join(args)
    return script.parent.team_chat(script, message)


@command
def t(script, *args):
    """Send a chat message to your team."""
    message = ' '.join(args)
    return script.parent.team_chat(script, message)
