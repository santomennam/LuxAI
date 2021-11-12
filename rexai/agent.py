import os
from typing import Any
import json
import base64
import math, sys
import numpy as np
from lux import game
from lux.game import Game
from lux.game_map import Cell, Position, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
from lux.game_objects import Player, Unit, City, CityTile

import display

# menu item: Code/inspect code

totalUnitsBuilt = 0
totalCitiesBuilt = 0
DIRECTIONS = Constants.DIRECTIONS
DIR_LIST = [DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST]
fuelThreshold = 200  # the amount of fuel a city must have to be considered not in danger


# return a list of the four Tile objects around pos
def getSurroundingTiles(pos, dist):
    surroundingTiles = []
    for direct in DIR_LIST:
        if pos.translate(direct, dist).x < game_state.map.width and pos.translate(direct,
                                                                                  dist).y < game_state.map.height:
            surroundingTiles.append(game_state.map.get_cell_by_pos(pos.translate(direct, dist)))
    return surroundingTiles


# #And for decoding this does the work (encStr is the encoded JSON string, loaded from somewhere):
#
# # get the encoded json dump
# enc = json.loads(encStr)
#

def readLastLineFromFile(filename):
    with open(filename, 'r') as f:
        last_line = f.readlines()[-1]
    return last_line


def decodeJSON(dump):
    enc = json.loads(dump)
    # dataType = np.dtype(enc[0])
    # eprint("dump",enc)
    # dataArray = list(enc[1][0])
    # eprint(enc[1][0])
    # eprint("data:",dataArray)
    return np.array(enc)


def parseInstructions(filename):
    line = readLastLineFromFile(filename)
    # eprint("last line:",line)
    dataArray = decodeJSON(line)
    # eprint("dataArray:",dataArray)
    return dataArray


def reportScore(score, filename):
    toWrite = json.dumps(score) + '\n'
    with open(filename, 'a') as f:
        f.write(toWrite)


class Score:

    def __init__(self, unit, instructionsList):  # should be a list of four lists, lengths 5,6,5,5
        # eprint("initializing")
        # res = dict(zip(test_keys, test_values))
        self.decisionParameters: dict = {"time": turnsUntilNight(),
                                         "cities": len(game_state.players[game_state.id].cities.values()),
                                         "workers": numWorkers(), "carts": numCarts(), "cityResTileReq": 1,
                                         "citiesInNeed": numCitiesInNeed(),
                                         "numResearch": game_state.players[game_state.id].research_points}
        self.c = self.decisionParameters["cities"]
        self.cN = self.decisionParameters["citiesInNeed"]
        self.w = self.decisionParameters["workers"]
        self.t = self.decisionParameters["time"]
        self.r = numResTiles(getSurroundingTiles(unit.pos, 1))
        self.rCargo = unit.get_cargo_space_left()

        self.inputLists = instructionsList
        self.inputLists = self.inputLists.reshape(4,6)
        # eprint("reshaped inputLists:",self.inputLists)
        # if len(self.inputLists) != 4:
        #     raise ValueError("expected 4 arguments, got", len(self.inputLists))

    # worker calculation master
    def calculateWorkerScores(self, unit, dest):
        # eprint("inputLists:", self.inputLists)
        return {self.calculateWorkerReturnScore(unit, self.inputLists[0]): "ret",
                self.calculateWorkerBuildScore(unit, self.inputLists[1]): "build",
                self.calculateWorkerStayScore(unit, self.inputLists[2]): "stay",
                self.calculateWorkerMoveToResScore(unit, dest, self.inputLists[3]): "moveToResource"}

    # compute individual worker scores
    def calculateWorkerReturnScore(self, unit, a):
        # a = [1,-0.1,-.5,-.1,0.5]
        a = a[:-1]
        b = [1, self.c, self.r, self.w, self.t]
        # eprint("return:", np.inner(a, b))
        return np.inner(a, b)

    def calculateWorkerBuildScore(self, unit, passed):
        # passed = [1, -0.1, -.5, -.1, 0.5, 0]
        a = passed[:-1]
        b = [1, self.c, self.r, self.w, self.t * self.cN >= passed[-1]]
        # eprint("build:", np.inner(a, b))
        return np.inner(a, b)

    def calculateWorkerStayScore(self, unit, a):
        b = [self.r, self.t, self.rCargo, self.c, self.cN]
        # a = [0.1, 0.1, 0.05, -0.1, -0.5]
        a = a[:-1]
        if self.rCargo != 0:
            # eprint("stay:", np.inner(a, b))
            return np.inner(a, b)
        else:
            return 0

    def calculateWorkerMoveToResScore(self, unit, dest, passed):
        # passed = [0.1,-.5,.2,0,0]
        a = passed[:-3]
        b = [self.t, numResTiles(getSurroundingTiles(dest, 1)), self.rCargo]
        if self.rCargo != 0:
            # eprint("move to resource:", np.inner(a, b))
            return np.inner(a, b) * (self.cN <= 0 or unit.cargo == 0)
        else:
            return 0

    # cart calculation master
    def calculateCartScores(self, unit, dest):
        return {"return": self.calculateCartReturnScore(unit),
                "stay": self.calculateCartStayScore(unit),
                "moveToWorkers": self.calculateCartMoveScore(unit, dest)}

    # compute individual cart scores
    def calculateCartReturnScore(self, unit):
        if self.rCargo != 0:
            wInSurround = len(getSurroundingUnits(unit.pos))
            return (0.5 * (self.c + 1) - wInSurround * 0.1) * (
                    + 0.1 * self.t + 0.5 * self.rCargo - 0.1 * self.c - 0.5 * self.cN)
        else:
            return 10

    def calculateCartMoveScore(self, unit, dest):
        wInSurround = len(getSurroundingUnits(dest.pos))
        score = (0.5 * (wInSurround) * (self.cN + 0.05 * (self.cR) + 0.1 * self.t))
        return score

    def calculateCartStayScore(self, unit):
        wInSurround = len(getSurroundingUnits(unit.pos))
        return 0.1 * self.c * (wInSurround * 0.1 + 0.1 * self.t + 0.5 * self.rCargo - 0.1 * self.c - 0.5 * self.cN)


