from typing import Dict
import sys
from agent import agent
import display
import pygame, sys
from pygame.locals import *


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


if __name__ == "__main__":
    doGraphics = False

    if doGraphics:
        display.init_display()
    def read_input():
        """
        Reads input from stdin
        """
        try:
            return input()
        except EOFError as eof:
            raise SystemExit(eof)
    step = 0
    class Observation(Dict[str, any]):
        def __init__(self, player=0) -> None:
            self.player = player
            # self.updates = []
            # self.step = 0
    observation = Observation()
    observation["updates"] = []
    observation["step"] = 0
    player_id = 0

    if doGraphics:
        pygame.time.set_timer( pygame.USEREVENT, 200)

    while True and doGraphics:
        take_step = False
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    pygame.time.set_timer(pygame.USEREVENT, 0)
                    take_step = True
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

                # elif event.key == pygame.K_a:
                #     # print("Player moved left!")
                # elif event.key == pygame.K_s:
                #     # print("Player moved down!")
                # elif event.key == pygame.K_d:
                #     # print("Player moved right!")
            elif event.type ==  pygame.USEREVENT:
                take_step = True

        pygame.display.update()

        if not take_step:
            continue
        while True:
            inputs = read_input()
            observation["updates"].append(inputs)

            if step == 0:
                player_id = int(observation["updates"][0])
                observation.player = player_id
            if inputs == "D_DONE":
                # sys.stderr.write(",".join(observation["updates"]))
                actions = agent(observation, None,doGraphics)
                observation["updates"] = []
                step += 1
                observation["step"] = step
                print(",".join(actions))
                print("D_FINISH")
                break
    while True and not doGraphics:
        while True:
            inputs = read_input()
            observation["updates"].append(inputs)
            if step == 0:
                player_id = int(observation["updates"][0])
                observation.player = player_id
            if inputs == "D_DONE":
                # sys.stderr.write(",".join(observation["updates"]))
                actions = agent(observation, None, doGraphics)
                observation["updates"] = []
                step += 1
                observation["step"] = step
                print(",".join(actions))
                print("D_FINISH")
                eprint("finished turn")
                break
