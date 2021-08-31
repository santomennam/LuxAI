import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
DIRECTIONS = Constants.DIRECTIONS
game_state = None

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def plotPath(destination,unit):
    path = []
    enemyCityTiles = []
    for city in game_state.players[0].cities.values():
        for tiles in city.citytiles:
            enemyCityTiles.append(tiles.pos)
    forbiddenTiles = [enemyCityTiles]

    eprint("destination: ",destination.x,destination.y)
    #resolve fringe cases:
    if destination == unit.pos:
        eprint("at destination")
        return path
    pos = path[-1]
    surroundingTiles = []
    
    #calculation
    optimalCell = None
    bestDist = sys.maxsize
    while destination != path[-1] and len(path) < 30:
        for direction in DIRECTIONS:
            if direction != DIRECTIONS.CENTER:
                surroundingTiles.append(pos.translate(direction, 1))
                
        for cell in surroundingTiles:
            if cell.pos == destination:
                eprint("adjacent to destination")
                path.append(cell.pos)
                return path
        for x in range(-1,1):
            for y in range(-1,1):
                pos = path[-1]
                if x == 0 ^ y == 0:
                    challengerCell = game_state.map.get_cell(pos.x + x, pos.y +y)
                else:
                    continue
                if challengerCell in forbiddenTiles:
                    continue

                if challengerCell.pos == destination:
                    path.append(destination)
                    eprint("challenger was dest. added to path.")
                    return path

                dist = challengerCell.pos.distance_to(destination)
                if dist < bestDist:
                    bestDist = dist
                    optimalCell = challengerCell
                    eprint("found better cell at", optimalCell.pos.x, optimalCell.pos.y)

        #if path.__contains__(optimalCell.pos):
            #eprint("path contains optimalCell already: ",optimalCell.pos.x, optimalCell.pos.y, ". My position is ",unit.pos.x,unit.pos.y,"My destination is ",destination.x,destination.y)
            #return path 
        path.append(optimalCell.pos)
    if len(path) >= 28: #prevent timeout
        path = [path[1]]
        eprint("timeout")
        return path
    eprint("Unit pos: ", unit.pos.x, unit.pos.y)
    for item in path:
        eprint(item.x, " ", item.y)
    return path

def calcCooldownToDest(destination,unit):
    cool = unit.cooldown
    if unit.is_worker():
        unitFactor = 2
    elif unit.is_cart():
        unitFactor = 3
    else:
        return -1 #tried to plot a cityTile path
    path = plotPath(destination,unit) #method does not exist yet, will return list of cells in path
    for cell in path:
       cool -= (cell.road - unitFactor)
    return cool

def move(unit, dest,actions):
    eprint("trying to move to dest: ",dest)
    surroundingTiles = []
    pos = unit.pos
    for x in range(-1, 1):
        for y in range(-1, 1):
            if x == 0 or y == 0:
                surroundingTiles.append(game_state.map.get_cell(pos.x + x, pos.y + y))
    for cell in surroundingTiles:
        if cell.pos == dest and cell.has_resource(): ## return if next to destination and dest is resource
            return
    path = plotPath(dest,unit)
    # if len(path) <= 1:
    #     eprint("path too short! path contains:")
    #     for item in path:
    #         eprint("(",item.x,item.y,")")
    #     return
    actions.append(unit.move(unit.pos.direction_to(path[0]))) #first object in path is our own position, so need to call to

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
    eprint("== TURN ", game_state.turn, " ==")
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)

    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            closest_dist = math.inf
            closest_resource_tile = None
            if unit.get_cargo_space_left() > 0:
                # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
                for resource_tile in resource_tiles:
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
                    dist = resource_tile.pos.distance_to(unit.pos)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_resource_tile = resource_tile
                if closest_resource_tile is not None:
                    eprint("closest resource tile is at ",closest_resource_tile.pos)
                    move(unit,closest_resource_tile.pos,actions)
                else:
                    eprint("NO CLOSEST RESOURCE TILE")
            else:
                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                ##should fetch time and time to harvest next resource and use it to calculate how much fuel required to survive the night - keep that if night is near
                if len(player.cities) > 0:
                    closest_dist = math.inf
                    closest_city_tile = None
                    for k, city in player.cities.items():
                        for city_tile in city.citytiles:
                            dist = city_tile.pos.distance_to(unit.pos)
                            if dist < closest_dist:
                                closest_dist = dist
                                closest_city_tile = city_tile
                    if closest_city_tile is not None:
                        eprint("trying to return to city.")
                        move(unit,closest_city_tile.pos,actions)
                    else:
                        eprint("CITY DEAD")

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions
