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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        list_id = kwargs.get('list_id')
        if not g.storage.list_exists(list_id):
            abort(404)
        return f(*args, **kwargs)
    return decorated_function

class DatabasePersistence:
    def __init__(self):
        self._setup_schema()

    def _setup_schema(self):
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute('''
                                SELECT COUNT(*)
                                FROM information_schema.tables
                                WHERE table_schema = 'public'
                                    and table_name = 'lists';
                                ''')
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                                    CREATE TABLE lists (
                                    id SERIAL PRIMARY KEY,
                                    title VARCHAR(100) UNIQUE NOT NULL
                                    );
                                ''')

                cursor.execute('''
                            SELECT COUNT(*)
                            FROM information_schema.tables
                            WHERE table_schema = 'public'
                                and table_name = 'todos';
                            ''')

                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                                    CREATE TABLE todos (
                                    id SERIAL PRIMARY KEY,
                                    title VARCHAR(100) NOT NULL,
                                    completed BOOLEAN NOT NULL DEFAULT FALSE,
                                    list_id INTEGER NOT NULL
                                        REFERENCES lists(id) ON DELETE CASCADE,
                                    position_idx INTEGER NOT NULL,
                                    unique(list_id, position_idx)
                                    );
                                ''')

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
        query = '''
                SELECT 1 FROM lists
                WHERE id = %s;
                '''
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                logger.info('''
                            Executing query: %s with list_id: %s
                            ''',
                            query, list_id)

                cursor.execute(query, (list_id,))

                row = cursor.fetchone()

        return row is not None

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
        logger.info('Executing query: %s with list_id: %s', query, list_id)

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
                ORDER BY position_idx
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
                INSERT INTO todos (title, list_id, position_idx)
                values (
                    %s,
                    %s,
                    (SELECT COALESCE(MAX(position_idx), 0) + 1 FROM todos
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

    def reorder_todo_item(self, list_id, todo_id, direction):
        with self._database_connect() as connection:
            with connection.cursor() as cursor:
                position_query = '''
                        SELECT position_idx FROM todos
                        WHERE list_id = %s and id = %s;
                        '''
                logger.info('''
                            Executing query: %s with list_id: %s,
                            and todo_id: %s
                            ''',
                            position_query, list_id, todo_id)
                cursor.execute(position_query, (list_id, todo_id))

                row = cursor.fetchone()

                if not row:
                    return

                current_position = row[0]

                if direction == 'up':
                    target_position = current_position - 1
                elif direction == 'down':
                    target_position = current_position + 1
                else:
                    return

                if target_position < 1:
                    return

                max_position_query = '''
                        SELECT COALESCE(MAX(position_idx), 0) FROM todos
                        WHERE list_id = %s;
                        '''
                logger.info('''
                            Executing query: %s with list_id: %s
                            ''',
                            max_position_query, list_id)
                cursor.execute(max_position_query, (list_id,))

                max_position = cursor.fetchone()[0]

                if target_position > max_position:
                    return

                temp_update_query = '''
                                    UPDATE todos
                                    SET position_idx = -1
                                    WHERE id = %s;
                                    '''
                swap_partner_query = '''
                                    UPDATE todos
                                    SET position_idx = %s
                                    WHERE list_id = %s AND position_idx = %s;
                                    '''
                set_todo_query = '''
                                    UPDATE todos
                                    SET position_idx = %s
                                    WHERE id = %s;
                                '''

                logger.info(
                            'Executing query: %s with todo id: %s',
                            temp_update_query, todo_id
                            )
                cursor.execute(temp_update_query, (todo_id,))

                logger.info('''
                            Executing query: %s with list_id: %s
                            and target_position: %s
                            ''',
                            swap_partner_query, list_id, target_position)
                cursor.execute(swap_partner_query,
                                (
                                    current_position, list_id, target_position
                                )
                            )

                logger.info(
                            'Executing query: %s with todo id: %s',
                            set_todo_query, todo_id
                            )
                cursor.execute(set_todo_query, (target_position, todo_id))