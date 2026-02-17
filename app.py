from uuid import uuid4
from functools import wraps
import os
import secrets
from flask import (
                    abort,
                    flash,
                    Flask,
                    redirect,
                    render_template,
                    request,
                    url_for,
                    g,
                    )
from todos.utils import (
                        error_for_list_title,
                        error_for_todo_item_name,
                        find_todo_by_id,
                        sort_todo_lists,
                        )

from todos.database_persistence import (
                                        DatabasePersistence,
                                        require_todo_exists,
                                        require_list_exists,
                                        )

app = Flask(__name__)
app.secret_key=secrets.token_hex(32)

# Routes
@app.before_request
def load_db():
    g.storage = DatabasePersistence()

@app.route('/')
def index():
    return redirect(url_for('get_lists'))

@app.route('/lists/new')
def add_todo_list():
    return render_template('new_list.html')

@app.route('/lists/<int:list_id>')
@require_list_exists
def display_list(list_id):
    lst = g.storage.find_list(list_id)
    return render_template('list.html', lst=lst)

@app.route('/lists')
def get_lists():
    lists = sort_todo_lists(g.storage.all_lists())
    return render_template('lists.html', lists=lists)

@app.route('/lists', methods=['POST'])
def create_list():
    title = request.form['list_title'].strip()

    error = error_for_list_title(title, g.storage.all_lists())
    if error:
        flash(error, 'error')
        return render_template('new_list.html', title=title)

    g.storage.create_new_list(title)
    flash('The list has been created.', 'success')

    return redirect(url_for('get_lists'))

@app.route('/lists/<int:list_id>/edit')
def edit_list(list_id):
    lst = g.storage.find_list(list_id)

    return render_template('edit_list.html', lst=lst)

@app.route('/lists/<int:list_id>/todos', methods=['POST'])
@require_list_exists
def create_todo(list_id):
    todo = request.form['todo'].strip()

    error = error_for_todo_item_name(todo)
    if error:
        flash(error, 'error')
        lst = g.storage.find_list(list_id)
        return render_template('list.html', lst=lst, todo=todo)

    g.storage.create_new_todo(list_id, todo)

    flash('The todo item has been created.', 'success')

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<int:list_id>/todos/<int:todo_id>/move', methods=['POST'])
@require_todo_exists
def reorder_todo_item(list_id, todo_id):
    direction = request.form['direction']
    g.storage.reorder_todo_item(list_id, todo_id, direction)

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<int:list_id>/todos/<int:todo_id>/delete', methods=['POST'])
@require_todo_exists
def delete_todo_item(list_id, todo_id):
    g.storage.delete_todo_from_list(todo_id)
    flash('Todo item successfully deleted.', 'success')

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<int:list_id>/todos/<int:todo_id>/toggle', methods=['POST'])
@require_todo_exists
def toggle_todo_completion(list_id, todo_id):
    status = request.form['completed'] == 'True'
    g.storage.toggle_todo_completion(todo_id, status)

    flash('Todo marked as completed.', 'success')

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<int:list_id>/complete_all', methods=['POST'])
@require_list_exists
def toggle_all_todo_completion(list_id):
    g.storage.toggle_all_todo_completion(list_id)

    flash('Todo marked as completed.', 'success')

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<int:list_id>/delete', methods=['POST'])
@require_list_exists
def delete_list(list_id):
    g.storage.delete_list(list_id)

    flash('Todo list successfully deleted.', 'success')

    return redirect(url_for('get_lists'))

@app.route('/lists/<int:list_id>/rename', methods=['POST'])
@require_list_exists
def rename_list(list_id):
    title = request.form['list_title'].strip()

    error = error_for_list_title(title, g.storage.all_lists())
    if error:
        flash(error, 'error')
        lst = g.storage.find_list(list_id)
        return render_template('edit_list.html', lst=lst)

    g.storage.rename_list_by_id(list_id, title)

    flash('Todo list successfully renamed.', 'success')

    return redirect(url_for('display_list', list_id=list_id))

# Context processors
@app.context_processor
def todos_completed():
    def todos_completed_count(lst):
        return sum(1 for todo in lst['todos'] if todo['completed'])
    return {'todos_completed_count': todos_completed_count}

if __name__ == "__main__":
    if os.environ.get('FLASK_ENV') == 'production':
        app.run(debug=False)
    else:
        app.run(debug=True, port=8080)