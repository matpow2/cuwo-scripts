"""
Random loot generation script by Sarcen
This is a library
generate_item should be imported by scripts wanting to generate items
"""

from cuwo.entity import ItemData, ItemUpgrade
import random

REWARD_CLASS_WEAPONS = \
    dict({
         # warrior
         1: dict({
                 (3, 0): (1, ),  # 1h swords only iron
                 (3, 1): (1, ),  # axes only iron
                 (3, 2): (1, ),  # maces only iron

                 (3, 13): (1, ),  # shields, only iron

                 (3, 15): (1, ),  # 2h, only iron
                 (3, 16): (1, ),  # 2h, only iron
                 (3, 17): (1, 2),  # 2h mace, iron and wood
                 }),
         # ranger
         2: dict({
                 (3, 6): (2, ),  # bows, only wood
                 (3, 7): (2, ),  # crossbows, only wood
                 (3, 8): (2, ),  # boomerangs, only wood
                 }),
         # mage
         3: dict({
                 (3, 10): (2, ),  # wands, only wood
                 (3, 11): (2, ),  # staffs, only wood
                 # bracelets, silver, gold
                 (3, 12): (11, 12),
                 }),
         # rogue
         4: dict({
                 (3, 3): (1, ),  # daggers only iron
                 (3, 4): (1, ),  # fists only iron
                 (3, 5): (1, ),  # longswords only iron
                 })
         })


REWARD_CLASS_ARMOR = \
    dict({
         1: dict({
                 (4, 0): (1, ),
                 (5, 0): (1, ),
                 (6, 0): (1, ),
                 (7, 0): (1, ),

                 (8, 0): (11, 12),  # rings, gold and silver
                 (9, 0): (11, 12),  # amulets, gold and silver
                 }),

         2: dict({
                 (4, 0): (26, ),
                 (5, 0): (26, ),
                 (6, 0): (26, ),
                 (7, 0): (26, ),

                 (8, 0): (11, 12),  # rings, gold and silver
                 (9, 0): (11, 12),  # amulets, gold and silver
                 }),

         3: dict({
                 (4, 0): (25, ),
                 (5, 0): (25, ),
                 (6, 0): (25, ),
                 (7, 0): (25, ),

                 (8, 0): (11, 12),  # rings, gold and silver
                 (9, 0): (11, 12),  # amulets, gold and silver
                 }),

         4: dict({
                 (4, 0): (27, ),
                 (5, 0): (27, ),
                 (6, 0): (27, ),
                 (7, 0): (27, ),

                 (8, 0): (11, 12),  # rings, gold and silver
                 (9, 0): (11, 12),  # amulets, gold and silver
                 }),
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


def random_item(itemdict):
    items = list(itemdict.keys())
    item_key = items[random.randint(0, len(items) - 1)]
    item = create_item_data()
    item.type = item_key[0]
    item.sub_type = item_key[1]
    materials = itemdict[item_key]
    item.material = materials[random.randint(0, len(materials) - 1)]
    return item


def generate_item(level=1, entity=None):
    item_bias = random.randint(0, 100)

    if item_bias < 30:
        if entity is not None:
            class_id = entity.class_type
        else:
            class_id = random.randint(1, 4)

        item = random_item(REWARD_CLASS_WEAPONS[class_id])
    elif item_bias < 60:
        if entity is not None:
            class_id = entity.class_type
        else:
            class_id = random.randint(1, 4)

        item = random_item(REWARD_CLASS_ARMOR[class_id])
    elif item_bias < 95:
        item = random_item(REWARD_MISC)
    else:
        item = random_item(REWARD_PET_ITEMS)

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
    elif entity is not None:
        item.level = entity.level
    else:
        item.level = level

    return item
