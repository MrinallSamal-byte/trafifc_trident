"""
Traffic-Mind – DQN Trainer
Complete training loop with logging, model saving, and epsilon decay.
"""

import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

from ai.dqn_network import DQN
from ai.replay_buffer import ReplayBuffer
from config.settings import (
    STATE_SIZE, ACTION_SIZE,
    LEARNING_RATE, GAMMA,
    EPSILON_START, EPSILON_END, EPSILON_DECAY,
    BATCH_SIZE, MEMORY_SIZE,
    TARGET_UPDATE_FREQ,
)


class DQNTrainer:
    """Handles training of the DQN agent."""

    def __init__(self, state_size: int = STATE_SIZE, action_size: int = ACTION_SIZE):
        self.state_size = state_size
        self.action_size = action_size

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  Training device: {self.device}")

        self.policy_net = DQN(state_size, action_size).to(self.device)
        self.target_net = DQN(state_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=LEARNING_RATE)
        self.replay_buffer = ReplayBuffer(MEMORY_SIZE)
        self.epsilon = EPSILON_START
        self.steps_done = 0

    # ─── action selection ─────────────────
    def select_action(self, state) -> int:
        if random.random() < self.epsilon:
            return random.randrange(self.action_size)

        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_t)
            return q_values.argmax(dim=1).item()

    # ─── optimise one step ────────────────
    def optimize(self):
        if len(self.replay_buffer) < BATCH_SIZE:
            return

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(BATCH_SIZE)
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        # Current Q-values
        q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        # Target Q-values
        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1)[0]
            target_q = rewards + GAMMA * next_q * (1 - dones)

        loss = nn.MSELoss()(q_values, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        self.steps_done += 1

    # ─── target network sync ─────────────
    def update_target(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    # ─── epsilon decay ────────────────────
    def decay_epsilon(self):
        self.epsilon = max(EPSILON_END, self.epsilon * EPSILON_DECAY)

    # ─── persist ──────────────────────────
    def save_model(self, path: str):
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        torch.save(self.policy_net.state_dict(), path)

    def load_model(self, path: str):
        self.policy_net.load_state_dict(
            torch.load(path, map_location=self.device, weights_only=True)
        )
        self.policy_net.eval()

    # ─── full training loop ───────────────
    def train(self, env, num_episodes: int = 500, render: bool = False, save_dir: str = "models"):
        """
        Master training loop.

        Returns:
            list of episode rewards for plotting.
        """
        os.makedirs(save_dir, exist_ok=True)
        best_reward = -float("inf")
        reward_history = []

        for episode in range(num_episodes):
            state = env.reset()
            total_reward = 0.0
            steps = 0

            while True:
                action = self.select_action(state)
                next_state, reward, done, info = env.step(action)
                self.replay_buffer.push(state, action, reward, next_state, done)
                self.optimize()

                total_reward += reward
                state = next_state
                steps += 1

                if steps % TARGET_UPDATE_FREQ == 0:
                    self.update_target()

                if render:
                    env.render()

                if done:
                    break

            self.decay_epsilon()
            reward_history.append(total_reward)

            # Save best
            if total_reward > best_reward:
                best_reward = total_reward
                self.save_model(os.path.join(save_dir, "best_model.pth"))

            # Checkpoint
            if episode % 50 == 0:
                self.save_model(os.path.join(save_dir, f"checkpoint_{episode}.pth"))

            # Log
            if episode % 10 == 0:
                avg = np.mean(reward_history[-10:]) if reward_history else 0
                tp = info.get("total_passed", 0)
                aw = info.get("avg_wait", 0)
                print(
                    f"Episode {episode:4d} | "
                    f"Reward: {total_reward:7.1f} | "
                    f"Avg(10): {avg:7.1f} | "
                    f"Epsilon: {self.epsilon:.3f} | "
                    f"Throughput: {tp:4d} | "
                    f"Avg Wait: {aw:5.1f}"
                )

        print(f"\n✅ Training complete!  Best reward: {best_reward:.1f}")
        print(f"   Model saved to: {save_dir}/best_model.pth")
        return reward_history
