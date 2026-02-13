import logging
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

class DatabasePersistence:
    def __init__(self):
        pass

    @contextmanager
    def _database_connect(self):
        connection = psycopg2.connect(dbname='todolist')

        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def all_lists(self):
        query = 'SELECT * FROM lists'
        logger.info('Executing query: %s', query)

        with self._database_connect() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()

        lists = [dict(result) for result in results]

        for lst in lists:
            lst.setdefault('todos', [])

        return lists

    def find_list(self, list_id):
        query = '''
                SELECT * FROM lists
                WHERE id = %s
                '''
        logger.info("Executing query: %s with list_id: %s", query, list_id)

        with self._database_connect() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(query, (list_id,))
                lst = dict(cursor.fetchone())

        lst.setdefault('todos', [])

        return lst

    def create_new_list(self, title):
        pass

    def rename_list_by_id(self, list_id, new_title):
        pass

    def delete_list(self, list_id):
        pass

    def create_new_todo(self, list_id, todo_name):
        pass

    def toggle_todo_completion(self, list_id, todo_id, status):
        pass

    def delete_todo_from_list(self, lst, todo):
        pass

    def toggle_all_todo_completion(self, lst):
        pass

    def reorder_todo_item(self, lst, todo, direction):
        pass


