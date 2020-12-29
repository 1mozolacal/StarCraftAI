import heapq
import time

import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.data import Alert
from sc2.player import Bot, Computer


class WorkerRushBot(sc2.BotAI):
    async def on_step(self, iteration: int):
        if iteration == 0:
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])


class basicTerranBot(sc2.BotAI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_heap = []

    def push_on_memory_heap(action, delay):
        self.memory_heap = heappush(
            self.memory_heap, ((time.time + delay), action))

    async def on_step(self, iteration):
        if self.supply_left < 4 and not self.already_pending(sc2.constants.p)

    async def build_supply_depo(self):
        pass

    async def build_barrack(self):
        pass

    async def building_addon(self):
        if self.alert(Alert.BuildingComplete):
            print("Building was built need to decide on addon")


run_game(maps.get("Abyssal Reef LE"), [
    Bot(Race.Zerg, WorkerRushBot()),
    Computer(Race.Protoss, Difficulty.Medium)
], realtime=False)
