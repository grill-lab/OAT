from taskmap_pb2 import OutputInteraction, Image, ScreenInteraction, Video, TaskMap, ExecutionStep
from task_graph import *
from .abstract_step_augmenter import AbstractSimpleStepAugmenter


class StepTextAugmenter(AbstractSimpleStepAugmenter):

    def condition(self, step: ExecutionStep) -> bool:
        return True

    def apply_output(self, step: ExecutionStep, processed_output: str) -> ExecutionStep:
        return processed_output

    def get_transformed_input(self, task_map: TaskMap):
        return None

    @staticmethod
    def split_step_text(step_text, step_length):
        new_steps = []
        rest = step_text.replace("\n", "")

        for i in range(0, step_length, 200):
            if rest != "":
                new_step = rest[:i + 100] + rest[i + 100:].split('.', 1)[0]
                if rest != new_step:
                    new_step += '. '
                new_steps.append(new_step.strip())
                rest = rest[len(new_step):]
        return new_steps

    def process(self, step: OutputInteraction, transformed_input) -> OutputInteraction:
        step_on_screen = step.response.screen.paragraphs[0].replace('\n', "")
        del step.response.screen.paragraphs[:]
        length_step = len(step_on_screen)

        screen = ScreenInteraction()

        if length_step < 200:  # don't change the step text
            screen.paragraphs.append(step_on_screen)
        else:
            new_steps = self.split_step_text(step_text=step_on_screen, step_length=length_step)
            for new_step in new_steps:
                screen.paragraphs.append(new_step)

        step.response.screen.MergeFrom(screen)

        return step