def numCitiesInNeed():
    global fuelThreshold
    cities = game_state.players[game_state.id].cities.values()
    needy = 0
    for city in cities:
        if city.fuel < fuelThreshold:
            needy += 1
    return needy


def allCells():
    width, height = game_state.map.width, game_state.map.height
    for y in range(height):
        for x in range(width):
            yield game_state.map.get_cell(x, y)


def getCell(unitOrPos):
    if isinstance(unitOrPos, Unit):
        return game_state.map.get_cell_by_pos(unitOrPos.pos)
    if isinstance(unitOrPos, Position):
        return game_state.map.get_cell_by_pos(unitOrPos)
    raise TypeError("getCell expects a Unit or Position")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def agent(observation, configuration, doGraphics):
    global game_state
    # eprint("dir:",os.listdir())
    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    actions = []

    instructionData = parseInstructions("instructions.txt")


    ### AI Code goes down here! ###
    if doGraphics:
        display.draw_map_underlay(observation, game_state)

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height


    score = didIWin() * 100 + len(player.cities.keys()) * 50 + len(
        player.units) * 10 - (numUnitsLost() * 8) - numCitiesLost() * 45
    reportScore(score, "scores.txt")

    # eprint(" === TURN ", game_state.turn, " ===")
    # updateParameters()
    workersOnCooldown = 0
    # categorizes tiles
    resource_tiles = initCells()

    for unit in opponent.units:
        getCell(unit).blocked = True

    # we iterate over all our units and do something with them
    for unit in player.units:
        getCell(unit).blocked = not getCell(unit).citytile

    for unit in player.units:
        unitActions(player, unit, actions, resource_tiles,instructionData)
    for city in opponent.cities.values():
        for tile in city.citytiles:
            getCell(tile.pos).blocked = True


    # eprint(workersOnCooldown, " workers on cooldown")

    for city in player.cities.values():
        cityActions(city, actions)

    if doGraphics:
        display.draw_map_overlay(observation, game_state, actions.copy())
    # eprint("returning!")
    return actions


def didIWin():
    if len(game_state.players[game_state.id].cities.keys()) != len(
            game_state.players[(game_state.id + 1) % 2].cities.keys()):
        return len(game_state.players[game_state.id].cities.keys()) > len(
            game_state.players[(game_state.id + 1) % 2].cities.keys())
    elif len(game_state.players[game_state.id].units) != len(game_state.players[(game_state.id + 1) % 2].units):
        return len(game_state.players[game_state.id].units) > len(game_state.players[(game_state.id + 1) % 2].units)
    else:
        return 0.5


