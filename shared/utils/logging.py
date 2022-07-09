import logging
import logging.config
import yaml
import os

"""
LOGGING CONFIGURATION
"""

try:
    with open("/shared/log_config.yaml", 'rt') as f:
        if not os.path.exists("/shared/logs"):
            os.makedirs("/shared/logs")

        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)

except Exception as e:
    print(e)
    print('Error in the log_config.yaml, switching to DEFAULT configs')

    logging.basicConfig(level=logging.INFO)

logger_parent_name = os.environ.get("LOGGING_LEVEL", "local")
container_name = os.environ.get('CONTAINER_NAME', "Undefined_Container_Name")

logger = logging.getLogger(logger_parent_name + "." + container_name)
