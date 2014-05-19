
""" King of the hill script by Sarcen """

from cuwo.script import ServerScript, ConnectionScript, command, admin
from cuwo.entity import (ItemData, ItemUpgrade, NAME_BIT,
                         AppearanceData, EntityData)
from cuwo.packet import (KillAction, MissionData, EntityUpdate)
from cuwo.vector import Vector3
from cuwo.constants import CHUNK_SCALE, SECTOR_SCALE, FULL_MASK
from cuwo.common import set_bit

entity_packet = EntityUpdate()

import time
import math
import random

KOTH_DATA = 'kingofthehill_settings'

REWARD_WEAPONS = dict({
    # Weapons
    (3, 0): (1, ),   # 1h swords only iron
    (3, 1): (1, ),   # axes only iron
    (3, 2): (1, ),   # maces only iron
    (3, 3): (1, ),   # daggers only iron
    (3, 4): (1, ),   # fists only iron
    (3, 5): (1, ),   # longswords only iron
    (3, 6): (2, ),   # bows, only wood
    (3, 7): (2, ),   # crossbows, only wood
    (3, 8): (2, ),   # boomerangs, only wood

    (3, 10): (2, ),  # wands, only wood
    (3, 11): (2, ),     # staffs, only wood
    (3, 12): (11, 12),   # bracelets, silver, gold

    (3, 13): (1, ),    # shields, only iron

    (3, 15): (1, ),    # 2h, only iron
    (3, 16): (1, ),    # 2h, only iron
    (3, 17): (1, 2),   # 2h mace, iron and wood
})

REWARD_ARMOR = dict({
    # Equipment
    # chest warrior (iron), mage (silk), ranger(linen), rogue(cotton)
    (4, 0): (1, 25, 26, 27),
    # gloves warrior (iron), mage (silk), ranger(linen), rogue(cotton)
    (5, 0): (1, 25, 26, 27),
    # boots warrior (iron), mage (silk), ranger(linen), rogue(cotton)
    (6, 0): (1, 25, 26, 27),
    # shoulder warrior (iron), mage (silk), ranger(linen), rogue(cotton)
    (7, 0): (1, 25, 26, 27),
    (8, 0): (11, 12),  # rings, gold and silver
    (9, 0): (11, 12),  # amulets, gold and silver
})

REWARD_MISC = dict({
    (11, 14): (128, 129, 130, 131),
})

REWARD_PET_ITEMS = dict({})

REWARD_PETS = (19, 22, 23, 25, 26, 27, 30, 33, 34, 35, 36, 37, 38, 39, 40, 50,
               53, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 74, 75,
               86, 87, 88, 90, 91, 92, 93, 98, 99, 102, 103, 104, 105, 106,
               151)


# generate pets and petfood in the reward item list based on reward pets
def generate_pets():
    for pet in REWARD_PETS:
        REWARD_PET_ITEMS[(19, pet)] = (0, )
        REWARD_PET_ITEMS[(20, pet)] = (0, )


generate_pets()


def create_item_data():
    item_data = ItemData()
    item_data.type = 0
    item_data.sub_type = 0
    item_data.modifier = 0
    item_data.minus_modifier = 0
    item_data.rarity = 0
    item_data.material = 0
    item_data.flags = 0
    item_data.level = 0
    item_data.items = []
    for _ in range(32):
        new_item = ItemUpgrade()
        new_item.x = 0
        new_item.y = 0
        new_item.z = 0
        new_item.material = 0
        new_item.level = 0
        item_data.items.append(new_item)
    item_data.upgrade_count = 0
    return item_data


def create_appearance_data():
    appearance = AppearanceData()
    appearance.not_used_1 = 0
    appearance.not_used_2 = 0
    appearance.hair_red = 0
    appearance.hair_green = 0
    appearance.hair_blue = 0
    appearance.movement_flags = 0
    appearance.entity_flags = 0
    appearance.scale = 1.0
    appearance.bounding_radius = 1.0
    appearance.bounding_height = 1.0
    appearance.head_model = -32767
    appearance.hair_model = -32767
    appearance.hand_model = -32767
    appearance.foot_model = -32767
    appearance.body_model = -32767
    appearance.back_model = -32767
    appearance.shoulder_model = -32767
    appearance.wing_model = -32767
    appearance.head_scale = 1.0
    appearance.body_scale = 1.0
    appearance.hand_scale = 1.0
    appearance.foot_scale = 1.0
    appearance.shoulder_scale = 1.0
    appearance.weapon_scale = 1.0
    appearance.back_scale = 1.0
    appearance.unknown = 1.0
    appearance.wing_scale = 1.0
    appearance.body_pitch = 0
    appearance.arm_pitch = 0
    appearance.arm_roll = 0
    appearance.arm_yaw = 0
    appearance.feet_pitch = 0
    appearance.wing_pitch = 0
    appearance.back_pitch = 0
    appearance.body_offset = Vector3()
    appearance.head_offset = Vector3()
    appearance.hand_offset = Vector3()
    appearance.foot_offset = Vector3()
    appearance.back_offset = Vector3()
    appearance.wing_offset = Vector3()
    return appearance


