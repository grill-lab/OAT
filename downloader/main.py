import os
import sys

from utils import Downloader, logger

"""
This can be used to trigger downloads of all artefacts for OAT
services without actually starting them all up. This can be used
for testing or if you want to ensure all files are downloaded 
before launching the services.
"""

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: docker compose run downloader <service1> [<service2> ...]")
        print("\te.g docker compose run downloader offline")
        print("")
        print("Supported services:")
        print("  - offline")
        print("  - functionalities")
        print("  - neural_functionalities")
        print("  - llm_functionalities")
        print("  - training")
        sys.exit(0)

    services = sys.argv[1:]
    logger.info(f"downloader: running on {len(services)}")

    for service in services:
        if not os.path.isdir(f"/{service}"):
            logger.error(f"Path /{service} doesn't exist (update docker-compose.yml volume configuration?)")
            sys.exit(-1)

        toml_file = f"/{service}/downloads.toml"
        logger.info(f"Starting downloads for {service} from {toml_file}")
        downloader = Downloader(toml_file)
        downloader.download()
        logger.info(f"Finished downloading for {service}")
