import whisper
import torch
import os
import subprocess

from utils import logger, get_file_system
from video_index.video_metadata_searcher import VideoSearcher
from video_index.transcription_searcher import TranscriptRetriever
from taskmap_pb2 import Video, TaskMap, ExecutionStep
from video_document_pb2 import VideoDocument
from .abstract_step_augmenter import AbstractBatchStepAugmenter

from sentence_transformers import SentenceTransformer, util
from typing import Dict


class AudioVideoStepAlignment(AbstractBatchStepAugmenter):

    def __init__(self):
        super().__init__()
        all_indices_dir = os.path.join(get_file_system(), 'offline', 'system_indexes')
        if os.path.isdir(os.path.join(all_indices_dir, 'video-index_dense')):
            self.searcher = VideoSearcher(video_index_path=f'{all_indices_dir}/video_index-simple',
                                          video_dense_index_path=f'{all_indices_dir}/video-index_dense')
        else:
            if not os.path.isdir(os.path.join(get_file_system(), f'{all_indices_dir}/video_index-simple')):
                logger.warning("Video index not found, can't run this augmenter!")
                exit(1)
            self.searcher = VideoSearcher(video_index_path=f'{all_indices_dir}/video_index-simple')
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.transcript_searcher = TranscriptRetriever(transcript_index_path=f"{all_indices_dir}/audio_index")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2', cache_folder="/shared/file_system/models/1_Pooling",
                                            device=self.device).to(self.device)

        self.auto_transcribe = False
        if self.auto_transcribe:
            logger.info('Auto transcribe set to True')
            self.whisper_model = whisper.load_model("base").to(self.device)
            self.audio_temp_dir = os.path.join(get_file_system(), 'temp_audio')
            if not os.path.isdir(self.audio_temp_dir):
                os.makedirs(self.audio_temp_dir, exist_ok=True)

        logger.info('Finished loading all audio step text alignment models')

    def condition(self, step: ExecutionStep) -> bool:
        if step.response.screen.video.title == "":
            return True
        return False

    def batch_process(self, batch):
        """ Handle the GPU processing of finding relevant videos and the best matching segments for steps.
            First, we gather the input for the embeddings. `step_input_list` contains the step_texts, and
            `video_segments_input_list` contains the video segments.
            We then embed those

        """
        step_input_list = []        # storing step inputs for embeddings
        hash_vals = []              # storing step hash vals
        video_segments_meta = {}    # storing {video.doc_id: video_segments}
        video_matches = {}          # {step hash val: matched video}

        # start gathering inputs for both step texts and video segments to generate embeddings
        for (hash_val, step, taskmap_title) in batch:
            hash_vals.append(hash_val)
            step_text = step.response.speech_text
            search_query = f'{taskmap_title}. {step_text}'
            video = self.search_video(search_query)
            video_matches[hash_val] = video
            if video is not None and not video_segments_meta.get(video.doc_id):
                if video:
                    video_segments = self.retrieve_whisper_captions(video)
                    video_segments_meta[video.doc_id] = video_segments

            step_input_list.append(step_text)

        video_pos = {}                      # position of specific video segments within the video embeddings list
        video_segments_input_list = []      # storing video embeddings

        for video_id in list(video_segments_meta.keys()):
            start_pos = len(video_segments_input_list)
            end_pos = start_pos + len(video_segments_meta[video_id])
            video_pos[video_id] = {'start_pos': start_pos, 'end_pos': end_pos}
            if len(video_segments_meta[video_id]) > 0:
                video_segments_input_list.extend([seg['text'] for seg in video_segments_meta[video_id]])

        # generate both step and video embeddings
        step_text_embeddings = self.embedder.encode(step_input_list, convert_to_tensor=True,
                                                    batch_size=128, show_progress_bar=True)
        video_segments_embeddings = self.embedder.encode(video_segments_input_list, convert_to_tensor=True,
                                                         batch_size=128, show_progress_bar=True)

        # assemble the embeddings and find the best matching segment for each step text
        relevant_videos = []        # output list to store results for video embeddings
        for step_embedding, hash_val in zip(step_text_embeddings, hash_vals):
            if video_matches[hash_val] is None:
                relevant_videos.append(None)
                continue
            matched_video_id = video_matches[hash_val].doc_id
            start_pos, end_pos = video_pos[matched_video_id]['start_pos'], video_pos[matched_video_id]['end_pos']
            assert len(video_segments_embeddings[start_pos:end_pos]) == len(video_segments_meta[matched_video_id]), \
                "No of video embeddings does not match number of retrieved video segments by Whisper"
            similarity_scores = util.cos_sim(step_embedding, video_segments_embeddings[start_pos:end_pos])[0]
            sorted_idxs = similarity_scores.argsort(descending=True)

            if len(video_segments_meta[matched_video_id]) > 0:
                best_match_idx = sorted_idxs[0]
                best_ranked_video_seg = video_segments_meta[matched_video_id][best_match_idx]
                score = similarity_scores[best_match_idx]

                if score > 0.5:
                    relevant_video = video_matches[hash_val]
                    relevant_videos.append((relevant_video, best_ranked_video_seg))
                else:
                    relevant_videos.append(None)
            else:
                relevant_videos.append(None)

        assert len(relevant_videos) == len(step_input_list), "No of relevant videos did not match no of input steps"

        return relevant_videos

    def get_transformed_input(self, task_graph: TaskMap):
        return task_graph.title

    def apply_output(self, step: ExecutionStep, processed_output) -> ExecutionStep:
        video_doc, video_segment = processed_output
        logger.info(f'Step text: "{step.response.speech_text}" aligned to video: "{video_doc.title}" '
                    f'with chosen segment: "{video_segment["text"]}"')

        video: Video = Video()
        video.title = video_doc.title
        video.doc_id = video_doc.doc_id
        video.hosted_mp4 = video_doc.hosted_mp4
        video.start_time = video_segment['start']
        video.end_time = video_segment['end']

        step.response.screen.video.MergeFrom(video)

        return step

    def __convert_video_to_audio(self, video_result) -> int:
        video_name = video_result.doc_id
        audio_path = os.path.join(self.audio_temp_dir, f'{video_name}.mp3')
        video_path = video_result.hosted_mp4
        if f'{video_name}.mp3' not in os.listdir(self.audio_temp_dir):
            result = subprocess.run(["ffmpeg", "-i", video_path, audio_path, '-hide_banner', '-loglevel', 'error'])
            return result.returncode
        else:
            return 0

    def __whisper_transcribe_video(self, video_result) -> Dict:
        if video_result.youtube_id != "":
            video_name = video_result.youtube_id
        else:
            video_name = video_result.doc_id
        audio_path = os.path.join(self.audio_temp_dir, f'{video_name}.mp3')
        success = self.__convert_video_to_audio(video_result)
        logger.info(f'Converting to audio success code: {success}')
        if success == 0:
            logger.info(f'Started transcribing...: {video_result.hosted_mp4}')
            transcript = self.whisper_model.transcribe(audio_path)
            return transcript

    def retrieve_whisper_captions(self, video_result) -> list:
        # search for YouTube id in whisper captions index
        transcript = self.transcript_searcher.retrieve_transcript(video_result.youtube_id)
        video_steps = []

        # if not found in pre-transcribed video index transcribe
        if not transcript:
            logger.info('Matched video not transcribed by whisper')
            if self.auto_transcribe:
                transcript = self.__whisper_transcribe_video(video_result)

        if transcript:
            for seg in transcript['segments']:
                video_steps.append({'text': seg['text'], 'start': seg['start'], 'end': seg['end']})

        return video_steps

    def search_video(self, step_text):
        video_result: VideoDocument = self.searcher.search_video(step_text)
        if video_result:
            if video_result.title is not None:
                return video_result
        else:
            return None
