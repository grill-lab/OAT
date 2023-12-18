import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import trange
import pytest


@pytest.mark.slow
def test_load_launch_request(interaction_obj):
    test_length = 60  # seconds
    tps = 7
    futures = []

    def load():
        try:
            start = time.time()
            response = interaction_obj.send_request('hello', '', True, '')
            latency = time.time() - start
            if response:
                return response.status_code, latency
            else:
                return None, latency
        except Exception as e:
            print(str(e))
            return None, 10

    with ThreadPoolExecutor(max_workers=test_length * tps) as executor:

        for _ in trange(test_length):
            # WARM-UP with 1 TPS
            future = executor.submit(load)
            futures.append(future)
            time.sleep(1)

        errors = 0.0
        sum_latency = 0
        for future in futures:
            status_code, latency = future.result()
            sum_latency += latency
            if not status_code == 200:
                errors += 1

        print(f"Average Latency for Warm-up: {sum_latency/test_length}s and success rate {1 - errors/test_length}")

    with ThreadPoolExecutor(max_workers=test_length * tps) as executor:

        futures = []
        for _ in trange(test_length):
            for _ in range(tps):
                future = executor.submit(load)
                futures.append(future)
            time.sleep(1)

        errors = 0.0
        sum_latency = 0
        for future in futures:
            status_code, latency = future.result()
            sum_latency += latency
            if not status_code == 200:
                errors += 1

        success_ratio = 1 - errors / (test_length * tps)

        print(f"Average Latency for Test: {sum_latency / (tps*test_length)}s")

        assert success_ratio > 0.7, f'Success rate of {success_ratio * 100:.2f}%, when threshold is 70%'
        print(f"Successful test with success ration of {success_ratio * 100:.2f}%")

        assert False