def create_entity_data():
    entity = EntityData()
    entity.mask = FULL_MASK
    entity.pos = Vector3(0, 0, 0)
    entity.body_roll = 0
    entity.body_pitch = 0
    entity.body_yaw = 0
    entity.velocity = Vector3()
    entity.accel = Vector3()
    entity.extra_vel = Vector3()
    entity.look_pitch = 0
    entity.physics_flags = 17
    entity.hostile_type = 0
    entity.entity_type = 0
    entity.current_mode = 0
    entity.mode_start_time = 0
    entity.hit_counter = 0
    entity.last_hit_time = 0
    entity.appearance = create_appearance_data()
    entity.flags_1 = 64
    entity.flags_2 = 0
    entity.roll_time = 0
    entity.stun_time = -10000
    entity.slowed_time = 0
    entity.make_blue_time = 0
    entity.speed_up_time = 0
    entity.show_patch_time = 0
    entity.class_type = 0
    entity.specialization = 0
    entity.charged_mp = 0
    entity.not_used_1 = 0
    entity.not_used_2 = 0
    entity.not_used_3 = 0
    entity.not_used_4 = 0
    entity.not_used_5 = 0
    entity.not_used_6 = 0
    entity.ray_hit = Vector3()
    entity.hp = 100
    entity.mp = 0
    entity.block_power = 0
    entity.max_hp_multiplier = 100
    entity.shoot_speed = 1
    entity.damage_multiplier = 1
    entity.armor_multiplier = 1
    entity.resi_multiplier = 1
    entity.not_used7 = 0
    entity.not_used8 = 0
    entity.level = 1
    entity.current_xp = 0
    entity.parent_owner = 0
    entity.unknown_or_not_used1 = 1
    entity.unknown_or_not_used2 = 0
    entity.power_base = 0
    entity.unknown_or_not_used4 = 4294967295
    entity.unknown_or_not_used5 = 4294967295
    entity.not_used11 = 4294967295
    entity.not_used12 = 0
    entity.super_weird = 0
    entity.spawn_pos = Vector3(0, 0, 0)
    entity.not_used19 = 0
    entity.not_used20 = 4294967295
    entity.not_used21 = 4294967295
    entity.not_used22 = 0
    entity.consumable = create_item_data()
    entity.equipment = []
    for _ in range(13):
        new_item = create_item_data()
        entity.equipment.append(new_item)
    entity.skills = []
    for _ in range(11):
        entity.skills.append(0)
    entity.mana_cubes = 0
    entity.name = ""
    return entity


class KotHConnection(ConnectionScript):
    reward_points = 0

    def on_join(self, event):
        if self.parent.event_entity is not None:
            entity_packet.set_entity(self.parent.event_entity,
                                     self.parent.event_entity_id,
                                     FULL_MASK)
            self.connection.send_packet(entity_packet)

        if self.parent.event_dummy is not None:
            entity_packet.set_entity(self.parent.event_dummy,
                                     self.parent.event_dummy_id,
                                     FULL_MASK)
            self.connection.send_packet(entity_packet)

        for id, entity in self.parent.event_radius_entities.items():
            if entity is not None:
                entity_packet.set_entity(entity, id)
                self.connection.send_packet(entity_packet)

    def on_kill(self, event):
        if self.parent.king is None:
            return

        if event.target == self.parent.king.entity_data:
            message = 'you killed {} for {}(+{}xp) KotH points! (+king bonus)'
            self.connection.send_chat((message
                                       .format(event.target.name,
                                               self.parent.kill_king_points,
                                               self.parent.kill_king_xp)))
            self.add_points(self.parent.kill_king_points)
            self.parent.give_xp(self.connection, self.parent.kill_king_xp)

        elif self.connection in self.parent.players_in_proximity:
            message = 'you killed {} for {}(+{}xp) KotH points!'
            self.connection.send_chat((message
                                       .format(event.target.name,
                                               self.parent.kill_points,
                                               self.parent.kill_xp)))
            self.add_points(self.parent.kill_points)
            self.parent.give_xp(self.connection, self.parent.kill_xp)

    def add_points(self, pts):
        new_points = self.reward_points + pts

        pct = [0.80, 0.60, 0.40, 0.20]
        maxpts = self.parent.reward_points

        for i in range(len(pct)):
            if (new_points >= pct[i] * maxpts and
                    self.reward_points < pct[i] * maxpts):
                self.show_koth_points()
                break

        self.reward_points = new_points

    def show_koth_points(self):
        maxpts = self.parent.reward_points
        pct = self.reward_points / maxpts * 100

        self.connection.send_chat(("KotH points {}/{} ({}%)"
                                  .format(int(self.reward_points),
                                          int(maxpts),
                                          int(pct))))

    def remove_points(self, pts):
        self.reward_points -= pts


