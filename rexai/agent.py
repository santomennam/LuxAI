import math, sys
from lux import game
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
import display

DIRECTIONS = Constants.DIRECTIONS
DIR_LIST = [DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST]


def getSurroundingTiles(pos, dist):
    surroundingTiles = []
    for direct in DIR_LIST:
        if pos.translate(direct, dist).x < game_state.map.width and pos.translate(direct,
                                                                                  dist).y < game_state.map.height:
            surroundingTiles.append(game_state.map.get_cell_by_pos(pos.translate(direct, dist)))
    return surroundingTiles


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

registeredCartIDs=[]
def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    actions = []


    ### AI Code goes down here! ###
    display.draw_map_underlay(observation, game_state)

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    eprint(" === TURN ", game_state.turn, " ===")

    # categorizes tiles
    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
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
            if cell.citytile and cell.citytile.team != game_state.id:
                cell.blocked = True
            else:
                cell.blocked = False
            cell.adjRes = []
            cell.visited = False
    for unit in opponent.units:
        game_state.map.get_cell_by_pos(unit.pos).blocked = True

    # we iterate over all our units and do something with them
    for unit in player.units:
        if not game_state.map.get_cell_by_pos(unit.pos).citytile:
            game_state.map.get_cell_by_pos(unit.pos).blocked = True
    for unit in player.units:
        if unit.is_cart():
            if unit.id not in registeredCartIDs:
                registerCart(unit)
                registeredCartIDs.append(unit.id)
            if unit.can_act():
                cartLogic(unit,actions)
        unit.cargo.total = unit.cargo.wood + unit.cargo.coal + unit.cargo.uranium
        if unit.is_worker() and unit.can_act():
            if unit.get_cargo_space_left() > 0:
                target = targetResource(unit, resource_tiles, player, actions)
                if not target.equals(unit.pos):
                    move(unit, target, actions)
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                eprint("cargo full")
                if (cityPlanner(unit, actions)):
                    continue
                else:
                    if targetCity(unit, player):
                        move(unit, targetCity(unit, player), actions)
                        continue
                    else:
                        for tile in getSurroundingTiles(unit.pos,1):
                            if not tile.resource and not tile.blocked:
                                move(unit,tile,actions)
                                continue
                        eprint(unit.id," is blocked!")

    for city in player.cities.values():
        cityActions(city, actions)

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    display.draw_map_overlay(observation, game_state, actions.copy())

    return actions

def registerCart(cart):
    cart.goingHome = False
    cart.dest = None

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
    eprint("expression:", list(
        map(lambda t: t.citytile is not None and t.citytile.team == game_state.players[game_state.id],
            getSurroundingTiles(unit.pos, 1))))
    eprint("any:", any(
        map(lambda t: t.citytile is not None and t.citytile.team == game_state.players[game_state.id],
            getSurroundingTiles(unit.pos, 1)))
           )
    return any(
        list(map(lambda t: t.citytile is not None and t.citytile.team == game_state.players[game_state.id],
                 getSurroundingTiles(unit.pos, 1))))


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


def cityPlanner(unit, actions):
    eprint("unit pos:", unit.pos.x, unit.pos.y, "can act: ", unit.can_act(), "nextToCity:", nextToCity(unit),
           "numResTiles:", numResTiles(getSurroundingTiles(unit.pos, 1)), "cargo space:", unit.get_cargo_space_left())
    if unit.can_act() and (nextToCity(unit) or numResTiles(
            getSurroundingTiles(unit.pos, 1)) >= 1) and unit.get_cargo_space_left() == 0:
        eprint("Trying to build city")
        unitTile = game_state.map.get_cell_by_pos(unit.pos)
        eprint("can_build:", unit.can_build(game_state.map))
        if not unitTile.has_resource() and not unitTile.citytile and turnsUntilNight() > 0 and unit.can_build(
                game_state.map):
            actions.append(unit.build_city())
            eprint("built city!")
            return True
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
                    adjTile = tileFromPos(tile.pos.translate(dir, 1))
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
        fuelPerTurn = (fuelGain - fuelLost) / rndTripLength

        # the tile that nets the highest fuel per turn becomes the target
        if (target == None or (fuelPerTurn > target.fuelPerTurn)):
            if not tile.blocked:
                target = tile
                target.fuelPerTurn = fuelPerTurn

    if target == None:
        eprint("no target in range")
        return targetCity(unit, player)
    else:
        # actions.append(annotate.sidetext("option: " + str(tile.pos.x) + ", " + str(tile.pos.y)))
        # actions.append(annotate.sidetext("rndTripLength = " + str(rndTripLength)))
        # actions.append(annotate.sidetext("fuelGain = " + str(fuelGain)))
        # actions.append(annotate.sidetext("fuelLost = " + str(fuelLost)))
        # actions.append(annotate.sidetext("fuelPerTurn = " + str(fuelPerTurn)))
        return target.pos


