from .chitchat_classifier import (
    ChitChatClassifier as DefaultChitChatClassifier,
)

from .chitchat_classifier_servicer import (Servicer,
    add_ChitChatClassifierServicer_to_server as add_to_server,
)
