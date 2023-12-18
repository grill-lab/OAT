import requests
from datetime import datetime

from offline_pb2 import HTMLDocument


def url_to_html(url):
    return requests.get(url).text


class Converter:

    def __init__(self, parsers):
        self.task_graph = None
        self.html = None
        self.url = None
        self.parsers = parsers

    def convert_urls(self, url):
        self.url = url
        self.html = url_to_html(url)
        self.task_graph = self.__html_to_taskgraph(url, self.html)

    def convert_htmls(self, url, html):
        self.task_graph = self.__html_to_taskgraph(url, html)

    def __html_to_taskgraph(self, url, html):
        for parser_config in self.parsers:
            if parser_config["file_path"] in url:
                parser = parser_config["parser"]()
                return parser.parse(url, html)
        else:
            return

    def get_taskgraph_proto(self):
        if self.task_graph is not None:
            return self.task_graph.to_proto()

    def get_html_proto(self):
        html_proto = HTMLDocument()
        setattr(html_proto, "html", self.html)
        setattr(html_proto, "url", self.url)
        today_date = datetime.today().strftime('%Y-%m-%d')
        setattr(html_proto, "date_retrieved", today_date)
        return html_proto