class KotHServer(ServerScript):
    connection_class = KotHConnection
    proximity_radius = 1700000 ** 2
    tick_frequency = 5.0
    last_tick = 0
    item_drop_radius = 1000000
    reward_points = 10000
    copper_per_tick = 0
    xp_per_tick = 2
    king_xp_bonus = 10
    points_per_tick = 0
    king_points_per_tick = 0
    kill_points = 100
    kill_king_points = 500
    event_active = False
    event_location = None
    event_entity = None
    event_dummy = None
    event_radius_entities = {}
    event_mission = None
    players_in_proximity = []
    king = None
    king_start = 0
    king_rewards = 0
    king_next_reward = 0
    max_level = 0

    def on_load(self):
        self.load_config()

        try:
            self.max_level = self.server.config.anticheat.level_cap
        except KeyError:
            pass
        except AttributeError:
            pass

        config = self.server.config.kingofthehill
        self.king_xp_bonus = config.king_xp_bonus
        self.xp_per_tick = config.xp_per_tick
        self.copper_per_tick = config.copper_per_tick
        self.tick_frequency = config.tick_frequency

        self.kill_points = config.kill_points
        self.kill_king_points = config.kill_king_points

        self.kill_xp = config.kill_xp
        self.kill_king_xp = config.kill_king_xp

        self.points_per_tick = (self.reward_points /
                                (config.reward_frequency /
                                 self.tick_frequency))

        self.king_points_per_tick = (self.reward_points /
                                     (config.king_reward_frequency /
                                      self.tick_frequency))

    def load_config(self):
        self.saved_config = self.server.load_data(KOTH_DATA, {})

        if 'location_x' in self.saved_config:
            self.event_location = Vector3(self.saved_config['location_x'],
                                          self.saved_config['location_y'],
                                          self.saved_config['location_z'])
        if 'radius' in self.saved_config:
            self.proximity_radius = self.saved_config['radius']

        if self.event_location is not None:
            self.start(self.event_location)

    def save_config(self):
        if self.event_location is not None:
            self.saved_config['location_x'] = self.event_location.x
            self.saved_config['location_y'] = self.event_location.y
            self.saved_config['location_z'] = self.event_location.z
        self.saved_config['radius'] = self.proximity_radius

        self.server.save_data(KOTH_DATA, self.saved_config)

    def update(self, event=None):
        if not self.event_active:
            return

        if self.event_mission is not None:
            self.server.update_packet.missions.append(self.event_mission)

        if (time.time() - self.last_tick >
                self.tick_frequency):
            self.do_proximity_check()
            self.grant_xp_and_gold()
            self.last_tick = time.time()

    def do_proximity_check(self):
        server = self.server
        players = list(server.players.values())
        bad_items = []
        for player in self.players_in_proximity:
            if player not in players:
                bad_items.append(player)

        for player in bad_items:
            self.players_in_proximity.remove(player)

        for player in players:
            distance = (self.event_location -
                        player.position).magnitude_squared()

            if (distance < self.proximity_radius and
                    player.entity_data.hp > 0):
                if player not in self.players_in_proximity:
                    self.players_in_proximity.append(player)
            elif player in self.players_in_proximity:
                self.players_in_proximity.remove(player)

        if len(self.players_in_proximity) > 0:
            if (self.king is None or
                (self.king.entity_id
                    != self.players_in_proximity[0].entity_id)):
                self.king_start = time.time()
                self.king = self.players_in_proximity[0]
                self.event_entity.name = self.king.name
                self.event_entity.hp = 10000000000
                self.event_entity.mask = set_bit(self.event_entity.mask,
                                                 NAME_BIT, True)
                print("New king of the hill", self.king.name)
        elif self.king is not None:
            self.event_entity.name = "King ofthe Hill"
            self.event_entity.hp = 10000000000
            self.event_entity.mask = set_bit(self.event_entity.mask,
                                             NAME_BIT, True)
            self.king = None

    def find_player_script(self, player):
        for child in self.children:
            if child.connection == player:
                return child
        return None

    def grant_xp_and_gold(self):
        if len(self.players_in_proximity) == 0:
            return

        for player in self.players_in_proximity:
            xp = self.xp_per_tick
            player_script = player.scripts.kingofthehill
            if player.entity_id == self.king.entity_id:
                xp += self.king_xp_bonus
                player_script.add_points(self.king_points_per_tick)
            else:
                player_script.add_points(self.points_per_tick)

            self.give_xp(player, xp)

            if player_script.reward_points > self.reward_points:
                player_script.remove_points(self.reward_points)
                message = (("{name} has reached {points} points," +
                           " and receives an additional reward!")
                           .format(name=player.name,
                                   points=self.reward_points))

                print(message)
                self.server.send_chat(message)
                item = self.generate_item(player.entity_data)
                player.give_item(item)

        self.drop_gold(self.copper_per_tick)

    def drop_gold(self, amount):
        gold_coins = int(amount / 10000)
        amount -= gold_coins * 10000
        silver_coins = int(amount / 100)
        amount -= silver_coins * 100
        copper_coins = amount

        # signed short limit
        if gold_coins > 32767:
            gold_coins = 32767

        if gold_coins > 0:
            gold = create_item_data()
            gold.type = 12
            gold.material = 11
            gold.level = gold_coins
            self.drop_item(gold)

        if silver_coins > 0:
            silver = create_item_data()
            silver.type = 12
            silver.material = 12
            silver.level = silver_coins
            self.drop_item(silver)

        if copper_coins > 0:
            copper = create_item_data()
            copper.type = 12
            copper.material = 10
            copper.level = copper_coins
            self.drop_item(copper)

    def drop_item(self, item):
        position = self.event_location.copy()

        d = random.uniform(0, 1) * math.pi * 2
        r = math.sqrt(random.uniform(0, 1)) * self.item_drop_radius
        position.x += math.cos(d) * r
        position.y += math.sin(d) * r
        self.server.drop_item(item, position)

    def give_xp(self, player, amount):
        # don't give XP to max levels
        if self.max_level == 0 or player.entity_data.level < self.max_level:
            update_packet = self.server.update_packet
            action = KillAction()
            action.entity_id = player.entity_id
            action.target_id = self.event_dummy_id
            action.xp_gained = amount
            update_packet.kill_actions.append(action)

    def set_radius(self, topostion):
        if self.event_location is not None:
            dist = (self.event_location - topostion).magnitude_squared()
            self.proximity_radius = dist
            self.save_config()

            self.start(self.event_location)

    def start(self, location):
        print("King of the hill mode activated at " + str(location))
        self.event_location = location.copy()
        self.event_active = True

        entity = self.event_entity
        if entity is None:
            entity = create_entity_data()

            entity.hostile_type = 2
            entity.entity_type = 138

            entity.appearance.entity_flags = 1
            entity.appearance.scale = 3.0
            entity.appearance.bounding_radius = 3.0
            entity.appearance.bounding_height = 4.0
            entity.appearance.body_model = 2565
            entity.appearance.head_scale = 0.0
            entity.appearance.hand_scale = 0.0
            entity.appearance.body_offset = Vector3(0, 0, 25)

            entity.level = math.pow(2, 31) - 1
            entity.power_base = 0

            entity.name = "King ofthe Hill"

        entity.mask = 0x0000FFFFFFFFFFFF
        entity.pos = location.copy()
        entity.pos += Vector3(0, 0, 100000)
        entity.spawn_pos = entity.pos
        entity.hp = 10000000000

        self.event_entity_id = 1000
        self.event_entity = entity
        self.server.entities[self.event_entity_id] = entity

        # Create a dummy entity that is hostile, only way
        # HitPacket will grant xp
        dummy = self.event_dummy
        if dummy is None:
            dummy = create_entity_data()
            dummy.mask = FULL_MASK
            dummy.hostile_type = 1
            dummy.pos = Vector3(0, 0, 100000000) + entity.pos
            dummy.spawn_pos = entity.pos
            dummy.hp = 10000000000
            dummy.power_base = 1
            dummy.name = "KOTHDummy!"
            dummy.appearance.entity_flags = 1

            self.event_dummy = dummy
            self.event_dummy_id = 1001
            self.server.entities[self.event_dummy_id] = dummy

        # Create entities in a circle around the main pillar
        radius_ents = 10
        for i in range(radius_ents):
            radius_entity = None
            id = 1002 + i
            if id in self.event_radius_entities:
                radius_entity = self.event_radius_entities[id]

            if radius_entity is None:
                radius_entity = create_entity_data()

                radius_entity.mask = FULL_MASK
                radius_entity.hostile_type = 2
                radius_entity.entity_type = 136

                radius_entity.hp = 10000000000
                radius_entity.level = math.pow(2, 31) - 1
                radius_entity.power_base = 0
                radius_entity.spawn_pos = self.event_entity.pos

                radius_entity.appearance.scale = 1.0
                radius_entity.appearance.bounding_radius = 1.0
                radius_entity.appearance.bounding_height = 1.5
                radius_entity.appearance.body_offset = Vector3(0, 0, 0)
                radius_entity.appearance.entity_flags = 1
                radius_entity.appearance.body_model = 2475
                radius_entity.appearance.head_scale = 0.0
                radius_entity.appearance.hand_scale = 0.0

                radius_entity.name = "King ofthe Hill"

            r = math.pi * 2 / radius_ents * i
            x = math.sqrt(self.proximity_radius) * math.sin(r)
            y = math.sqrt(self.proximity_radius) * math.cos(r)
            radius_entity.pos = Vector3(x, y, 0) + self.event_entity.pos
            radius_entity.hp = 10000000000
            radius_entity.mask = 0x0000FFFFFFFFFFFF
            radius_entity.velocity = Vector3(0, 0, -100000)
            self.event_radius_entities[id] = radius_entity
            self.server.entities[id] = radius_entity

        self.create_mission_data()

        self.save_config()

    def create_mission_data(self):
        mission = MissionData()
        mission.section_x = int(self.event_entity.pos.x / SECTOR_SCALE)
        mission.section_y = int(self.event_entity.pos.y / SECTOR_SCALE)
        mission.something1 = 1
        mission.something2 = 1
        mission.something3 = 1
        mission.mission_id = 1
        mission.something5 = 1
        mission.monster_id = 1000  # How is this monster id when its an int32?
        mission.quest_level = 500
        mission.something8 = 1
        mission.state = 1
        mission.something10 = 100
        mission.something11 = 100
        mission.chunk_x = int(self.event_entity.pos.x / CHUNK_SCALE)
        mission.chunk_y = int(self.event_entity.pos.y / CHUNK_SCALE)
        self.event_mission = mission

    def random_item(self, itemdict):
        list = list(itemdict.keys())
        item_key = list[random.randint(0, len(list) - 1)]
        item = create_item_data()
        item.type = item_key[0]
        item.sub_type = item_key[1]
        materials = itemdict[item_key]
        item.material = materials[random.randint(0, len(materials) - 1)]
        return item

    def generate_item(self, entity_data):
        item_bias = random.randint(0, 100)

        if item_bias < 30:
            item = self.random_item(REWARD_WEAPONS)
        elif item_bias < 60:
            item = self.random_item(REWARD_ARMOR)
        elif item_bias < 95:
            item = self.random_item(REWARD_MISC)
        else:
            item = self.random_item(REWARD_PET_ITEMS)

        if item.type == 11:
            item.rarity = 2
        elif item.type == 20 or item.type == 19:
            item.rarity = 0
        else:
            item.rarity = random.randint(3, 4)

        if item.type == 19 or item.type == 11:
            item.modifier = 0
        else:
            item.modifier = random.randint(0, 16777216)

        if item.type == 20:
            item.level = 1
        else:
            item.level = entity_data.level

        return item

    def get_mode(self, event):
        return 'king of the hill'


def get_class():
    return KotHServer


@command
def koth_points(script):
    script.show_koth_points()


@command
@admin
def koth_set_radius(script):
    script.parent.set_radius(script.connection.position)


# koth_start, starts a king of the hill event at the location of the caller
@command
@admin
def koth_start(script):
    script.parent.start(script.connection.position)