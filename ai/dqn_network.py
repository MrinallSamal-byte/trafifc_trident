"""
Traffic-Mind – Deep Q-Network Architecture
"""

import torch
import torch.nn as nn
from config.settings import STATE_SIZE, ACTION_SIZE


class DQN(nn.Module):
    """
    Deep Q-Network for traffic light control.

    Input  (STATE_SIZE = 12):
        [north_count, north_avg_wait, north_queue_len,
         south_count, south_avg_wait, south_queue_len,
         east_count,  east_avg_wait,  east_queue_len,
         west_count,  west_avg_wait,  west_queue_len]

    Output (ACTION_SIZE = 2):
        Q(s, a) for each action
        0 → NS green   1 → EW green
    """

    def __init__(self, state_size: int = STATE_SIZE, action_size: int = ACTION_SIZE):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, action_size),
        )
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)
