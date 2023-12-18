import torch
import marqo
import os
from utils import logger, get_file_system
from marqo.errors import BackendCommunicationError
from abc import ABC, abstractmethod


class BaseMarqoUtils(ABC):

    def __init__(self, index_settings="", batch_size=0, processes=1):
        self.device: int = -1 if not torch.cuda.is_available() else 0
        logger.info(f"Cuda found: {torch.cuda.is_available()}")
        if os.environ.get('MARQO_URL'):
            self.mq = marqo.Client(url=os.environ['MARQO_URL'])
            logger.info('MARQO URL found')
        else:
            logger.warning("MARQO CONTAINER ENV URL NOT FOUND!")
            logger.warning("MARQO WILL NOT RUN!")

        self.batch_size = batch_size
        self.processes = processes
        self.index_settings = index_settings

        marqo.set_log_level('WARN')

    def check_if_index_exists(self, index_name):
        """ Method to check for existing indices on Marqo-os mounted folder """
        try:
            if hasattr(self, 'mq'):
                existing_indices = self.mq.get_indexes()
                logger.info(f"Existing indices: {[i.index_name for i in existing_indices['results']]}")
                if index_name in [i.index_name for i in existing_indices['results']]:
                    return True
                else:
                    logger.info(f"Index {index_name} does not exist!")
                    return False
            else:
                logger.warning(f"Marqo is not running")
                logger.info(e)
                return False             

        except BackendCommunicationError as e:
            logger.warning('Failed connection with Marqo container, is it running?')
            logger.info(e)
            return False