import logging
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from functools import wraps
from flask import (
                    abort,
                    g,
                    )

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Helper Functions
def require_todo_exists(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        todo_id = kwargs.get('todo_id')
        if not g.storage.todo_exists(todo_id):
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

def require_list_exists(f):
    pass

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

    def todo_exists(self, todo_id):
        query = '''
                SELECT 1 FROM todos
                WHERE id = %s;
                '''
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info('''
                            Executing query: %s with todo_id: %s
                            ''',
                            query, todo_id)

                cursor.execute(query, (todo_id,))

                row = cursor.fetchone()

        return row is not None

    def list_exists(self, list_id):
        pass

    def all_lists(self):
        query = 'SELECT * FROM lists'
        logger.info('Executing query: %s', query)

        with self._database_connect() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()

        lists = [dict(result) for result in results]

        for lst in lists:
            todos = self._find_todos_for_list(lst['id'])
            lst.setdefault('todos', todos)

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

        todos = self._find_todos_for_list(list_id)
        lst.setdefault('todos', todos)

        return lst

    def _find_todos_for_list(self, list_id):
        query = '''
                SELECT * FROM todos
                WHERE list_id = %s
                ORDER BY position
                '''
        logger.info('Executing query: %s with list_id: %s', query, list_id)
        with self._database_connect() as connection:
            with connection.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute(query, (list_id,))
                return cursor.fetchall()

    def create_new_list(self, title):
        query = '''
                INSERT INTO lists (title)
                values (%s)
                '''
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info(
                        'Executing query: %s with title: %s',
                        query, title
                        )
                cursor.execute(query, (title,))

    def rename_list_by_id(self, list_id, new_title):
        query = '''
                UPDATE lists
                SET title = %s
                WHERE id = %s
                '''
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info('''
                            Executing query: %s with list_id: %s
                            ''',
                            query, list_id)

                cursor.execute(query, (new_title, list_id,))


    def delete_list(self, list_id):
        query = '''
                DELETE FROM lists
                WHERE id = %s
                '''
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info('''
                            Executing query: %s with list_id: %s
                            ''',
                            query, list_id)

                cursor.execute(query, (list_id,))

    def create_new_todo(self, list_id, title):
        query = '''
                INSERT INTO todos (title, list_id, position)
                values (
                    %s,
                    %s,
                    (SELECT COALESCE(MAX(position), 0) + 1 FROM todos
                    WHERE list_id = %s)
                );
                '''

        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info(
                        'Executing query: %s with list_id: %s, and title: %s',
                        query, list_id, title
                        )
                cursor.execute(query, (title, list_id, list_id))

    def toggle_todo_completion(self, todo_id, status):
        query = '''
                UPDATE todos
                SET completed = %s
                WHERE id = %s;
                '''

        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info(
                        'Executing query: %s with todo_id: %s, and status: %s',
                        query, todo_id, status
                        )
                cursor.execute(query, (status, todo_id,))

    def toggle_all_todo_completion(self, list_id):
        query = '''
                UPDATE todos
                SET completed = CASE
                    WHEN EXISTS (
                        SELECT 1 FROM todos
                        WHERE list_id = %s and completed = false
                    ) THEN true
                    ELSE false
                END
                WHERE list_id = %s;
                '''

        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info(
                        'Executing query: %s with list_id: %s',
                        query, list_id
                        )
                cursor.execute(query, (list_id, list_id,))

    def delete_todo_from_list(self, todo_id):
        query = '''
                DELETE FROM todos
                WHERE id = %s
                '''
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info('''
                            Executing query: %s with todo_id: %s
                            ''',
                            query, todo_id)

                cursor.execute(query, (todo_id,))

    def reorder_todo_item(self, lst, todo, direction):
        current_position = todo['position']

        if direction == 'up':
            target_position = current_position - 1

            if target_position < 1:
                return

        elif direction == 'down':
            target_position = current_position + 1

            with self._database_connect() as connection:
                with connection.cursor() as cursor:
                    query = '''
                            SELECT COALESCE(MAX(position), 0) FROM todos
                            WHERE list_id = %s;
                            '''
                    logger.info('''
                                Executing query: %s with list_id: %s
                                ''',
                                query, lst['id'])
                    cursor.execute(query, (lst['id'],))

                    max_position = cursor.fetchone()[0]

            if target_position > max_position:
                return

        temp_update_query = '''
                            UPDATE todos
                            SET position = -1
                            WHERE id = %s;
                            '''
        swap_partner_query = '''
                            UPDATE todos
                            SET position = %s
                            WHERE list_id = %s AND position = %s;
                            '''
        set_todo_query = '''
                            UPDATE todos
                            SET position = %s
                            WHERE id = %s;
                        '''

        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info(
                            'Executing query: %s with todo id: %s',
                            temp_update_query, todo['id']
                            )
                cursor.execute(temp_update_query, (todo['id'],))

                logger.info('''
                            Executing query: %s with list_id: %s
                            and target_position: %s
                            ''',
                            swap_partner_query, lst['id'], target_position)
                cursor.execute(swap_partner_query,
                                (
                                    current_position, lst['id'], target_position
                                )
                            )

                logger.info(
                            'Executing query: %s with todo id: %s',
                            set_todo_query, todo['id']
                            )
                cursor.execute(set_todo_query, (target_position, todo['id']))