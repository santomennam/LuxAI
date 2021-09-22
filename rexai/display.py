from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame, sys
from pygame.locals import *
from lux.constants import Constants
from lux.game_map import Position, Cell

# set up the colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

resource_color = {Constants.RESOURCE_TYPES.COAL: BLACK,
                Constants.RESOURCE_TYPES.WOOD: GREEN,
                Constants.RESOURCE_TYPES.URANIUM: RED}

gameDisplay = None

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class GameDisplay:
    def __init__(self):
        if not pygame.get_init():
            pygame.init()

        self.window = pygame.display.set_mode((1400, 800), 0, 32)
        pygame.display.set_caption('Lux')

        self.basicFont = pygame.font.SysFont(None, 18)

    def all_positions(self):
        for x in range(self.game_state.map.width):
            for y in range(self.game_state.map.height):
                yield Position(x,y)

    def all_cells(self):
        return map(lambda p: self.get_cell(p), self.all_positions())

    def all_city_tiles(self, player):
        for k, city in player.cities.items():
            for city_tile in city.citytiles:
                yield city, city_tile

    def cell_rect(self, pos):
        return Rect(pos.x * self.cell_size+self.margin, pos.y * self.cell_size+self.margin, self.cell_size, self.cell_size)

    def draw_text(self, rect, back_color, text_color, message):
        text = self.basicFont.render(message, True, text_color, back_color)
        textRect = text.get_rect()
        textRect.centerx = rect.centerx
        textRect.centery = rect.centery
        self.window.blit(text, textRect)

    def draw_number(self, rect, back_color, text_color, num):
        self.draw_text(rect, back_color, text_color, '{}'.format(num))

    def draw_resource(self, rect, resource):
        pygame.draw.rect(self.window, resource_color[resource.type], rect.inflate(-8, -8), 1)
        self.draw_number(rect, WHITE, resource_color[resource.type], resource.amount)

    def get_cell(self, pos) -> Cell:
        return self.game_state.map.get_cell(pos.x, pos.y)

    def draw_unit(self, unit, color):
        pygame.draw.ellipse(self.window, color, self.cell_rect(unit.pos), 2)
        if unit.is_worker() and unit.can_act():
            pygame.draw.ellipse(self.window, BLACK, self.cell_rect(unit.pos).inflate(-4, -4), 3)

    def draw_city(self, city, tile, color):
        rect = self.cell_rect(tile.pos)
        pygame.draw.rect(self.window, color, rect, 2)
        self.draw_number(rect, WHITE, BLACK, city.fuel)

    def drawUnderlay(self, observation, game_state):

        self.game_state = game_state

        width = self.window.get_rect().width
        height = self.window.get_rect().height

        self.margin = 10

        cell_width = (width-self.margin*2) / game_state.map.width
        cell_height = (height-self.margin*2) / game_state.map.height

        self.cell_size = min(cell_width, cell_height)

        # draw the white background onto the surface
        self.window.fill(WHITE)

        for cell in self.all_cells():
            if cell.has_resource():
                self.draw_resource(self.cell_rect(cell.pos), cell.resource)

        player = game_state.players[observation.player]
        opponent = game_state.players[(observation.player + 1) % 2]

        for city, tile in self.all_city_tiles(player):
            self.draw_city(city, tile, GREEN)

        for city, tile in self.all_city_tiles(opponent):
            self.draw_city(city, tile, RED);

        for unit in player.units:
            self.draw_unit(unit, GREEN)

        for unit in opponent.units:
            self.draw_unit(unit, RED)

    def drawOverlay(self, observation, game_state, messages):

        # sample drawing commands
        # pygame.draw.polygon(self.window, GREEN, ((146, 0), (291, 106), (236, 277), (56, 277), (0, 106)))
        # pygame.draw.line(self.window, BLUE, (60, 60), (120, 60), 4)
        # pygame.draw.circle(self.window, BLUE, (300, 50), 20, 0)
        # pygame.draw.ellipse(self.window, RED, (300, 250, 40, 80), 1)

        action_count = len(messages)

        messages.insert(0, 'Step: {}'.format(game_state.turn))
        messages.insert(1, '# Actions: {}'.format(action_count))

        msg_rect = Rect(game_state.map.height*self.cell_size+10, 20, (game_state.map.width-game_state.map.height)*self.cell_size, 20)
        for msg in messages:
            msg_text = self.basicFont.render(msg, True, BLACK, WHITE)
            self.window.blit(msg_text, msg_rect)
            msg_rect = msg_rect.move(0, 20)

        pygame.display.update()

def init_display():
    global gameDisplay
    gameDisplay = GameDisplay()

def draw_map_underlay(observation, game_state):
    gameDisplay.drawUnderlay(observation, game_state)

def draw_map_overlay(observation, game_state, messages):
    gameDisplay.drawOverlay(observation, game_state, messages)
