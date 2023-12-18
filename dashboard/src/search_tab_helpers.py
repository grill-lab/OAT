import jsonlines
import re
import csv


def output_session_features_as_csv(session_list):
    intent_measure = []

    with jsonlines.open('intents.jsonl', mode='w') as writer:
        for session in session_list:
            for interaction in session:
                writer.write(interaction)
    for session in session_list:
        for interaction in range(len(session) - 1):
            measure = {'intent_pred': session[interaction]['intent_pred'][0], 'user': session[interaction]['user'],
                       'system_response': session[interaction]['agent_response'], 'annotation': '',
                       'time': session[interaction]['time']}
            # measure['system'] = session[interaction]['prev_agent']
            intent_measure.append(measure)

    search_measure = []
    for session in session_list:
        for interaction in range(len(session) - 2):
            if 'search' in session[interaction]['intent_pred'][0]:
                measure = {'user': session[interaction]['user'],
                           'search_results': session[interaction + 1]['agent_response'],
                           'time': session[interaction]['time']}
                # measure['system'] = session[interaction]['prev_agent']
                if not re.search('"(.+?)"', session[interaction]['intent_pred'][0]) is None:
                    measure['search_query'] = re.search('"(.+?)"', session[interaction]['intent_pred'][0]).group(1)
                else:
                    measure['search_query'] = ""
                search_measure.append(measure)

    chitchat_measure = []
    for session in session_list:
        for interaction in range(len(session) - 1):
            if 'chit_chat' in session[interaction]['intent_pred'][0]:
                measure = {'user': session[interaction]['user'],
                           'system_response': session[interaction]['agent_response'],
                           'time': session[interaction]['time']}
                # measure['system'] = session[interaction]['prev_agent']
                chitchat_measure.append(measure)

    intent_keys = intent_measure[0].keys()
    search_keys = search_measure[0].keys()
    chitchat_keys = chitchat_measure[0].keys()

    with open('intents.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, intent_keys)
        dict_writer.writeheader()
        dict_writer.writerows(intent_measure)

    with open('search.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, search_keys)
        dict_writer.writeheader()
        dict_writer.writerows(search_measure)

    with open('chitchat.csv', 'w', newline='') as output_file:
        dict_writer = csv.DictWriter(output_file, chitchat_keys)
        dict_writer.writeheader()
        dict_writer.writerows(chitchat_measure)


def get_nothing_count(sessions_list):
    leaving_count = 0
    for session in sessions_list:
        for interaction in range(len(session) - 1):
            intent = session[interaction].get('intent_pred')
            if intent:
                if 'search' in intent[0]:
                    if interaction == len(session) - 2:
                        leaving_count += 1
    return leaving_count, len(sessions_list)


def get_most_common_intents(session_list):
    intents_dict = {}
    search_queries = []

    for session in session_list:
        for interaction in session:
            intents = interaction.get('intent_pred', [])
            if len(intents) > 0:
                intent = re.sub("\(.*?\)", "()", intents[0])
                if intent in intents_dict.keys():
                    intents_dict[intent] += 1
                else:
                    intents_dict[intent] = 1
                search_query = intent[intent.find("(")+1:intent.find(")")]
                search_queries.append(search_query)

    return dict(sorted(intents_dict.items(), key=lambda item: item[1])), search_queries


def get_search_count(session_list):
    search_count = 0
    for session in session_list:
        search_flag = False
        for interaction in range(len(session) - 1):
            intent = session[interaction].get('intent_pred')
            if intent:
                if 'search' in intent[0]:
                    search_flag = True
        if search_flag:
            search_count += 1
    return search_count, len(session_list)


def get_click_through(session_list):
    total_searches = 0
    num_selects = 0
    for session in session_list:
        for interaction in range(len(session) - 1):
            intent = session[interaction].get('intent_pred')
            if intent:
                if 'search' in intent[0]:
                    total_searches += 1
                    next_intent = session[interaction + 1].get('intent_pred')
                    if next_intent:
                        if 'select' in next_intent[0]:
                            num_selects += 1
    return num_selects, total_searches


def get_reformulated_search(session_list):
    total_searches = 0
    new_searches = 0
    for session in session_list:
        for interaction in range(len(session) - 1):
            intent = session[interaction].get('intent_pred')
            if intent:
                if 'search' in intent[0]:
                    total_searches += 1
                    next_intent = session[interaction + 1].get('intent_pred')
                    if next_intent:
                        if 'search' in next_intent[0]:
                            new_searches += 1
    return new_searches, total_searches


def log_intent_parser(sessions_df):
    all_sessions = []
    turns_by_session = sessions_df['turn']
    for turns in turns_by_session:
        session_outputs = []
        for turn in turns:
            turn_output = {}
            agent_response = turn['agent_response']
            user_response = turn['user_request']
            time = agent_response.get('time')

            if time:
                turn_output['time'] = time

            speech_text = agent_response['interaction'].get('speech_text')
            if speech_text:
                turn_output['system'] = speech_text

            param = user_response['interaction'].get('params')
            if param:
                turn_output['intent_pred'] = param

            text = user_response['interaction'].get('text')
            if text:
                turn_output['user'] = text
            session_outputs.append(turn_output)
        all_sessions.append(session_outputs)
    return all_sessions
