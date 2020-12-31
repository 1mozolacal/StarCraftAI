import heapq
import time
import random

import sc2
from sc2.bot_ai import BotAI
from sc2.player import Bot, Computer
from sc2.ids.unit_typeid import UnitTypeId


class basicTerranBot(sc2.BotAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_heap = []
        self.last_scout_time = time.time()
        self.enemy_raiding_party = []  # tuple of time,location,armyvalue
        self.no_add_on_building = []
        self.iteration = 0
        self.last_attack = 0
        self.last_defend = 0

    def push_on_memory_heap(action, delay):
        self.memory_heap = heappush(
            self.memory_heap, ((time.time + delay), action))

    async def on_step(self, iteration):
        self.iteration = iteration
        await self.macro()
        # await self.marine_raid()
        await self.attack()
        await self.defend()
        await self.scout()

    async def macro(self):
        await self.distribute_workers()
        await self.build_workers()
        await self.expand()
        await self.build_on_gas()
        await self.build_structures()
        await self.research_upgrades()
        await self.train_units()

    async def build_structures(self):
        await self.build_supply_depo()
        await self.build_factory()
        await self.build_barrack()
        await self.build_add_ons()

    async def train_units(self):
        await self.train_tanks()
        await self.train_marines()
        await self.train_tech()

    async def research_upgrades(self):
        await self.build_research_buildings()
        await self.research()

    async def build_research_buildings(self):
        if self.structures.filter(lambda struc: struc.type_id == UnitTypeId.ENGINEERINGBAY).amount < 1 \
                and self.structures.filter(lambda struc: struc.type_id == UnitTypeId.BARRACKS).amount > 2:
            await self.build_building(UnitTypeId.ENGINEERINGBAY)
        if self.structures.filter(lambda struc: struc.type_id == UnitTypeId.ARMORY).amount < 1 \
                and self.structures.filter(lambda struc: struc.type_id == UnitTypeId.FACTORY).amount > 2:
            await self.build_building(UnitTypeId.ARMORY)
        # if self.structures.filter(lambda stru: struc.type_id == UnitTypeId.BARRACKS and struc)

    async def research(self):
        engi_upgrades = [
            sc2.AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1,
            sc2.AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1,
        ]
        for engi in self.structures.filter(lambda struc: struc.type_id == UnitTypeId.ENGINEERINGBAY):
            ava_abil = await self.get_available_abilities(engi)
            for abil in engi_upgrades:
                if abil in ava_abil and engi.is_ready and engi.is_idle and self.can_afford(abil):
                    self.do(engi(abil))
                    break

    async def offensive(self):
        await self.marine_raid()

    async def build_supply_depo(self):
        early_game_supply = bool(
            self.supply_left < 4 and not self.already_pending(UnitTypeId.SUPPLYDEPOT))
        late_game_supply = bool(
            self.supply_cap > 90 and (
                self.supply_left < 6 and not self.already_pending(
                    UnitTypeId.SUPPLYDEPOT)
                or self.supply_left < 2 and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 2
            ))
        if (self.can_afford(UnitTypeId.SUPPLYDEPOT)
                and (early_game_supply or late_game_supply)):
            # pick a location
            place_location = await self.get_base_building_location(
                UnitTypeId.SUPPLYDEPOT)
            if place_location is None:
                return
            # pick a worker near that location
            selected_worker = self.get_nearby_builder(place_location)
            if selected_worker is None:
                return
            # issue the build command
            if not self.can_afford(UnitTypeId.SUPPLYDEPOT):
                return
            selected_worker.build(UnitTypeId.SUPPLYDEPOT, place_location)

    async def build_on_gas(self):
        if (self.structures.filter(lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER).amount > 1) or (self.units.filter(lambda unit: unit.type_id == UnitTypeId.SCV).amount > 15):
            comand_centers = self.structures.filter(
                lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER and structure.is_ready)
            if not comand_centers:
                return
            gasses = self.vespene_geyser.filter(
                lambda geyser: any([geyser.position.distance_to(cc) < 10 for cc in comand_centers]))
            scvs = self.units.filter(
                lambda unit: unit.type_id == UnitTypeId.SCV)
            for gas in gasses:
                near_scv = [
                    x for x in scvs if gas.position.distance_to(x) < 15]
                if len(near_scv) < 5:
                    return
                if not self.can_afford(UnitTypeId.REFINERY):
                    return
                builder = self.get_nearby_builder(gas.position)
                if builder is None:
                    return
                builder.build(UnitTypeId.REFINERY, gas)

    async def build_workers(self):
        for command_center in self.structures.filter(lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER and structure.is_ready and structure.is_idle):
            if not self.can_afford(UnitTypeId.SCV):
                return
            if self.supply_workers > 80:
                return
            command_center.train(UnitTypeId.SCV)

    async def build_barrack(self):
        rack_amount = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.BARRACKS).amount
        command_amount = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER).amount
        if (rack_amount < 2 * command_amount) or (self.minerals > 1000):
            location = await self.get_base_building_location(UnitTypeId.BARRACKS)
            if location is None:
                return
            builder = self.get_nearby_builder(location)
            if builder is None:
                return
            builder.build(UnitTypeId.BARRACKS, location)

    async def build_factory(self):
        rack_amount = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.BARRACKS).amount
        if rack_amount < 1:
            return
        factory_amount = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.FACTORY).amount
        command_amount = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER).amount
        if factory_amount < 2 * command_amount or (self.minerals > 1000 and self.vespene > 600):
            await self.build_building(UnitTypeId.FACTORY, True)

    async def build_add_ons(self):
        for factory in self.structures.filter(lambda unit: unit.type_id == UnitTypeId.FACTORY and not unit.has_add_on):
            if(self.can_afford(UnitTypeId.TECHLAB) and factory.is_ready):
                # factory.build(UnitTypeId.TECHLAB)
                self.do(factory(sc2.AbilityId.BUILD_TECHLAB_FACTORY))

    async def build_building(self, structure, add_on_room=False):
        if not self.can_afford(structure):
            return
        location = await self.get_base_building_location(structure, add_on_room)
        if location is None:
            return
        builder = self.get_nearby_builder(location)
        if builder is None:
            return
        builder.build(structure, location)

    def get_nearby_builder(self, location):
        build_ready_workers = self.workers.filter(
            lambda worker: worker.is_collecting or worker.is_idle)
        if len(build_ready_workers) < 0:
            return None
        selected_worker = build_ready_workers.closest_to(location)
        return selected_worker

    async def get_base_building_location(self, building, add_on_room=False):

        cc = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER)
        if not cc:
            return
        random_command_center = cc.random
        location = await self.find_placement(building, near=random_command_center.position, max_distance=45, placement_step=3, addon_place=add_on_room)
        for retry in range(20):
            if location is None or not (location.distance_to_closest(self.mineral_field) < 5
                                        and location.distance_to_closest(self.structures.filter(lambda struc: struc.type_id == UnitTypeId.COMMANDCENTER)) < 5
                                        ):
                break
            # await self.chat_send(f"Re pick location {location} retry-{retry}")
            random_command_center = cc.random
            location = await self.find_placement(building, near=random_command_center.position, placement_step=3, max_distance=45 + 2 * retry, addon_place=add_on_room)
        return location

    async def get_generic_foward_buildling_position(self):
        rough_location = self.start_location.towards(
            self.game_info.map_center, distance=10)
        place_location = await self.find_placement(UnitTypeId.SUPPLYDEPOT, near=rough_location, placement_step=1)
        return place_location  # can be none

    async def train_marines(self):
        for rack in self.structures.filter(lambda structure: structure.type_id == UnitTypeId.BARRACKS and structure.is_ready and structure.is_idle):
            if not self.can_afford(UnitTypeId.MARINE):
                return
            rack.train(UnitTypeId.MARINE)

    async def train_tanks(self):
        for factory in self.structures.filter(lambda stru: stru.type_id == UnitTypeId.FACTORY and stru.has_add_on):
            if factory.is_idle and factory.is_ready:
                factory.train(UnitTypeId.SIEGETANK)

    async def train_tech(self):
        pass

    async def expand(self):
        scv_amount = self.units.filter(
            lambda unit: unit.type_id == UnitTypeId.SCV).amount
        command_amount = self.structures.filter(
            lambda structure: structure.type_id == UnitTypeId.COMMANDCENTER).amount
        if scv_amount < command_amount * 12:
            return  # we don't want to expand too few workers
        await self.expand_now()

    def target_attack(self):
        if self.enemy_units:
            attack_location = self.enemy_units.random.position
        elif self.enemy_structures:
            attack_location = self.enemy_structures.random.position
        else:
            attack_location = self.enemy_start_locations[0]
        return attack_location

    async def marine_raid(self):
        marines = self.units.filter(
            lambda unit: unit.type_id == UnitTypeId.MARINE and unit.is_idle)
        if marines.amount < 12:
            return
        attack_location = self.target_attack()
        for marine in marines:
            self.do(marine.attack(attack_location))

    async def attack(self):
        military_units = self.units.filter(
            lambda unit: unit.type_id != UnitTypeId.SCV)
        if self.supply_army > self.supply_cap * 0.3 and self.iteration - self.last_attack > 100:
            self.last_attack = self.iteration
            attack_location = self.target_attack()
            for unit in military_units:
                unit.attack(attack_location)

    async def defend(self):
        ccs = self.structures.filter(
            lambda struc: struc.type_id == UnitTypeId.COMMANDCENTER)
        for enemy in self.enemy_units:
            distances = [enemy.position.distance_to(cc) for cc in ccs]
            if distances and min(distances) < 20 and self.iteration - self.last_defend < 50:
                self.last_defend = self.iteration
                attack_location = enemy.position
                military_units = self.units.filter(
                    lambda unit: unit.type_id != UnitTypeId.SCV)
                for unit in military_units:
                    unit.attack(attack_location)

    async def scout(self):
        if time.time() - self.last_scout_time > 25:
            self.last_scout_time = time.time()
            marines = self.units.filter(
                lambda unit: unit.type_id == UnitTypeId.MARINE and unit.is_idle)
            if not marines:
                return
            location = self.expansion_locations_list[random.randrange(
                len(self.expansion_locations_list))]
            scouter = marines.closest_to(location)
            scouter.attack(location)

    async def on_enemy_unit_entered_vision(self, unit):
        # await self.chat_send(f"I see your {unit.type_id}")
        pass

    async def building_addon(self):
        if self.alert(Alert.BuildingComplete):
            print("Building was built need to decide on addon")


sc2.run_game(
    sc2.maps.get("AcropolisLE"),
    [Bot(sc2.Race.Terran, basicTerranBot()),
     Computer(sc2.Race.Terran, sc2.Difficulty.Hard)
     ],
    realtime=False,
)
# Computer(sc2.Race.Terran, sc2.Difficulty.Medium)
# Human(sc2.Race.Terran)
