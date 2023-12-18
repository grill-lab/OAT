import hashlib
from typing import Any, Callable, ClassVar, Type
import time
import os

import grpc
from grpc_interceptor import ServerInterceptor
from grpc_interceptor.exceptions import GrpcException
from functools import wraps

from utils import logger


def get_taskmap_id(doc_type: str, dataset: str, url: str) -> str:
    """Generate a TaskMap ID string.

    Given a document type, dataset, and URL, this method will
    return a string concatenation of each of the 3 values, 
    encoding the URL as an MD5 hash.

    Args:
        document type (str): TaskMap document type
        dataset (str): dataset the TaskMap is part of
        url (str): source URL for the TaskMap

    Returns:
        A concatenation of the first 2 parameters with 
        an MD5 hash of the URL (str)

    """
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return doc_type + '+' + dataset + '+' + md5


def init(config_dict: dict) -> Any:
    """Generic method to instantiate a class with a kwargs dict.

    This method expects to receive a dict with 'class' and 'kwargs'
    keys. The value of 'class' should be a class type. The value of
    'kwargs' should be a dict of param_name: param_value pairs.

    The method instantiates an object of the given class and 
    passes the kwargs dict to the constructor, then returns the
    new object.

    Args:
        config_dict (dict): a dict containing 'class' and 'kwargs' keys

    Returns:
        an instance of the supplied class
    """
    default_class: Type[Any] = config_dict['class']
    kwargs: dict = config_dict.get('kwargs', {})

    return default_class(**kwargs)

def get_file_system() -> str:
    """Returns the path to the 'file_system' folder inside containers.

    The shared folder is mounted to each OAT container using the 
    /shared mountpoint. This method simply returns the path to the
    file_system folder inside, it's very widely used by the various
    services so it makes sense to have it defined in a single place.

    Returns:
        the path to the shared/file_system folder (str)

    """
    return "/shared/file_system"


class ExceptionInterceptor(ServerInterceptor):

    def intercept(self, method: Callable, request: Any, context: grpc.ServicerContext, method_name: str) -> Any:

        try:
            response = method(request, context)
            if response is None:
                logger.error(f"{method_name} RETURNED A NONE RESPONSE!")
                raise Exception("None Response")
            return response
        except GrpcException as exc:
            logger.error("Exception while executing %s" % method_name, exc_info=exc)
            context.set_code(exc.status_code)
            context.set_details(exc.details)
            raise
        except Exception as exc:
            logger.error("Exception while executing %s" % method_name, exc_info=exc)
            context.set_code(grpc.StatusCode.UNKNOWN)
            context.set_details(type(exc).__name__ + ": " + str(exc))
            raise


class LatencyInterceptor(ServerInterceptor):

    def intercept(self, method: Callable, request: Any, context: grpc.ServicerContext, method_name: str) -> Any:
        start = time.time()
        response = method(request, context)
        latency = time.time() - start
        container_name = os.environ.get('CONTAINER_NAME', "Undefined_Container_Name")

        logger.info(f"[SYSTEM_LATENCY_LOG] {container_name}{method_name} {latency:.2f}")
        return response


def get_server_interceptor():
    return ExceptionInterceptor()

def get_interceptors():
    return [ExceptionInterceptor(), LatencyInterceptor()]


def log_latency(fn):
    @wraps(fn)
    def decorated(*args, **kwargs):
        start = time.time()
        response = fn(*args, **kwargs)
        latency = time.time() - start
        container_name = os.environ.get('CONTAINER_NAME', "Undefined_Container_Name")
        logger.info(f"[SYSTEM_LATENCY_LOG] {container_name}/{fn.__name__} {latency:.2f}")

        return response

    return decorated
