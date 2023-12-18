import grpc
import os
import hashlib

from searcher_pb2 import SearchQuery, CandidateList, SearchResults, ScoreCandidateInput
from taskmap_pb2 import Session
from searcher_pb2_grpc import ScoreCandidateStub

from utils import logger, indri_stop_words, jaccard_sim
from pyserini.analysis import Analyzer, get_lucene_analyzer


def get_docid(url):
    """ Generate document unique identifier. """
    return hashlib.md5(url.encode('utf-8')).hexdigest()


class FeatureReRanker:

    def __init__(self):
        self.analyzer = Analyzer(get_lucene_analyzer(stemmer='porter', stopwords=True))
        self.word_tokenizer = Analyzer(get_lucene_analyzer(stemming=False, stopwords=False))
        neural_channel = grpc.insecure_channel(os.environ["NEURAL_FUNCTIONALITIES_URL"])
        self.neural_scorer = ScoreCandidateStub(neural_channel)

        # List of reputable authors.
        with open('/source/searcher/data/good_authors.txt', 'r') as f:
            lines = f.readlines()
            self.good_authors = [line.rstrip().lower() for line in lines]
        # List of reputable domains.
        with open('/source/searcher/data/good_domains.txt', 'r') as f:
            lines = f.readlines()
            self.good_domains = [line.rstrip().lower() for line in lines]
        # List of bad urls.
        with open('/source/searcher/data/bad_urls.txt', 'r') as f:
            lines = f.readlines()
            self.bad_urls = [line.rstrip().lower() for line in lines]

    def __processing(self, sentence: str):
        """ process queries or sections of documents by removing stopwords before sharding / stemming. """
        words = self.word_tokenizer.analyze(sentence)
        new_sentence = " ".join([w for w in words if w not in indri_stop_words])
        return self.analyzer.analyze(new_sentence)

    def re_rank(self, query: SearchQuery, retrieval_result: SearchResults) -> SearchResults:
        """ Re-rank list of taskmaps based on features that maximise probability of taskmap being a
        'good' experience for the user using SophIain features """

        def _process_log_float(f):
            """ Process floats to strings for logging purposes"""
            if isinstance(f, float) or isinstance(f, int):
                return str(round(f, 3))
            else:
                return "0.0"

        logger.info(f"User Query is conversation: {query.text}, last_utterance {query.last_utterance}")
        top_k: int = query.top_k

        utterance_processed = self.__processing(query.last_utterance)

        # L2R weights for linear combination with scores
        category_weights = {
            'neural_score': 22.0,
            'category_score': 18.0
        }

        cooking_weights = {
            'neural_score': 22.0,
            'title_utterance_score': 3.0,
            'requirements_utterance_score': 3.0,
            'tags_utterance_score': 3.0,
            'step_score': 1.0,
            'av_w_steps_score': 0.5,
            'requirements_score': 2.0,
            'rating_score': 0.5,
            'image_score': 3.0,
            'rating_count_score': 1.0,
            'views_score': 0.5,
            'domain_score': 3.0,
            'author_score': 6.0,
            'image_steps_score': 0.0,
            'domain_aligns_score': 0.0,
            'custom_taskmap_score': 0.001,
            'iain2rank_norm_score': 0.0,
            'source_domain_score': 5.0,
            'category_score': 15.0,
            'staged_score': 3.0,
        }

        diy_weights = {
            'neural_score': 22.0,
            'title_utterance_score': 6.0,
            'requirements_utterance_score': 4.0,
            'tags_utterance_score': 3.0,
            'step_score': 1.0,
            'av_w_steps_score': 0.5,
            'requirements_score': 2.0,
            'rating_score': 0.1,
            'image_score': 3.0,
            'rating_count_score': 0.1,
            'views_score': 0.1,
            'domain_score': 1.0,
            'author_score': 0.0,
            'image_steps_score': 0.0,
            'domain_aligns_score': 0.0,
            'custom_taskmap_score': 0.001,
            'iain2rank_norm_score': 0.0,
            'source_domain_score': 0.1,
            'category_score': 18.0,
            'staged_score': 3.0,
        }

        weights = cooking_weights if query.domain == Session.Domain.COOKING else diy_weights

        # Build neural feature
        title_list = []
        for candidate in retrieval_result.candidate_list.candidates:
            title_list.append(getattr(candidate, candidate.WhichOneof('candidate')).title)
        score_candidate_input = ScoreCandidateInput()
        score_candidate_input.query = query.last_utterance
        score_candidate_input.title.extend(title_list)
        score_candidate_output = self.neural_scorer.score_candidate(score_candidate_input)

        # --- group candidates ---
        l2r_candidates_temp = []
        i = 0
        fastrank_l2r_rows = []
        max_l2r_score = None
        min_l2r_score = None
        for candidate in retrieval_result.candidate_list.candidates:
            l2r_score = 0.0
            if candidate.HasField('category'):
                l2r_score += category_weights['neural_score'] * score_candidate_output.score[i]
                l2r_score += weights['category_score']
                i += 1
                l2r_candidates_temp.append((candidate, l2r_score))
                continue

            candidate_union = candidate
            candidate = candidate.task

            # >>> depending on domain classification, rank search results from certain scores more

            if query.domain == Session.Domain.COOKING:
                if candidate.domain_name.lower() in ['seriouseats', 'wholefoodmarket', 'wholefoodsmarket',
                                                     'wholefoods']:
                    l2r_score += weights['source_domain_score'] * 1

            # >>> title text similarity (neural) <<<
            neural_score = score_candidate_output.score[i]
            l2r_score += weights['neural_score'] * neural_score

            # >>> title text similarity (jaccard) <<<
            title_processed = self.__processing(candidate.title)
            title_utterance_score = jaccard_sim(utterance_processed, title_processed)
            l2r_score += weights['title_utterance_score'] * title_utterance_score

            # >>> requirements text similarity (jaccard)  <<<
            requirements_processed = self.__processing(" ".join([r.name for r in candidate.requirement_list]))
            requirements_utterance_score = jaccard_sim(utterance_processed, requirements_processed)
            l2r_score += weights['requirements_utterance_score'] * requirements_utterance_score

            # >>> tag text similarity (jaccard)  <<<
            tags_processed = self.__processing(" ".join(candidate.tags))
            tags_utterance_score = jaccard_sim(utterance_processed, tags_processed)
            l2r_score += weights['tags_utterance_score'] * tags_utterance_score

            # >>> step count <<<
            num_steps = len(candidate.steps)
            if num_steps < 4:
                step_score = 0.5
            elif 4 <= num_steps < 10:
                step_score = 1.0
            elif 10 <= num_steps < 15:
                step_score = 0.7
            elif 15 <= num_steps < 20:
                step_score = 0.4
            else:
                step_score = 0.0
            l2r_score += weights['step_score'] * step_score

            # >>> average words in step <<<
            w_steps = [len(s.response.speech_text.split(" ")) for s in candidate.steps]
            av_w_steps = sum(w_steps) / len(w_steps)
            if av_w_steps < 5:
                av_w_steps_score = 0.5
            elif 5 <= av_w_steps < 20:
                av_w_steps_score = 1.0
            elif 20 <= av_w_steps < 30:
                av_w_steps_score = 0.7
            elif 30 <= av_w_steps < 40:
                av_w_steps_score = 0.25
            else:
                av_w_steps_score = 0.0
            l2r_score += weights['av_w_steps_score'] * av_w_steps_score

            # >>> requirement count <<<
            num_requirements = len(candidate.requirement_list)
            if num_requirements < 4:
                requirements_score = 0.5
            elif 4 <= num_requirements < 8:
                requirements_score = 1.0
            elif 8 <= num_steps < 12:
                requirements_score = 0.7
            elif 12 <= num_steps < 16:
                requirements_score = 0.5
            else:
                requirements_score = 0.0
            l2r_score += weights['requirements_score'] * requirements_score

            # >>> quality rating <<<
            rating_score = float(candidate.rating_out_100) / 100 if candidate.rating_out_100 else 0.35
            l2r_score += weights['rating_score'] * rating_score

            # >>> has image <<<
            image_score = 1.0 if candidate.thumbnail_url and "https://oat-2-data.s3.amazonaws.com/" != candidate.thumbnail_url else 0.0
            l2r_score += weights['image_score'] * image_score

            # >>> rating count <<<
            rating_count = candidate.rating_count
            if rating_count == 0:
                rating_count_score = 0.0
            elif 1 <= rating_count < 25:
                rating_count_score = 0.2
            elif 25 <= num_steps < 100:
                rating_count_score = 0.4
            elif 100 <= num_steps < 250:
                rating_count_score = 0.6
            else:
                rating_count_score = 1.0
            l2r_score += weights['rating_count_score'] * rating_count_score

            # >>> views <<<
            views = candidate.rating_count
            if views == 0:
                views_score = 0.0
            elif 1 <= views < 100:
                views_score = 0.2
            elif 100 <= views < 1000:
                views_score = 0.4
            elif 1000 <= views < 10000:
                views_score = 0.6
            else:
                views_score = 1.0
            l2r_score += weights['views_score'] * views_score

            # >>> reputable domain <<<
            domain_score = 1.0 if any(d in str(candidate.domain_name).lower() for d in self.good_domains) else 0.0
            l2r_score += weights['domain_score'] * domain_score

            # >>> promote staged <<<
            staged_score = 1.0 if "staged" in candidate.dataset else 0.0
            l2r_score += weights['staged_score'] * staged_score

            # >>> reputable author <<<
            author_score = 1.0 if candidate.author.lower() in self.good_authors else 0.0
            if candidate.author.lower() in self.good_authors:
                logger.info(f'GOOD AUTHOR: {candidate.author}')
            l2r_score += weights['author_score'] * author_score

            # Append L2R score with candidate taskmap
            l2r_candidates_temp.append((candidate_union, l2r_score))

            i += 1

            # set st start
            if not max_l2r_score:
                max_l2r_score = l2r_score
            if not min_l2r_score:
                min_l2r_score = l2r_score

            # set st start
            if max_l2r_score < l2r_score:
                max_l2r_score = l2r_score
            if min_l2r_score > l2r_score:
                min_l2r_score = l2r_score

        l2r_candidates = []
        for candidates, l2r_score in l2r_candidates_temp:
            l2r_candidates.append((candidates, l2r_score))
        # Sort by l2r_score and select top_k highest.
        sorted_candidates = sorted(l2r_candidates, key=lambda x: x[1], reverse=True)

        taskmap_ids = [get_docid(c[0].task.source_url) for c in sorted_candidates]
        duplicate_taskmap_ids = list(set([i for i in taskmap_ids if taskmap_ids.count(i) > 1]))

        author_domain_pairs = [(c[0].task.domain_name, c[0].task.author) for c in sorted_candidates
                               if c[0].task.author != ""]
        duplicates = list(set([i for i in author_domain_pairs if author_domain_pairs.count(i) > 1]))

        # deduplication and diversification
        API_data = {}
        filtered_candidates = []
        already_seen_domains_names = []

        for candidate, l2r_score in sorted_candidates:
            task = candidate.task
            # don't include bad urls
            if task.source_url in self.bad_urls:
                continue
            # don't include API duplicates of index results
            elif get_docid(task.source_url) in duplicate_taskmap_ids or any(
                    str(task.author).lower() == author.lower() for domain, author in duplicates):
                if task.dataset == 'API':
                    API_data[get_docid(task.source_url)] = {
                        "thumbnail_url": task.thumbnail_url,
                        "serves": task.serves,
                        "difficulty": task.difficulty
                    }
                else:
                    filtered_candidates.append((candidate, l2r_score))
                    if Session.Domain.COOKING:
                        already_seen_domains_names.append(task.domain_name)
            # COOKING task diversification - skip domain names that are not great that we have seen before
            elif task.domain_name in already_seen_domains_names and Session.Domain.COOKING:
                continue
            else:
                filtered_candidates.append((candidate, l2r_score))
                already_seen_domains_names.append(task.domain_name)

        new_sorted_candidates = []
        categories_count = 0
        for idx in range(len(filtered_candidates)):
            if not filtered_candidates[idx][0].HasField('category') or not categories_count >= 1:
                new_sorted_candidates.append(filtered_candidates[idx])
            if filtered_candidates[idx][0].HasField('category'):
                categories_count += 1

        filtered_candidates = new_sorted_candidates

        for idx in range(2):
            if idx < len(filtered_candidates) - 1 and filtered_candidates[idx][0].HasField('category'):
                filtered_candidates[idx], filtered_candidates[idx + 1] = filtered_candidates[idx + 1], \
                    filtered_candidates[idx]

        logger.info('--- SophIain 2Rank scores ---')
        for candidate, l2r_score in filtered_candidates[:9]:
            title = getattr(candidate, candidate.WhichOneof('candidate')).title
            cat_or_task = type(getattr(candidate, candidate.WhichOneof('candidate')))
            if 'TaskMap' in str(cat_or_task):
                dataset = candidate.task.dataset
                domain = candidate.task.domain_name
                author = candidate.task.author
                logger.info(f'{title}: {round(l2r_score, 3)} from {dataset} by {author} '
                            f'from domain: {domain}, type: {cat_or_task}')
            else:
                logger.info(f'{title}: {round(l2r_score, 3)}, type: {cat_or_task}')

        # Init TaskMapList.
        candidate_list: CandidateList = CandidateList()
        for candidate, l2r_score in filtered_candidates[:9]:
            doc_id = get_docid(candidate.task.source_url)

            # augment index match with API match data for specific fields
            API_match = API_data.get(doc_id, None)
            if API_match is not None:
                logger.info(API_match)
                candidate.task.thumbnail_url = API_match["thumbnail_url"]
                candidate.task.serves = API_match["serves"]
                candidate.task.difficulty = API_match["difficulty"]

            candidate_list.candidates.append(candidate)

        # Search results
        search_results = SearchResults()
        search_results.candidate_list.MergeFrom(candidate_list)

        return search_results
