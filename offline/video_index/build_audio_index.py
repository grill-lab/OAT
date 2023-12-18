import shutil
import json
import os

from utils import get_file_system, logger, Downloader
from index_builders import PyseriniBM25Builder


class AudioIndexBuilder(PyseriniBM25Builder):
    """ Class that runs the video document generation process and builds index. """

    # we don't actually use the two methods since we don't have audio protos
    @staticmethod
    def parse(proto_message):
        pass

    def build_doc(self, proto_message, include_proto):
        pass

    def __init__(self, temp_dir: str, index_dir: str):
        # Unpack config_dict.
        self.version = "0.1_test"
        self.file_system_path = get_file_system()
        artefact_id = "whisper_transcripts"
        downloader = Downloader()
        downloader.download([artefact_id])
        self.audio_metadata_dir = downloader.get_artefact_path(artefact_id)
        self.temp_dir = temp_dir
        self.version = "test_audio_corpus"
        self.index_dir = index_dir

        if not os.path.isdir(self.audio_metadata_dir):
            logger.warning("Required Whisper transcripts are not found, can't run this component. "
                           "Have you run the bash script?")
            exit(1)

        # remove the temp audio directory if it exists
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)

        # index folder
        if not os.path.isdir(index_dir):
            os.makedirs(index_dir, exist_ok=True)

    def build_meta_documents(self):
        # process audio json directly from jsonl (in offline/whisper_transcripts/ into jsonl in the right format
        files = os.listdir(self.audio_metadata_dir)
        with open(os.path.join(self.temp_dir, "full_transcript_dumps.jsonl"), "w") as out_file:
            for file in files:
                with open(os.path.join(self.audio_metadata_dir, file), "r") as in_file:
                    for line in in_file.readlines():
                        transcript = json.loads(line)
                        formatted = {
                            "id": transcript["youtube_id"],
                            "contents": transcript["text"],
                            "document_json": transcript
                        }
                        json.dump(formatted, out_file)
                        out_file.write('\n')

    def run(self):
        self.build_meta_documents()
        self.build_index(self.temp_dir, self.index_dir)
