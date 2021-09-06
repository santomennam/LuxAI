import math, sys
from lux import game
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

DIRECTIONS = Constants.DIRECTIONS
DIR_LIST = [DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST]
game_state = None


def getSurroundingTiles(pos, dist):
    surroundingTiles = []
    for direct in DIR_LIST:
        if pos.translate(direct, dist).x < game_state.map.width and pos.translate(direct, dist).y < game_state.map.height:
            surroundingTiles.append(game_state.map.get_cell_by_pos(pos.translate(direct, dist)))
    return surroundingTiles


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


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
    for unit in opponent.units:
        game_state.map.get_cell_by_pos(unit.pos).blocked = True

    # we iterate over all our units and do something with them
    for unit in player.units:
        unit.cargo.total = unit.cargo.wood + unit.cargo.coal + unit.cargo.uranium
        if unit.is_worker() and unit.can_act():
            if unit.get_cargo_space_left() > 0:
                target = targetResource(unit, resource_tiles, player, actions)
                if not target.equals(unit.pos):
                    move(unit, target, actions)
                elif not game_state.map.get_cell_by_pos(unit.pos).citytile:
                    game_state.map.get_cell_by_pos(unit.pos).blocked = True
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                eprint("cargo full")
                move(unit, targetCity(unit, player), actions)

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions


def targetResource(unit, resourceTiles, player, actions):

    ## STILL NOT ACCURATE, RETURNS VERY BAD TILES ##

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
                        (adjTile.resource.type == "uranium" and player.researched_uranium()))):
                        
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
                turnOptions.append(min(adjTile.resource.amount, (100 - unit.cargo.wood) / adjTile.resource.mineRate))
            elif adjTile.resource.type == "coal":
                coalGain += adjTile.resource.mineRate
                turnOptions.append(min(adjTile.resource.amount, (100 - unit.cargo.coal) / adjTile.resource.mineRate))
            elif adjTile.resource.type == "uranium":
                uraniumGain += adjTile.resource.mineRate
                turnOptions.append(min(adjTile.resource.amount, (100 - unit.cargo.uranium) / adjTile.resource.mineRate))
        
        turnsAtDest = min(turnOptions)

        # total resources after the turns spent at dest
        totalWood = unit.cargo.wood + (min(woodGain, (100 - unit.cargo.wood)) * turnsAtDest)
        totalCoal = unit.cargo.coal + (min(coalGain, (100 - unit.cargo.coal)) * turnsAtDest)
        totalUranium = unit.cargo.uranium + (min(uraniumGain, (100 - unit.cargo.uranium)) * turnsAtDest)

        # total length of trip     -- has to change once roads implemented   | ************************** |
        rndTripLength = (unit.pos.distance_to(tile.pos) * 2 + turnsAtDest) * (2 if unit.is_worker() else 3)
        # turns of that trip during the night
        nightTurns = (rndTripLength + (game_state.turn % 40)) - 30
        nightTurns = nightTurns if nightTurns > 0 else 0
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
    if len(player.cities) > 0:
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
            return unit.pos


def recursivePath(tile, dest, path):
    if tile.blocked:
        return False
    tile.blocked = True
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


def tileFromPos(pos):
    return game_state.map.get_cell_by_pos(pos)


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

def move(unit,dest,actions):
    path = findPath(unit,dest,actions,True)
    if len(path):
        actions.append(unit.move(unit.pos.direction_to(path[0])))