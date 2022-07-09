import time
from .. import logger

__time_dict: dict = {}

def flush_times():
    global __time_dict
    for key in __time_dict.keys():
        __time_dict[key] = None

def print_times():
    global __time_dict

    logger.info("LOGGING STATS FOR TIMEIT")
    for key, value in __time_dict.items():
        if value is None:
            continue
        logger.info(f'- Function {key} took on average {value["total"] / value["counter"]:.4f} s and '
                    f'it was called {value["counter"]} times, for a total of {value["total"]} s')

def timeit(func):
    def wrapper(*args, **kwargs):
        global __time_dict
        start = time.time()
        result = func(*args, **kwargs)
        time_elapsed = time.time()-start
        logger.info(f"TIMEIT: {func.__name__} took {time_elapsed:.4f} s")
        if __time_dict.get(func.__name__) is None:
            __time_dict[func.__name__] = {
                'total': 0.0,
                'counter': 0
            }

        __time_dict[func.__name__]['total'] += time_elapsed
        __time_dict[func.__name__]['counter'] += 1

        return result
    return wrapper