def targetCity(unit, player):
    if len(player.cities.values()) > 0:
        closest_dist = math.inf
        closest_city_tile = None
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                dist = city_tile.pos.distance_to(unit.pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
        if closest_city_tile != None:
            eprint("city at ", closest_city_tile.pos.x, ", ", closest_city_tile.pos.y)
            return closest_city_tile.pos
    else:
        eprint("No city!!")
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
            num +=1
    return num
def numCarts():
    num = 0
    for unit in game_state.players[game_state.id].units:
        if unit.is_cart():
            num += 1
    return num

def cityActions(city, actions):
    for citytile in city.citytiles:
        if citytile.cooldown < 1:
            if len(game_state.players[game_state.id].units)%4 == 0:
                if buildCart(citytile, actions):
                    eprint("built a cart!")
                    continue
            elif buildWorker(citytile, actions):
                eprint("built a worker!")
                continue
            elif not game_state.players[game_state.id].researched_uranium():
                actions.append(citytile.research())
                eprint('research!:', game_state.players[game_state.id].research_points)

def cartDestFinder(cart):
    bestTile = None
    bestNum = 0
    for tile in game_state.map.map.values():
        if len(getSurroundingUnits(tile.pos)) > bestNum and not tile.blocked:
            bestTile = tile
            bestNum = getSurroundingUnits(tile.pos)
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

def cartLogic(cart, actions):
    if (cart.get_cargo_space_left() == 0):
        cart.goingHome = True
    if inCity(cart.pos):
        cart.goingHome = False
    if cart.goingHome:
        move(cart, targetCity(cart, game_state.players[game_state.id]), actions)
        return
    if not cart.dest or len(getSurroundingUnits(cart.pos)) == 0:
        cart.dest = cartDestFinder(cart.pos)
        if cart.dest is not None:
            move(cart, cart.dest, actions)
        else:
            cart.dest = targetCity(cart, game_state.players[game_state.id])
            cart.goingHome = True
    if cart.pos == cart.dest and (turnsUntilNight() > 3 or cart.cargo < 10):
        for unit in getSurroundingUnits(cart.pos):
            if unit.is_worker() and unit.can_act():
                resourceAmounts = {}
                resourceAmounts["wood"]: unit.cargo.wood
                resourceAmounts["coal"]: unit.cargo.coal
                resourceAmounts["uranium"]: unit.cargo.uranium
                max_res = max(resourceAmounts, key=resourceAmounts.get)
                if max(resourceAmounts.values()) > 20:  # dont bother transferring if don't have enough
                    actions.append(unit.transfer(cart.id, max_res, max(resourceAmounts.values()) - 5))
        return
    if cart.pos != cart.dest:
        move(cart, cart.dest, actions)


def tileFromPos(pos):
    return game_state.map.get_cell_by_pos(pos)


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
    eprint("My location: ", unit.pos)
    eprint("Destination: ", dest)

    path = []
    recursivePath(tileFromPos(unit.pos), dest, path)
    if doAnnotate:
        actions.append(annotate.circle(dest.x, dest.y))
        for tiles in path:
            actions.append(annotate.x(tiles.x, tiles.y))
    return path


def move(unit, dest, actions):
    if dest is None:
       eprint("WHAT! DEST IS NONE! Unit ID = ",unit.id)
    if(not game_state.map.get_cell_by_pos(dest).blocked):
        path = findPath(unit, dest, actions, True)
    if len(path):
        actions.append(unit.move(unit.pos.direction_to(path[0])))
