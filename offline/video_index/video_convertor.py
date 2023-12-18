import sys

from compiled_protobufs.video_document_pb2 import VideoDocument

sys.path.insert(0, '../data')
sys.path.insert(0, '../data/shared')
sys.path.insert(0, '../data/shared/task_graph')
sys.path.insert(0, '../data/shared/compiled_protobufs')


def get_taskmap_id(doc_type, dataset, url) -> str:
    """ Generate taskmap_id using MD5 hash. """
    import hashlib
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return doc_type + '+' + dataset + '+' + md5
    

class VideoConvertor:
    DOC_TYPE = 'video'

    def __init__(self, data_set):
        self.data_set = data_set

    def update_video_doc(self, document, video_doc: VideoDocument) -> VideoDocument:
        """ Add Wikihow attributes to task_graph. """

        # Taskmap ID
        url = str(document.url)
        video_id = get_taskmap_id(doc_type=self.DOC_TYPE, dataset=self.data_set, url=document.url)
        video_doc.doc_id = video_id

        # wikihow article URL
        if url:
            video_doc.url = url

        # Title
        if document.title:
            video_doc.title = str(document.title)

        # Video
        if document.video:
            video_doc.video_url = document.video

        return video_doc

    def build_video_document(self, title="", url="", image="", hosted_mp4='', uploader='',
                             views=0, duration=0, description='', youtube_id='', subtitles=''):
        video_doc = VideoDocument()
        video_id = get_taskmap_id(doc_type=self.DOC_TYPE, dataset=self.data_set, url=youtube_id)
        video_doc.doc_id = video_id
        video_doc.url = url
        video_doc.title = str(title)
        video_doc.thumbnail = image
        video_doc.hosted_mp4 = hosted_mp4
        video_doc.uploader = uploader
        if views != 0:
            video_doc.views = views
        if duration != 0:
            video_doc.duration = duration
        video_doc.description = description
        video_doc.youtube_id = youtube_id
        video_doc.subtitles = subtitles
        return video_doc
