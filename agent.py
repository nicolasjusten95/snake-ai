import torch
import random
import numpy as np
from collections import deque
from snake_game_ai import SnakeGameAi, Direction, Point
from model import LinearQNet, QTrainer
from helper import plot

MAX_MEMORY = 200_000
BATCH_SIZE = 2000
LR = 0.001


class Agent:

    def __init__(self):
        self.number_of_games = 0
        self.epsilon = 0  # randomness
        self.gamma = 0.9  # discount rate
        self.memory = deque(maxlen=MAX_MEMORY)
        self.model = LinearQNet(11, 256, 3)
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)

    def get_state(self, game):
        head = game.snake[0]
        point_l = Point(head.x - 20, head.y)
        point_r = Point(head.x + 20, head.y)
        point_u = Point(head.x, head.y - 20)
        point_d = Point(head.x, head.y + 20)
        dir_l = game.direction == Direction.LEFT
        dir_r = game.direction == Direction.RIGHT
        dir_u = game.direction == Direction.UP
        dir_d = game.direction == Direction.DOWN

        state = [
            # danger straight
            (dir_r and game.is_collision(point_r)) or
            (dir_l and game.is_collision(point_l)) or
            (dir_u and game.is_collision(point_u)) or
            (dir_d and game.is_collision(point_d)),
            # danger right
            (dir_u and game.is_collision(point_r)) or
            (dir_d and game.is_collision(point_l)) or
            (dir_l and game.is_collision(point_u)) or
            (dir_r and game.is_collision(point_d)),
            # danger left
            (dir_d and game.is_collision(point_r)) or
            (dir_u and game.is_collision(point_l)) or
            (dir_r and game.is_collision(point_u)) or
            (dir_l and game.is_collision(point_d)),
            # move direction
            dir_l,
            dir_r,
            dir_u,
            dir_d,
            # food direction
            game.food.x < game.head.x,
            game.food.x > game.head.x,
            game.food.y < game.head.y,
            game.food.y > game.head.y
        ]

        return np.array(state, dtype=int)

    def remember(self, state, action, reward, next_state, is_game_over):
        self.memory.append((state, action, reward, next_state, is_game_over))

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            sample = random.sample(self.memory, BATCH_SIZE)
        else:
            sample = self.memory
        states, actions, rewards, next_states, is_game_overs = zip(*sample)
        self.trainer.train_step(states, actions, rewards, next_states, is_game_overs)

    def train_short_memory(self, state, action, reward, next_state, is_game_over):
        self.trainer.train_step(state, action, reward, next_state, is_game_over)

    def get_action(self, state):
        self.epsilon = 80 - self.number_of_games
        move = [0, 0, 0]
        if (random.randint(0, 200)) < self.epsilon:
            direction = random.randint(0, 2)
            move[direction] = 1
        else:
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model(state0)
            direction = torch.argmax(prediction).item()
            move[direction] = 1

        return move


def train():
    plot_scores = []
    plot_mean_sores = []
    total_score = 0
    record = 0
    agent = Agent()
    game = SnakeGameAi()

    while True:
        state_old = agent.get_state(game)
        move = agent.get_action(state_old)
        reward, is_game_over, score = game.play_step(move)
        state_new = agent.get_state(game)
        agent.train_short_memory(state_old, move, reward, state_new, is_game_over)
        agent.remember(state_old, move, reward, state_new, is_game_over)
        if is_game_over:
            game.reset()
            agent.number_of_games += 1
            agent.train_long_memory()
            if score > record:
                record = score
                agent.model.save()
            print('Game:', agent.number_of_games, 'Score:', score, 'Record:', record)
            plot_scores.append(score)
            total_score += score
            mean_score = total_score / agent.number_of_games
            plot_mean_sores.append(mean_score)
            plot(plot_scores, plot_mean_sores)


if __name__ == '__main__':
    train()
