from typing import Dict
import sys
from agent import agent
import display
import pygame, sys
from pygame.locals import *

if __name__ == "__main__":

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
    while True:
        take_step = False
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    take_step = True
                # elif event.key == pygame.K_a:
                #     # print("Player moved left!")
                # elif event.key == pygame.K_s:
                #     # print("Player moved down!")
                # elif event.key == pygame.K_d:
                #     # print("Player moved right!")

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
                sys.stderr.write(",".join(observation["updates"]))
                actions = agent(observation, None)
                observation["updates"] = []
                step += 1
                observation["step"] = step
                print(",".join(actions))
                print("D_FINISH")
                break
