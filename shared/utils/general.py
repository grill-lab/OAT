from typing import Callable, Any, ClassVar


def get_taskmap_id(doc_type, dataset, url) -> str:
    """ Generate taskmap_id using MD5 hash. """
    import hashlib
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return doc_type + '+' + dataset + '+' + md5


def init(config_dict: dict) -> Any:
    default_class: ClassVar = config_dict['class']
    kwargs: dict = config_dict.get('kwargs', {})

    return default_class(**kwargs)

def consume_intents(user_interaction,
                    intents_list):

    for intent in intents_list:
        if intent in user_interaction.intents:
            user_interaction.intents.remove(intent)
            user_interaction.intents.append('Consumed.'+intent)


def get_file_system():
    return "/shared/file_system"


def get_server_interceptor():

    from grpc_interceptor import ServerInterceptor
    from grpc_interceptor.exceptions import GrpcException
    import grpc
    from utils import logger

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

    return ExceptionInterceptor()


def jaccard_similarity(list1, list2):
    intersection = len(list(set(list1).intersection(list2)))
    union = (len(set(list1)) + len(set(list2))) - intersection
    return float(intersection) / union