def numUnitsLost():
    global totalUnitsBuilt
    return totalUnitsBuilt + 1 - len(game_state.players[game_state.id].units)


def numCitiesLost():
    global totalCitiesBuilt
    return totalCitiesBuilt + 1 - len(game_state.players[game_state.id].cities.keys())


def initCells():
    resource_tiles: list[Cell] = []
    for cell in allCells():
        if cell.has_resource():
            resource_tiles.append(cell)
            if cell.resource.type == "wood":
                cell.resource.mineRate = 20
                # fuel per unit of resource
                cell.resource.fuelVal = 1
            elif cell.resource.type == "coal":
                cell.resource.mineRate = 5
                cell.resource.fuelVal = 10
            elif cell.resource.type == "uranium":
                cell.resource.mineRate = 2
                cell.resource.fuelVal = 40
        cell.blocked = cell.citytile and cell.citytile.team != game_state.id
        cell.adjRes = []
        cell.visited = False
    return resource_tiles


def simulateTurns(adjResTiles, unitCargoSpace):
    tileCopy = adjResTiles.copy()
    turn = 0
    depletedTiles = 0
    while True:
        if unitCargoSpace <= 0 or depletedTiles == len(adjResTiles):
            return turn
        turn += 1
        for tile in tileCopy:
            unitCargoSpace -= tile.resource.mineRate
            tile.resource.amount -= tile.resource.mineRate
            if tile.resource.amount <= 0:
                depletedTiles += 1
                tileCopy.remove(tile)


def nextToCity(unit):
    objMap = map(lambda t: t.citytile is not None and t.citytile.team == game_state.players[game_state.id],
                 getSurroundingTiles(unit.pos, 1))
    # eprint("expression:", list(objMap))
    # eprint("any:", any(objMap))
    return any(list(objMap))


def turnsUntilNight():
    return max(30 - game_state.turn % 40, 0)


def nightRemaining():
    return min(39 - (game_state.turn % 40), 10)


def numResTiles(tiles):
    num = 0
    for tile in tiles:
        if tile.resource:
            num += 1
    return num


def unassignedTilesInCity(city):
    unassigned = 0
    for tile in city.citytiles:
        if tile.assignedUnit is None:
            unassigned += 1
    return unassigned


def mostUnassigned():
    cities = game_state.players[game_state.id].cities.values()
    if len(cities):
        cities.sort(key=lambda a: unassignedTilesInCity(a), reversed=True)
        return cities[0]
    return None


def assignUnits():
    for unit in game_state.players[game_state.id].units:
        if unit.assignedCity is None:
            if mostUnassigned():
                unit.assignedCity = mostUnassigned()


# decide whether to build a new city tile (and if so, do so)
def cityPlanner(unit, actions):
    global totalCitiesBuilt
    # is it possible to build a city here?
    possible = unit.can_build(game_state.map) and not getCell(unit).citytile
    desired = (nextToCity(unit) or numResTiles(getSurroundingTiles(unit.pos, 1)) >= 1) and turnsUntilNight() > 0
    if possible and desired:
        actions.append(unit.build_city())
        # eprint("built city!")
        totalCitiesBuilt += 1
        return True
    # eprint("failed to build city")
    return False


