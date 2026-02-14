"""
Traffic-Mind – Experience Replay Buffer
"""

import random
from collections import deque
import torch
import numpy as np


class ReplayBuffer:
    """Fixed-size circular buffer storing (s, a, r, s', done) transitions."""

    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action: int, reward: float, next_state, done: bool):
        self.buffer.append((
            np.array(state, dtype=np.float32),
            action,
            reward,
            np.array(next_state, dtype=np.float32),
            done,
        ))

    def sample(self, batch_size: int):
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        return (
            torch.FloatTensor(np.array(states)),
            torch.LongTensor(actions),
            torch.FloatTensor(rewards),
            torch.FloatTensor(np.array(next_states)),
            torch.FloatTensor([float(d) for d in dones]),
        )

    def __len__(self) -> int:
        return len(self.buffer)
