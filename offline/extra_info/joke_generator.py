import sqlite3
from utils import logger

import sys
import os
sys.path.insert(0, '/shared')

from extra_info.abstract_generator import AbstractGenerator

from utils import get_file_system

class JokeGenerator(AbstractGenerator):
    
    def __init__(self):
        conn = sqlite3.connect(os.path.join(get_file_system(), 'offline', 'extra_info_data', 'jokes_database.db'))
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            joke TEXT UNIQUE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS joke_keywords (
            joke_id INTEGER,
            keyword_id INTEGER,
            FOREIGN KEY (joke_id) REFERENCES jokes(id),
            FOREIGN KEY (keyword_id) REFERENCES keywords(id)
        )
        """)

        conn.close()
    
    def run(self):
        conn = sqlite3.connect(os.path.join(get_file_system(), 'offline', 'extra_info_data', 'jokes_database.db'))
        cursor = conn.cursor()
        logger.info("Running the generation")
        self.add_initial_corpus()
        conn.close()
    
    def add_initial_corpus(self):
        conn = sqlite3.connect(os.path.join(get_file_system(), 'offline', 'extra_info_data', 'jokes_database.db'))
        cursor = conn.cursor()

        f = open(os.path.join(get_file_system(), 'offline/extra_info_data/jokes.txt'), 'r')
        for joke in f:
            if joke != '\n':
                self.add_joke(joke.strip('\n'))
                
        f.close()
        conn.close()
    
    def add_joke(self, joke):
        conn = sqlite3.connect(os.path.join(get_file_system(), 'offline', 'extra_info_data', 'jokes_database.db'))
        cursor = conn.cursor()
        joke = super().filter_joke(joke)
        
        if joke != None:
            keywords = super().get_keywords(joke)
            cursor.execute("INSERT OR IGNORE INTO jokes (joke) VALUES (?)", (joke,))
            logger.info("Joke was added to the database " + joke)
            logger.info("Keywords are " + str(keywords))
            joke_id = cursor.lastrowid
            for keyword in keywords:
                cursor.execute("SELECT id FROM keywords WHERE keyword=?", (keyword,))
                keyword_id = cursor.fetchone()
                if keyword_id is None:
                    cursor.execute("INSERT INTO keywords (keyword) VALUES (?)", (keyword,))
                    keyword_id = cursor.lastrowid
                else:
                    keyword_id = keyword_id[0]
                cursor.execute("INSERT INTO joke_keywords (joke_id, keyword_id) VALUES (?,?)", (joke_id, keyword_id))
            conn.commit()
        conn.close()

    def get_jokes_by_keyword(self, keyword):
        conn = sqlite3.connect(os.path.join(get_file_system(), 'offline', 'extra_info_data', 'jokes_database.db'))
        cursor = conn.cursor()
        cursor.execute("""
        SELECT joke FROM jokes
        JOIN joke_keywords ON jokes.id=joke_keywords.joke_id
        JOIN keywords ON keywords.id=joke_keywords.keyword_id
        WHERE keyword=?
        """, (keyword,))

        joke_set = set([joke[0] for joke in cursor.fetchall()])

        conn.commit()
        conn.close()
        
        return joke_set
    