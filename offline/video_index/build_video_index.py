import json
import os
import shutil
import sys

from .video_convertor import VideoConvertor
from compiled_protobufs.video_document_pb2 import VideoDocument
from google.protobuf.json_format import MessageToDict

from utils import get_file_system, Downloader
from index_builders import build_json_docs, write_protobuf_list_to_file
from index_builders import PyseriniBM25Builder

sys.path.insert(0, '/video_index')


class VideoIndexBuilder(PyseriniBM25Builder):
    """ Class that runs the video document generation process and builds index. """

    def __init__(self, temp_metadata: str, index_dir: str):
        # Unpack config_dict.
        self.version = "0.1_test"
        self.file_system_path = get_file_system()
        artefact_id = "video_metadata"
        downloader = Downloader()
        downloader.download([artefact_id])
        self.video_metadata_dir = downloader.get_artefact_path(artefact_id)
        self.video_metadata_temp_dir = temp_metadata
        self.version = "test_video_corpus"
        self.dataset_name = 'custom'
        self.k = 5000
        self.Convertor = VideoConvertor
        self.index_dir = index_dir

        # remove the temp video directory if it exists
        if os.path.isdir(temp_metadata):
            shutil.rmtree(temp_metadata)
        os.makedirs(temp_metadata, exist_ok=True)

        # index folder
        if not os.path.isdir(index_dir):
            os.makedirs(index_dir, exist_ok=True)

    @staticmethod
    def parse(proto_message):
        """ Extract text content from proto. """
        contents = ''
        contents += proto_message.title + '. '
        contents += proto_message.uploader + '. '
        contents += proto_message.description + '. '
        contents += proto_message.subtitles + ''
        return contents.replace('\n', '')

    def build_doc(self, proto_message, include_proto):
        """ Build pyserini document from taskmap message. """
        contents = self.parse(proto_message)

        if include_proto:
            return {
                "id": proto_message.doc_id,
                "contents": contents,
                "document_json": MessageToDict(proto_message),
            }
        else:
            return {
                "id": proto_message.doc_id,
                "contents": contents,
            }

    def write_to_file(self, doc_list, chunk_counter, video_source='', temp_dir='/temp'):
        if len(doc_list) > 0:
            # Write chunk of taskmaps to file.
            print('---------------------')
            print(f'len: {len(doc_list)}')
            path = os.path.join(temp_dir, f'video_{video_source}_{chunk_counter}.bin')
            print(f'writing taskmaps to file:{path}')

            write_protobuf_list_to_file(path=path, protobuf_list=doc_list)
            chunk_counter += 1
        return chunk_counter

    def convert_json_to_video(self, meta_list, hosted_folder, DATASET = 'downloaded'):
        taskmap_list = []
        for video in meta_list:
            subtitles = ''
            if video.get('subtitles'):
                subtitles = video.get('subtitles')
            hosted_mp4 = f'https://youtube-video-corpus.s3.amazonaws.com/{hosted_folder}/{video["id"]}.mp4'
            video_doc = self.Convertor(DATASET).build_video_document(title=video['title'], uploader=video['uploader'],
                                                                     views=video['views'], duration=video['duration'],
                                                                     description=video['description'], hosted_mp4=hosted_mp4,
                                                                     subtitles=subtitles, youtube_id=video["id"])
            taskmap_list.append(video_doc)

        self.write_to_file(doc_list=taskmap_list, chunk_counter=0, video_source=hosted_folder,
                           temp_dir=self.video_metadata_temp_dir)

    def build_meta_documents(self):
        """ Generate folder of taskmaps stored within binary files for meta data """
        print('*** building meta data video documents ***')

        # mapping metadata scripts to where the videos are hosted on S3
        hosted_path_dic = {"meta_data_cooking.json": "food_videos",
                           "meta_data_diy.json": "diy_videos",
                           "meta_data_how_tos.json": "how_to_videos"}

        files = os.listdir(self.video_metadata_dir)
        for file in files:
            meta_list = []
            with open(f"{self.video_metadata_dir}/{file}") as json_file:
                for line in json_file.readlines():
                    meta_list.append(json.loads(line))
            self.convert_json_to_video(meta_list, hosted_path_dic[file])

    def run(self):
        temp_dir = os.path.join(get_file_system(), 'temp')

        # convert the video document protos into .bin files
        self.build_meta_documents()

        build_json_docs(input_dir=self.video_metadata_temp_dir, output_dir=temp_dir, proto_message=VideoDocument,
                        include_proto=True, build_doc_function=self.build_doc)
        self.build_index(temp_dir, self.index_dir)