def targetResource(unit, resourceTiles, player, actions):
    tileOptions = []
    for y in range(game_state.map_height):
        for x in range(game_state.map_width):
            tile = game_state.map.get_cell(x, y)
            for dir in DIR_LIST:
                if (tile.pos.translate(dir, 1).x in range(0, game_state.map_width) and
                        tile.pos.translate(dir, 1).y in range(0, game_state.map_height)):
                    # makes a list of all tiles next to resources
                    adjTile = getCell(tile.pos.translate(dir, 1))
                    if (adjTile.has_resource() and (adjTile.resource.type == "wood" or
                                                    (adjTile.resource.type == "coal" and player.researched_coal()) or
                                                    (
                                                            adjTile.resource.type == "uranium" and player.researched_uranium()))):
                        # each of those tiles has a list of resources next to it
                        tile.adjRes.append(adjTile)
                        if tile not in tileOptions:
                            tileOptions.append(tile)
    target = None
    for tile in tileOptions:
        woodGain = 0
        coalGain = 0
        uraniumGain = 0
        turnOptions = []
        # gets the amount of resources per turn and number of turns spent at each tile
        for adjTile in tile.adjRes:
            if adjTile.resource.type == "wood":
                woodGain += adjTile.resource.mineRate
                turnOptions.append(
                    min(adjTile.resource.amount, unit.get_cargo_space_left()) / adjTile.resource.mineRate)
            elif adjTile.resource.type == "coal":
                coalGain += adjTile.resource.mineRate
                turnOptions.append(
                    min(adjTile.resource.amount, unit.get_cargo_space_left() / adjTile.resource.mineRate))
            elif adjTile.resource.type == "uranium":
                uraniumGain += adjTile.resource.mineRate
                turnOptions.append(
                    min(adjTile.resource.amount, unit.get_cargo_space_left() / adjTile.resource.mineRate))

        turnsAtDest = simulateTurns(tile.adjRes, unit.get_cargo_space_left())  # simulating the turns seems simpler

        # total resources after the turns spent at dest
        totalWood = unit.cargo.wood + (min(woodGain, (100 - unit.cargo.wood)) * turnsAtDest)
        totalCoal = unit.cargo.coal + (min(coalGain, (100 - unit.cargo.coal)) * turnsAtDest)
        totalUranium = unit.cargo.uranium + (min(uraniumGain, (100 - unit.cargo.uranium)) * turnsAtDest)

        # total length of trip     -- has to change once roads implemented   | ************************** |
        rndTripLength = (unit.pos.distance_to(tile.pos) * 2 + turnsAtDest) * (2 if unit.is_worker() else 3)
        # turns of that trip during the night
        nightTurns2 = (rndTripLength + (game_state.turn % 40)) - 30
        nightTurns = min(max(rndTripLength - turnsUntilNight(), 0), nightRemaining())
        nightTurns2 = nightTurns2 if nightTurns2 > 0 else 0
        # if nightTurns != nightTurns2:
        #     eprint("not equivalent on turn ",game_state.turn%40,"with trip length ",rndTripLength,". nighturns: ",nightTurns," nightTurns2: ",nightTurns2)
        # else:
        #     eprint("equal on turn ",game_state.turn%40,"with trip length ",rndTripLength)

        # amount of fuel needed to last that many night turns
        fuelBurned = nightTurns * (4 if unit.is_worker() else 10)

        # of the resources we will have, which ones will be burned
        woodUsed = fuelBurned if (fuelBurned < totalWood) else totalWood
        if (math.ceil((fuelBurned - woodUsed) / 10) < totalCoal):
            coalUsed = math.ceil((fuelBurned - woodUsed) / 10)
        else:
            coalUsed = totalCoal
        if (math.ceil((fuelBurned - (woodUsed + coalUsed)) / 40) < totalUranium):
            uraniumUsed = math.ceil((fuelBurned - (woodUsed + coalUsed)) / 40)
        else:
            uraniumUsed = totalUranium

        fuelGain = (woodGain * turnsAtDest) + (coalGain * turnsAtDest) * 10 + (uraniumGain * turnsAtDest) * 40
        fuelLost = woodUsed + coalUsed * 10 + uraniumUsed
        # calculates potential fuel (after city conversion) per turn
        fuelPerTurn = (fuelGain - fuelLost) / (max(rndTripLength, 1))

        # the tile that nets the highest fuel per turn becomes the target
        if (target == None or (fuelPerTurn > target.fuelPerTurn)):
            if not tile.blocked:
                target = tile
                target.fuelPerTurn = fuelPerTurn

    if target == None:
        # eprint("no target in range")
        return targetCity(unit, player, 1, actions)
    else:
        # actions.append(annotate.sidetext("option: " + str(tile.pos.x) + ", " + str(tile.pos.y)))
        # actions.append(annotate.sidetext("rndTripLength = " + str(rndTripLength)))
        # actions.append(annotate.sidetext("fuelGain = " + str(fuelGain)))
        # actions.append(annotate.sidetext("fuelLost = " + str(fuelLost)))
        # actions.append(annotate.sidetext("fuelPerTurn = " + str(fuelPerTurn)))
        return target.pos


