import time

import stream

from offline_pb2 import HTMLDocument
from utils import init, logger
from config import offline_config


class MeasureTime:
    def __init__(self):
        self.currentMeasurement = None
        self.measurements = {}

    def start(self, item):
        self.measurements[item] = (time.time(), 0)
        self.currentMeasurement = item

    def stop(self, item=None):
        if item is None:
            item = self.currentMeasurement
        self.currentMeasurement = None
        self.measurements[item] = (self.measurements[item][0], time.time())

    def print_measurements(self):
        logged_output = "Timing info:"
        if self.measurements.keys == 0:
            return logged_output + " No measurements performed."
        for key, item in self.measurements.items():
            logged_output += f"\n Duration of {key} component: {round(item[1] - item[0], 1)}s"
        return logged_output


def write_protobuf_list_to_file(path, protobuf_list, buffer_size=1000):
    logger.info(path)
    stream.dump(path, *protobuf_list, buffer_size=buffer_size)


def read_protobuf_list_from_file(path, protobuf):
    logger.info(path)
    return [d for d in stream.parse(path, protobuf)]


def webpage_to_proto(webpage):
    # types = {"html": str, "url": str, "url_host_registered_domain": str, "fetch_time": str, "fetch_status": int,
    #          "warc_filename": str, "warc_record_offset": int, "warc_record_length": int, "warc_segment": float,
    #          "crawl": str}

    html_proto = HTMLDocument()
    setattr(html_proto, "html", webpage['html'])
    setattr(html_proto, "url", webpage['url'])

    return html_proto


if __name__ == "__main__":

    logger.info("OFFLINE PIPELINE container started!")
    measurements = MeasureTime()

    for config_step in offline_config["steps"]:
        print(config_step)
        if config_step["enable"]:
            measurements.start(config_step["step"])
            component = init(config_step)
            component.run()
            measurements.stop()

    logger.info(measurements.print_measurements())
    logger.info("OFFLINE PIPELINE container stopped!")
