"""
Team Deathmatch script by Sarcen

Features:
Two Teams
Killing Sprees
Multikills
Kill and Assist XP

It should not be used together with the PvP script, unless you want team
members to be able to kill each other.
"""

from cuwo.script import admin, command
from scripts.teams import TeamConnection, Team, TeamServer
from scripts.loot import generate_item
from scripts.announcer import Announcer
from cuwo.packet import PickupAction, ServerUpdate, KillAction
import math


def get_max_xp(level):
    xp = 1050 - 1000 / (0.05 * (level - 1) + 1)
    return int(xp)


class TDMConnection(TeamConnection):
    male_entities = (0, 2, 9, 11, 4, 7, 15, 13)

    multikill_time = 5.0
    multikill_names = ['doublekill',
                       'triplekill',
                       'multikill',
                       'ultrakill',
                       'monsterkill']

    spree_kill_count = 3
    spree_names = ['%s is on a killing spree!',
                   '%s is on a rampage!',
                   '%s is dominating!',
                   '%s is unstoppable!',
                   '%s is godlike!']

    def on_load(self):
        super().on_load()

        self.spree = 0
        self.last_kill = 0
        self.multikill = 0
        self.max_level = math.pow(2, 32)-1
        try:
            self.max_level = self.server.config.anticheat.level_cap
        except KeyError:
            pass
        except AttributeError:
            pass

    def give_kill_xp(self, player, is_assist=False):
        if self.connection.entity_data.level >= self.max_level:
            return
        xp_action = KillAction()
        xp_action.entity_id = self.connection.entity_id
        xp_action.target_id = player.connection.entity_id
        level = player.connection.entity_data.level
        xp_action.xp_gained = max(get_max_xp(level) * 0.03, 5)
        if is_assist:
            xp_action.xp_gained *= 0.5
        self.server.update_packet.kill_actions.append(xp_action)

    def on_player_kill(self, player):
        self.old_spree = self.spree
        self.spree += 1

        if self.loop.time() - self.last_kill > self.multikill_time:
            self.multikill = 0
        self.multikill += 1

        killer = self.connection
        killed = player.connection

        message = ''
        if self.team is not None:
            message += '[%s] ' % self.team.name
        message += '%s killed %s' % (killer.name, killed.name)

        if self.multikill > 1:
            kill_index = min(self.multikill-2, len(self.multikill_names)-1)
            message += ', %s! ' % self.multikill_names[kill_index]

        killed_spree = int(player.spree / self.spree_kill_count)
        player.spree = 0
        if killed_spree > 0:
            entity_type = player.connection.entity_data.entity_type
            his_her = 'his' if entity_type in self.male_entities else 'her'
            message += ', ending %s killing spree.' % his_her

        spree_index = min(int(self.spree / self.spree_kill_count),
                          len(self.spree_names))
        old_spree_index = int(self.old_spree / self.spree_kill_count)

        self.server.send_chat(message)

        if spree_index > old_spree_index:
            message = self.spree_names[spree_index-1] % killer.name
            self.server.send_chat(message)

        self.last_kill = self.loop.time()

        # give myself xp
        self.give_kill_xp(player)

        # give anyone that assisted me in killing assist xp
        for assist, t in player.assists.items():
            if assist is None:
                continue
            if assist == self:
                continue
            if self.loop.time() - t < self.tag_duration:
                assist.give_kill_xp(player, True)

        player.assists = {}


class TDMTeam(Team):
    def __init__(self, server, name):
        super(TDMTeam, self).__init__(server, name)

        self.reset_stats()

    def reset_stats(self):
        self.kills = 0
        self.deaths = 0

    def on_kill(self, killed, killer):
        self.kills += 1

        if self.kills >= self.server.max_score:
            self.server.declare_winner(self)

    def on_death(self, victim, killer=None):
        self.deaths += 1


class TDMServer(TeamServer):
    team_class = TDMTeam
    connection_class = TDMConnection
    allow_join_when_locked = True
    destroy_empty_teams = False
    locked_teams = True
    auto_balance = True

    round_delay = 20

    round_active = False
    suppress_damage = True

    max_score = 25
    announcer = None

    def get_mode(self, event):
        return 'Team Deathmatch'

    def on_load(self):
        super(TDMServer, self).on_load()

        self.create_team('Red')
        self.create_team('Blue')

        self.loop.call_later(5.0, self.start_round_delayed)

    def give_reward(self, team):
        for m in team.members:
            self.silent_give_item(m.connection,
                                  generate_item(0, m.connection.entity_data))

    # give items silently to players without broadcasting it to everyone
    def silent_give_item(self, connection, item):
        packet = ServerUpdate()
        packet.reset()
        action = PickupAction()
        action.entity_id = connection.entity_id
        action.item_data = item
        packet.pickups.append(action)
        connection.send_packet(packet)

    def declare_winner(self, team):
        if self.round_active:
            self.round_active = False
            self.suppress_damage = True
            message = 'Team "%s" has reached %s kills and won the round!'
            message = message % (team.name, self.max_score)
            print(message)
            self.server.send_chat(message)
            self.give_reward(team)

            self.loop.call_later(5.0, self.start_round_delayed)

    def set_max_score(self, score):
        self.max_score = score
        message = 'Team Deathmatch score max set to %s' % score
        self.server.send_chat(message)
        return message

    def get_scores(self):
        scores = []
        for name, t in self.teams.items():
            scores.append('%s %sK %sD' % (t.name, t.kills, t.deaths))

        return 'Score: ' + ' - '.join(scores)

    def start_round(self):
        for name, t in self.teams.items():
            t.reset_stats()

        self.auto_rebalance_teams()
        self.round_active = True
        self.suppress_damage = False
        message = 'Team Deathmatch! first team to %s kills wins.' % \
                  self.max_score
        print(message)
        self.server.send_chat(message)

    def start_round_delayed(self):
        self.announcer = Announcer()
        self.announcer.server = self.server
        self.announcer.irc_announcement = False
        self.announcer.action = 'Round starting'
        self.announcer.abort_message = 'round aborted.'
        self.announcer.message = "{time}"
        self.announcer.message_long = "Round starting in {time} seconds."
        self.announcer.time_left = self.round_delay
        self.announcer.reason = '1'
        self.announcer.action_func = self.start_round
        self.announcer.action_func_args = []
        self.announcer.announce()


def get_class():
    return TDMServer


@admin
@command
def tdm_set_max_score(script, score):
    """Set the kill count per round."""
    try:
        score = int(score)
    except Exception:
        return

    return script.parent.set_max_score(score)


@command
def tdm_score(script):
    """Show all teams and their K(ills) and D(eaths)."""
    return script.parent.get_scores()