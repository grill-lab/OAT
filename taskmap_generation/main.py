
from config import config_dict
from runner import Runner

if __name__ == '__main__':
    print(config_dict)

    runner = Runner(config_dict)
    runner.build_taskmaps()
    runner.build_index()