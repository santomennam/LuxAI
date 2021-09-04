import math, sys
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
            if cell.citytile and cell.citytile.team != game_state.id:
                cell.blocked = True
            else:
                cell.blocked = False
            cell.adjRes = 0
    for unit in opponent.units:
        game_state.map.get_cell_by_pos(unit.pos).blocked = True

    # we iterate over all our units and do something with them
    for unit in player.units:
        unit.cargo.amount = unit.cargo.wood + unit.cargo.coal + unit.cargo.uranium
        if unit.is_worker() and unit.can_act():
            if unit.get_cargo_space_left() > 0:
                target = targetResource(unit, resource_tiles, player, actions)
                if not target.equals(unit.pos):
                    move(unit, target, actions)
                elif not game_state.map.get_cell_by_pos(unit.pos).citytile:
                    game_state.map.get_cell_by_pos(unit.pos).blocked = True
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                move(unit, targetCity(unit, player), actions)

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions


def targetResource(unit, resourceTiles, player, actions):
    tileOptions = []
    # lists all tiles adjacent to resources
    for resource in resourceTiles:
        if (resource.resource.type == Constants.RESOURCE_TYPES.WOOD or
                (resource.resource.type == Constants.RESOURCE_TYPES.COAL and player.researched_coal()) or
                (resource.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.researched_uranium())):
            for dir in DIR_LIST:
                if (resource.pos.translate(dir, 1).x > 0 and resource.pos.translate(dir, 1).x < game_state.map.width and
                        resource.pos.translate(dir, 1).y > 0 and resource.pos.translate(dir,
                                                                                        1).y < game_state.map.height):
                    tileOptions.append(game_state.map.get_cell_by_pos(resource.pos.translate(dir, 1)))
                    game_state.map.get_cell_by_pos(resource.pos.translate(dir, 1)).adjRes += 1

    target = None
    for tile in tileOptions:
        # calculates amount of fuel used by the trip
        # need to change once roads implemented
        nightTurns = (unit.pos.distance_to(tile.pos) * (2 if unit.is_worker() else 3) + (game_state.turn % 40)) - 30
        nightTurns = nightTurns if nightTurns > 0 else 0
        fuelUse = nightTurns * (4 if unit.is_worker() else 10)

        # can we survive the trip?
        if (fuelUse == 0 or fuelUse < unit.cargo.amount) and tile.blocked != True:
            if target == None or (tile.adjRes > target.adjRes or
                                  (tile.adjRes == target.adjRes and unit.pos.distance_to(
                                      tile.pos) < unit.pos.distance_to(target.pos))):
                target = tile

    if target == None:
        eprint("no target in range")
        return targetCity(unit, player)
    else:
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


def tileFromPos(unit):
    return game_state.map.get_cell_by_pos(unit.pos)


def findPath(unit, dest, actions, doAnnotate):
    eprint("My location: ", unit.pos)
    eprint("Destination: ", dest)

    path = []
    recursivePath(tileFromPos(unit), dest, path)
    if doAnnotate:
        actions.append(annotate.circle(dest.x, dest.y))
        for tiles in path:
            actions.append(annotate.x(tiles.x, tiles.y))
    return path

def move(unit,dest,actions):
    path = findPath(unit,dest,actions,True)
    if len(path):
        actions.append(unit.move(unit.pos.direction_to(path[0])))