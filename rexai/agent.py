import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

DIRECTIONS = Constants.DIRECTIONS
DIR_LIST = [DIRECTIONS.NORTH, DIRECTIONS.EAST, DIRECTIONS.SOUTH, DIRECTIONS.WEST]
game_state = None

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

    #categorizes tiles
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
                    findPath(unit, target, actions)
                elif not game_state.map.get_cell_by_pos(unit.pos).citytile:
                    game_state.map.get_cell_by_pos(unit.pos).blocked = True
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                findPath(unit, targetCity(unit, player), actions)

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
                resource.pos.translate(dir, 1).y > 0 and resource.pos.translate(dir, 1).y < game_state.map.height):

                    tileOptions.append(game_state.map.get_cell_by_pos(resource.pos.translate(dir, 1)))
                    game_state.map.get_cell_by_pos(resource.pos.translate(dir, 1)).adjRes += 1

    target = None
    for tile in tileOptions:
        # calculates amount of fuel used by the trip
        # need to change once roads implemented
        nightTurns = (unit.pos.distance_to(tile.pos) * (2 if unit.is_worker() else 3) + (game_state.turn % 40)) - 30
        nightTurns = nightTurns if nightTurns > 0 else 0
        fuelUse = nightTurns * (4 if unit.is_worker() else 10)

        if (fuelUse == 0 or fuelUse < unit.cargo.amount) and tile.blocked != True:
            if target == None or (tile.adjRes > target.adjRes or 
            (tile.adjRes == target.adjRes and unit.pos.distance_to(tile.pos) < unit.pos.distance_to(target.pos))):
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

def findPath(unit, dest, actions):
    eprint("My location: ", unit.pos)
    eprint("Destination: ", dest)
    actions.append(annotate.circle(dest.x, dest.y))

    path = [unit.pos]
    step = 1
    stepBack = 0
    while not path[step - 1].equals(dest):
        distEast = dest.x - path[step - 1].x
        distSouth = dest.y - path[step - 1].y
        path.append(None)
        # takes the shortest path to the destination
        if distEast != 0 and (abs(distEast) >= abs(distSouth) or (stepBack > 0 and abs(distEast) < abs(distSouth))):
            path[step] = path[step - 1].translate(DIRECTIONS.EAST, int(distEast / abs(distEast)))
        else:
            path[step] = path[step - 1].translate(DIRECTIONS.SOUTH, int(distSouth / abs(distSouth)))
        actions.append(annotate.x(path[step].x, path[step].y))

        # unless cells along the path are or will be blocked
        cellBlocked = game_state.map.get_cell_by_pos(path[step]).blocked
        if cellBlocked == True or cellBlocked == step:
             eprint("path stepBack: pos (", path[step].x, ", ", path[step].y, ") blocked = ", cellBlocked)
             step = step - stepBack
             stepBack = stepBack + 1
        else:
            game_state.map.get_cell_by_pos(path[step]).blocked = step
            step = step + 1
    if step > 1:
        actions.append(unit.move(unit.pos.direction_to(path[1])))