def targetCity(unit, player, order, actions):
    if len(player.cities.values()) > 0:
        closest_dist = math.inf
        closest_city_tiles = []
        for k, city in player.cities.items():
            for tile in city.citytiles:
                closest_city_tiles.append(tile)
        if len(closest_city_tiles):
            closest_city_tiles.sort(key=lambda y: unit.pos.distance_to(y.pos))
            order = max(min(order - 1, len(closest_city_tiles) - 1), 0)
            # eprint("city at ", closest_city_tiles[order].pos.x, ", ", closest_city_tiles[order].pos.y)
            return closest_city_tiles[order].pos
    else:
        # eprint("No city!! looking for element #", order - 1)
        return unit.pos


def recursivePath(tile, dest, path):
    if tile.blocked or tile.visited:
        return False
    tile.visited = True
    surrounding = getSurroundingTiles(tile.pos, 1)
    if game_state.map.get_cell_by_pos(dest) in surrounding:
        path.append(dest)
        return True
    surrounding.sort(key=lambda a: a.pos.distance_to(dest))
    for cell in surrounding:
        if recursivePath(cell, dest, path):
            path.append(cell.pos)
            return True
    return False


def numWorkers():
    num = 0
    for unit in game_state.players[game_state.id].units:
        if unit.is_worker():
            num += 1
    return num


def numCarts():
    num = 0
    for unit in game_state.players[game_state.id].units:
        if unit.is_cart():
            num += 1
    return num


def unitActions(player, unit, actions, resource_tiles,instructions):
    if not unit.can_act():
        return False
    if unit.is_cart():
        return cartLogic(unit, actions)
    return workerLogic(player, unit, actions, resource_tiles,instructions)


def cityActions(city, actions):
    global totalUnitsBuilt
    for citytile in city.citytiles:
        if citytile.cooldown < 1:
            if len(game_state.players[game_state.id].units) % 4 == 0:
                if buildCart(citytile, actions):
                    # eprint("built a cart!")
                    continue
                    totalUnitsBuilt += 1
            elif buildWorker(citytile, actions):
                # eprint("built a worker!")
                totalUnitsBuilt += 1
                continue
            elif not game_state.players[game_state.id].researched_uranium():
                actions.append(citytile.research())
                # eprint('research!:', game_state.players[game_state.id].research_points)


def cartDestFinder(cart):
    bestTile = None
    bestNum = 0
    for array in game_state.map.map:
        for tile in array:
            if len(getSurroundingUnits(tile.pos)) > bestNum and not tile.blocked:
                bestTile = tile
                bestNum = len(getSurroundingUnits(tile.pos))
    return bestTile.pos


def getSurroundingUnits(pos):
    units = []
    tiles = getSurroundingTiles(pos, 1)
    for unit in game_state.players[game_state.id].units:
        if game_state.map.get_cell_by_pos(unit.pos) in tiles:
            units.append(unit)
    return units


def inCity(pos):
    for city in game_state.players[game_state.id].cities.values():
        for tile in city.citytiles:
            if pos == tile.pos:
                return True
    return False


goingHomeSet = set()
cartDestDict = {}


def cartLogic(cart, actions):
    global goingHomeSet
    global cartDestDict
    if (cart.get_cargo_space_left() == 0):
        goingHomeSet.add(cart.id)
        cartDestDict.pop[cart.id]
    if inCity(cart.pos) and cart.id in goingHomeSet:
        goingHomeSet.remove(cart.id)
    if cart.id in goingHomeSet:
        if move(cart, targetCity(cart, game_state.players[game_state.id], 1, actions), actions):
            return
    if not cart.id not in cartDestDict.keys() or len(getSurroundingUnits(cart.pos)) == 0:
        cartDestDict[cart.id] = cartDestFinder(cart.pos)
        if cart.id in cartDestDict.keys():
            move(cart, cartDestDict[cart.id], actions)
        else:
            cartDestDict[cart.id] = targetCity(cart, game_state.players[game_state.id], 1, actions)
            goingHomeSet.add(cart.id)
    if cart.id in cartDestDict.keys() and cart.pos == cartDestDict[cart.id] and (
            turnsUntilNight() > 3 or (cart.get_cargo_space_left()) > 1990):
        for unit in getSurroundingUnits(cart.pos):
            if unit.is_worker() and unit.can_act():
                resourceAmounts = {}
                resourceAmounts["wood"]: unit.cargo.wood
                resourceAmounts["coal"]: unit.cargo.coal
                resourceAmounts["uranium"]: unit.cargo.uranium
                if len(resourceAmounts):
                    max_res = max(resourceAmounts, key=resourceAmounts.get)
                    if max(resourceAmounts.values()) > 20:  # dont bother transferring if don't have enough
                        actions.append(unit.transfer(cart.id, max_res, max(resourceAmounts.values()) - 5))
        return
    if cart.id in cartDestDict.keys() and cart.pos != cartDestDict[cart.id]:
        move(cart, cartDestDict[cart.id], actions)


