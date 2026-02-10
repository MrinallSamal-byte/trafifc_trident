from setuptools import setup, find_packages

setup(
    name="traffic-mind",
    version="1.0.0",
    description="AI-Powered Reinforcement Learning Traffic Light Controller",
    author="Trident Academy Hackathon Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pygame>=2.5.0",
        "torch>=2.0.0",
        "numpy>=1.24.0",
        "pyserial>=3.5",
        "matplotlib>=3.7.0",
    ],
    entry_points={
        "console_scripts": [
            "traffic-mind=main:main",
            "traffic-mind-train=train:train",
            "traffic-mind-demo=demo:run_demo",
        ],
    },
)
