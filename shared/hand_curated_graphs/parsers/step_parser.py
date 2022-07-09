from .abstract_parser import AbstractNodeParser
from taskmap_pb2 import OutputInteraction, ScreenInteraction, Image
from task_graph import ExecutionNode

class StepParser(AbstractNodeParser):

    def __init__(self):
        self.response = OutputInteraction()

    def _parse_field(self, label, content):
        if "screen" in label:

            if label == "screen_headline":
                self.response.screen.headline = content

            elif label == "screen_format":
                self.response.screen.format = ScreenInteraction.ScreenFormat.Value(content)

            elif label == "screen_text":
                self.response.screen.paragraphs.append(content)

            elif label == "screen_image_path":
                screen_image: Image = self.response.screen.image_list.add()
                screen_image.path = content

        elif label == "speech":
            self.response.speech_text = content
        elif label == "description":
            self.response.description = content

    def _return_node(self) -> ExecutionNode:
        return ExecutionNode(response=self.response)