# TODO: Go save a dying city?

def workerReturn(unit, targetDest, actions):
    if targetCity(unit, game_state.players[game_state.id], 1, actions):
        if move(unit, targetCity(unit, game_state.players[game_state.id], 1, actions), actions):
            return True
    elif targetCity(unit, game_state.players[game_state.id], 2, actions):
        if move(unit, targetCity(unit, game_state.players[game_state.id], 2, actions), actions):
            return True
    return False


def workerStay(unit, targetDest, actions):
    return True


def moveToTarget(unit, targetDest, actions):
    return move(unit, targetDest, actions)


def workerBuild(unit, targetDest, actions):
    return cityPlanner(unit, actions)


def workerLogic(player, unit, actions, resource_tiles,instructions):
    # unit.cargo.total = unit.cargo.wood + unit.cargo.coal + unit.cargo.uranium
    functToOptions = {"ret": workerReturn, "stay": workerStay, "moveToResource": moveToTarget, "build": workerBuild}
    score = Score(unit,instructions)
    targetDest = targetResource(unit, resource_tiles, player, actions)
    options = score.calculateWorkerScores(unit, targetDest)
    choice = options[max(options.keys())]

    for i in options.keys():
        if functToOptions[choice](unit, targetDest, actions):
            return True
        else:
            i = 0
            choice = options[max(options.keys())]
    return False


def cityTileFuelUse(tile):
    surrounding = getSurroundingTiles(tile.pos, 1)
    surroundingCities = 0
    for city in surrounding:
        if city.citytile is not None and city.citytile.id == game_state.id:
            surroundingCities += 1
    return 23 - (5 * surroundingCities)


def totalCityFuelUse(city):
    totalFuel = 0
    for tile in city.citytiles:
        totalFuel += cityTileFuelUse(tile)
    return totalFuel


def buildWorker(citytile, actions):
    if citytile.can_act and unitCount() < totalCityTiles():
        actions.append(citytile.build_worker())
        return True
    return False


def buildCart(citytile, actions):
    if citytile.can_act and unitCount() < totalCityTiles():
        actions.append(citytile.build_cart())
        return True
    return False


def unitCount():
    return len(game_state.players[game_state.id].units)


def totalCityTiles():
    totalTiles = 0
    for cities in game_state.players[game_state.id].cities.values():
        totalTiles += len(cities.citytiles)
    return totalTiles


def findPath(unit, dest, actions, doAnnotate):
    # eprint("My location: ", unit.pos)
    # eprint("Destination: ", dest)

    path = []
    recursivePath(getCell(unit), dest, path)
    if doAnnotate:
        actions.append(annotate.circle(dest.x, dest.y))
        for tiles in path:
            actions.append(annotate.x(tiles.x, tiles.y))
    return path


def move(unit, dest, actions):
    if dest is None:
        eprint("WHAT! DEST IS NONE! Unit ID = ", unit.id)
    # if game_state.map.get_cell_by_pos(dest).blocked:
    # eprint("we seem to think that", dest.x, dest.y, "is blocked")
    else:
        path = findPath(unit, dest, actions, True)
        if len(path) > 0:
            # eprint("path has length when", unit.id, "tried to move to ", dest.x, dest.y)
            actions.append(unit.move(unit.pos.direction_to(path[0])))
            return True
    # eprint("navigation failed while ", unit.id, " tried to move to", dest.x, dest.y, ". unit was at ", unit.pos.x,
    #        unit.pos.y)
    return False
