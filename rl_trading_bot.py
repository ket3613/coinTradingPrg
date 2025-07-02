import pyupbit
import gym
import numpy as np

class TradingEnv(gym.Env):
    """간단한 수익률 기반 보상 환경"""

    metadata = {"render.modes": ["human"]}

    def __init__(self, ticker="KRW-DOGE", count=200):
        super().__init__()
        self.ticker = ticker
        self.data = pyupbit.get_ohlcv(ticker, interval="minute30", count=count)
        self.prices = self.data["close"].values
        self.max_steps = len(self.prices) - 1
        self.action_space = gym.spaces.Discrete(3)  # 0: 관망, 1: 매수, 2: 매도
        self.observation_space = gym.spaces.Box(low=0, high=np.inf, shape=(1,))
        self.reset()

    def reset(self):
        self.current_step = 0
        self.cash = 1_000_000  # 시작 자본
        self.coin = 0.0
        self.total_asset = self.cash
        return np.array([self.prices[self.current_step]])

    def step(self, action):
        price = self.prices[self.current_step]
        self.current_step += 1
        done = self.current_step >= self.max_steps

        if action == 1:  # 매수
            if self.cash > 0:
                self.coin += self.cash / price
                self.cash = 0
        elif action == 2:  # 매도
            if self.coin > 0:
                self.cash += self.coin * price
                self.coin = 0

        new_total_asset = self.cash + self.coin * price
        reward = (new_total_asset - self.total_asset) / self.total_asset
        self.total_asset = new_total_asset
        obs = np.array([self.prices[self.current_step]])
        return obs, reward, done, {}

    def render(self, mode="human"):
        print(f"step: {self.current_step}, asset: {self.total_asset:.2f}")


if __name__ == "__main__":
    env = TradingEnv()
    obs = env.reset()
    done = False
    total_reward = 0.0
    while not done:
        action = env.action_space.sample()
        obs, reward, done, _ = env.step(action)
        total_reward += reward
        env.render()
    print("Total reward:", total_reward)
