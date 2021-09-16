from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame, sys
from pygame.locals import *
from lux.constants import Constants


windowSurface = None
basicFont = None

# set up the colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

resource_color = {Constants.RESOURCE_TYPES.COAL: BLACK,
                Constants.RESOURCE_TYPES.WOOD: GREEN,
                Constants.RESOURCE_TYPES.URANIUM: RED}

def init_display():
    global windowSurface
    global basicFont
    # set up pygame
    pygame.init()

    # set up the window
    windowSurface = pygame.display.set_mode((1400, 800), 0, 32)
    pygame.display.set_caption('Hello world!')

    # set up fonts
    basicFont = pygame.font.SysFont(None, 18)

def draw_resource(rect, resource):
    global basicFont
    # pygame.draw.rect(windowSurface, resource_color[resource.type], rect)
    text = basicFont.render('{}'.format(resource.amount), True, WHITE, resource_color[resource.type])
    textRect = text.get_rect()
    textRect.centerx = rect.centerx
    textRect.centery = rect.centery
    windowSurface.blit(text, textRect)

def draw_map(observation, game_state, messages):
    global windowSurface
    global basicFont
    # set up the text

    width = windowSurface.get_rect().width
    height = windowSurface.get_rect().height

    margin = 10

    cell_width = (width-margin*2) / game_state.map.width
    cell_height = (height-margin*2) / game_state.map.height

    cell_size = min(cell_width, cell_height)

    # text = basicFont.render('Step: {}'.format(game_state.turn), True, WHITE, BLUE)
    # textRect = text.get_rect()
    # textRect.centerx = windowSurface.get_rect().centerx
    # textRect.centery = windowSurface.get_rect().centery

    # draw the white background onto the surface
    windowSurface.fill(WHITE)

    for y in range(game_state.map.width):
        for x in range(game_state.map.height):
            cell = game_state.map.get_cell(x, y)
            cell_rect = Rect(x * cell_size+margin, y * cell_size+margin, cell_size - 2, cell_size - 2)
            if cell.has_resource():
                draw_resource(cell_rect, cell.resource)
                # pygame.draw.rect(windowSurface, RED,
                #                  (x * cell_size, y * cell_size, cell_size - 2, cell_size - 2))

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]

    # we iterate over all our units and do something with them
    for unit in player.units:
        x = unit.pos.x
        y = unit.pos.y
        cell_rect = Rect(x * cell_size + margin, y * cell_size + margin, cell_size - 2, cell_size - 2)
        pygame.draw.ellipse(windowSurface, GREEN, cell_rect, 2)
        if unit.is_worker() and unit.can_act():
            pygame.draw.ellipse(windowSurface, BLACK, cell_rect.inflate(-4, -4), 3)

    for unit in opponent.units:
        x = unit.pos.x
        y = unit.pos.y
        cell_rect = Rect(x * cell_size + margin, y * cell_size + margin, cell_size - 2, cell_size - 2)
        pygame.draw.ellipse(windowSurface, RED, cell_rect, 2)
        if unit.is_worker() and unit.can_act():
            pygame.draw.ellipse(windowSurface, BLACK, cell_rect.inflate(-4, -4), 3)
        # if unit.is_worker() and unit.can_act():

    # # draw a green polygon onto the surface
    # pygame.draw.polygon(windowSurface, GREEN, ((146, 0), (291, 106), (236, 277), (56, 277), (0, 106)))
    #
    # # draw some blue lines onto the surface
    # pygame.draw.line(windowSurface, BLUE, (60, 60), (120, 60), 4)
    # pygame.draw.line(windowSurface, BLUE, (120, 60), (60, 120))
    # pygame.draw.line(windowSurface, BLUE, (60, 120), (120, 120), 4)
    #
    # # draw a blue circle onto the surface
    # pygame.draw.circle(windowSurface, BLUE, (300, 50), 20, 0)
    #
    # # draw a red ellipse onto the surface
    # pygame.draw.ellipse(windowSurface, RED, (300, 250, 40, 80), 1)

    # draw the text's background rectangle onto the surface
    # pygame.draw.rect(windowSurface, RED,
    #                  (textRect.left - 20, textRect.top - 20, textRect.width + 40, textRect.height + 40))

    action_count = len(messages)

    messages.insert(0, 'Step: {}'.format(game_state.turn))
    messages.insert(1, '# Actions: {}'.format(action_count))

    msg_rect = Rect(game_state.map.height*cell_size+10, 20, (game_state.map.width-game_state.map.height)*cell_size, 20)
    for msg in messages:
        msg_text = basicFont.render(msg, True, BLACK, WHITE)
        windowSurface.blit(msg_text, msg_rect)
        msg_rect = msg_rect.move(0, 20)

    # # get a pixel array of the surface
    # pixArray = pygame.PixelArray(windowSurface)
    # pixArray[480][380] = BLACK
    # del pixArray

    # draw the text onto the surface
    # windowSurface.blit(text, textRect)

    # draw the window onto the screen
    pygame.display.update()
