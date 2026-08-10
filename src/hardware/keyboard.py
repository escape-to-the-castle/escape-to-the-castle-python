from __future__ import annotations

import pygame

from .interface import Action, HardwareInterface


class KeyboardHardware(HardwareInterface):
    def poll_actions(self) -> set[Action]:
        actions: set[Action] = set()
        keys = pygame.key.get_pressed()

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            actions.add(Action.MOVE_LEFT)
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            actions.add(Action.MOVE_RIGHT)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.add(Action.QUIT)
            elif event.type == pygame.KEYDOWN:
                mapping = {
                    pygame.K_SPACE: Action.JUMP,
                    pygame.K_s: Action.ROLL,
                    pygame.K_DOWN: Action.ROLL,
                    pygame.K_LSHIFT: Action.ROLL,
                    pygame.K_RSHIFT: Action.ROLL,
                    pygame.K_1: Action.ANSWER_1,
                    pygame.K_2: Action.ANSWER_2,
                    pygame.K_3: Action.ANSWER_3,
                    pygame.K_4: Action.ANSWER_4,
                    pygame.K_r: Action.RESTART,
                    pygame.K_ESCAPE: Action.QUIT,
                }
                action = mapping.get(event.key)
                if action is not None:
                    actions.add(action)
        return actions
