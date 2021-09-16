from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame, sys
from pygame.locals import *
from lux.constants import Constants

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

class GameDisplay:
    def __init__(self):
        if not pygame.get_init():
            pygame.init()

        self.window = pygame.display.set_mode((1400, 800), 0, 32)
        pygame.display.set_caption('Lux')

        self.basicFont = pygame.font.SysFont(None, 18)

    def draw_resource(self, rect, resource):
        # pygame.draw.rect(self.window, resource_color[resource.type], rect)
        text = self.basicFont.render('{}'.format(resource.amount), True, WHITE, resource_color[resource.type])
        textRect = text.get_rect()
        textRect.centerx = rect.centerx
        textRect.centery = rect.centery
        self.window.blit(text, textRect)

    def draw(self, observation, game_state, messages):
        # set up the text

        width = self.window.get_rect().width
        height = self.window.get_rect().height

        margin = 10

        cell_width = (width-margin*2) / game_state.map.width
        cell_height = (height-margin*2) / game_state.map.height

        cell_size = min(cell_width, cell_height)

        # text = basicFont.render('Step: {}'.format(game_state.turn), True, WHITE, BLUE)
        # textRect = text.get_rect()
        # textRect.centerx = self.window.get_rect().centerx
        # textRect.centery = self.window.get_rect().centery

        # draw the white background onto the surface
        self.window.fill(WHITE)

        for y in range(game_state.map.width):
            for x in range(game_state.map.height):
                cell = game_state.map.get_cell(x, y)
                cell_rect = Rect(x * cell_size+margin, y * cell_size+margin, cell_size - 2, cell_size - 2)
                if cell.has_resource():
                    self.draw_resource(cell_rect, cell.resource)
                    # pygame.draw.rect(self.window, RED,
                    #                  (x * cell_size, y * cell_size, cell_size - 2, cell_size - 2))

        player = game_state.players[observation.player]
        opponent = game_state.players[(observation.player + 1) % 2]

        # we iterate over all our units and do something with them
        for unit in player.units:
            x = unit.pos.x
            y = unit.pos.y
            cell_rect = Rect(x * cell_size + margin, y * cell_size + margin, cell_size - 2, cell_size - 2)
            pygame.draw.ellipse(self.window, GREEN, cell_rect, 2)
            if unit.is_worker() and unit.can_act():
                pygame.draw.ellipse(self.window, BLACK, cell_rect.inflate(-4, -4), 3)

        for unit in opponent.units:
            x = unit.pos.x
            y = unit.pos.y
            cell_rect = Rect(x * cell_size + margin, y * cell_size + margin, cell_size - 2, cell_size - 2)
            pygame.draw.ellipse(self.window, RED, cell_rect, 2)
            if unit.is_worker() and unit.can_act():
                pygame.draw.ellipse(self.window, BLACK, cell_rect.inflate(-4, -4), 3)
            # if unit.is_worker() and unit.can_act():

        # # draw a green polygon onto the surface
        # pygame.draw.polygon(self.window, GREEN, ((146, 0), (291, 106), (236, 277), (56, 277), (0, 106)))
        #
        # # draw some blue lines onto the surface
        # pygame.draw.line(self.window, BLUE, (60, 60), (120, 60), 4)
        # pygame.draw.line(self.window, BLUE, (120, 60), (60, 120))
        # pygame.draw.line(self.window, BLUE, (60, 120), (120, 120), 4)
        #
        # # draw a blue circle onto the surface
        # pygame.draw.circle(self.window, BLUE, (300, 50), 20, 0)
        #
        # # draw a red ellipse onto the surface
        # pygame.draw.ellipse(self.window, RED, (300, 250, 40, 80), 1)

        # draw the text's background rectangle onto the surface
        # pygame.draw.rect(self.window, RED,
        #                  (textRect.left - 20, textRect.top - 20, textRect.width + 40, textRect.height + 40))

        action_count = len(messages)

        messages.insert(0, 'Step: {}'.format(game_state.turn))
        messages.insert(1, '# Actions: {}'.format(action_count))

        msg_rect = Rect(game_state.map.height*cell_size+10, 20, (game_state.map.width-game_state.map.height)*cell_size, 20)
        for msg in messages:
            msg_text = self.basicFont.render(msg, True, BLACK, WHITE)
            self.window.blit(msg_text, msg_rect)
            msg_rect = msg_rect.move(0, 20)

        # # get a pixel array of the surface
        # pixArray = pygame.PixelArray(self.window)
        # pixArray[480][380] = BLACK
        # del pixArray

        # draw the text onto the surface
        # self.window.blit(text, textRect)

        # draw the window onto the screen
        pygame.display.update()


def init_display():
    global gameDisplay
    gameDisplay = GameDisplay()

def draw_map(observation, game_state, messages):
    gameDisplay.draw(observation, game_state, messages)

