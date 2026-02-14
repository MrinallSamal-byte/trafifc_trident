#!/usr/bin/env python3
"""
Traffic-Mind — DQN Training Script
═══════════════════════════════════
Train the reinforcement-learning agent before running the demo.

Usage:
    python train.py                         # 500 episodes, no GUI
    python train.py --episodes 300 --render # with live visualisation
"""

import argparse
import os
import sys
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

from config.settings import STATE_SIZE, ACTION_SIZE, TARGET_UPDATE_FREQ
from simulation.environment import TrafficEnvironment
from ai.trainer import DQNTrainer


def plot_training_curve(rewards: list, path: str = "models/training_curve.png"):
    """Save a nice reward-over-episodes chart."""
    plt.figure(figsize=(10, 5))
    plt.plot(rewards, alpha=0.3, color="steelblue", label="Episode reward")

    # Smoothed (running avg of 20)
    window = 20
    if len(rewards) >= window:
        import numpy as np
        smoothed = np.convolve(rewards, np.ones(window) / window, mode="valid")
        plt.plot(range(window - 1, len(rewards)), smoothed, color="orange",
                 linewidth=2, label=f"Moving avg ({window})")

    plt.xlabel("Episode")
    plt.ylabel("Total Reward")
    plt.title("Traffic-Mind — DQN Training Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"📈 Training curve saved to {path}")


def train():
    parser = argparse.ArgumentParser(description="Train Traffic-Mind DQN agent")
    parser.add_argument("--episodes", type=int, default=500, help="Number of training episodes")
    parser.add_argument("--render", action="store_true", help="Show PyGame window during training")
    parser.add_argument("--save-dir", type=str, default="models", help="Directory for saved models")
    args = parser.parse_args()

    os.makedirs(args.save_dir, exist_ok=True)

    print("═" * 55)
    print("  🚦  Traffic-Mind — DQN Training")
    print("═" * 55)
    print(f"  Episodes       : {args.episodes}")
    print(f"  State size     : {STATE_SIZE}")
    print(f"  Action size    : {ACTION_SIZE}")
    print(f"  Render         : {args.render}")
    print(f"  Save directory : {args.save_dir}")
    print("═" * 55)
    print()

    env = TrafficEnvironment(render_mode=args.render)
    trainer = DQNTrainer(STATE_SIZE, ACTION_SIZE)

    reward_history = trainer.train(
        env,
        num_episodes=args.episodes,
        render=args.render,
        save_dir=args.save_dir,
    )

    plot_training_curve(reward_history, os.path.join(args.save_dir, "training_curve.png"))

    env.close()
    print("\n🏁 Done!")


if __name__ == "__main__":
    train()
