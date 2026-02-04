from uuid import uuid4
from functools import wraps
import os
from flask import (
                    abort,
                    flash,
                    Flask,
                    redirect,
                    render_template,
                    request,
                    session,
                    url_for,
                    )
from todos.utils import (
                        delete_todo,
                        error_for_list_title,
                        error_for_todo_item_name,
                        find_list_by_id,
                        find_todo_by_id,
                        mark_all_complete,
                        sort_todo_lists,
                        )

app = Flask(__name__)
app.secret_key='secret1'

# Helper functions
def ensure_todo_positions(lst):
    for index, todo in enumerate(lst['todos']):
        todo['position'] = index

def require_list(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        list_id = kwargs.get('list_id')
        lst = find_list_by_id(list_id, session['lists'])
        if not lst:
            abort(404)

        return f(lst=lst, *args, **kwargs)

    return decorated_function

def require_todo(f):
    @wraps(f)
    @require_list
    def decorated_function(lst, *args, **kwargs):
        todo_id = kwargs.get('todo_id')
        todo = find_todo_by_id(todo_id, lst['todos'])
        if not todo:
            abort(404)
        return f(lst=lst, todo=todo, *args, **kwargs)

    return decorated_function

# Routes
@app.before_request
def initialize_session():
    if 'lists' not in session:
        session['lists'] = []

@app.route('/')
def index():
    return redirect(url_for('get_lists'))

@app.route('/lists/new')
def add_todo_list():
    return render_template('new_list.html')

@app.route('/lists/<list_id>')
@require_list
def display_list(lst, list_id):
    ensure_todo_positions(lst)

    return render_template('list.html', lst=lst)

@app.route('/lists')
def get_lists():
    lists = sort_todo_lists(session['lists'])
    return render_template('lists.html', lists=lists)

@app.route('/lists', methods=['POST'])
def create_list():
    title = request.form['list_title'].strip()

    error = error_for_list_title(title, session['lists'])
    if error:
        flash(error, 'error')
        return render_template('new_list.html', title=title)

    session['lists'].append({
        'id': str(uuid4()),
        'title': title,
        'todos': [],
    })

    flash('The list has been created.', 'success')
    session.modified = True

    return redirect(url_for('get_lists'))

@app.route('/lists/<list_id>/edit')
def edit_list(list_id):
    lst = find_list_by_id(list_id, session['lists'])
    ensure_todo_positions(lst)

    return render_template('edit_list.html', lst=lst)

@app.route('/lists/<list_id>/todos', methods=['POST'])
@require_list
def create_todo(lst, list_id):
    todo = request.form['todo'].strip()

    ensure_todo_positions(lst)

    error = error_for_todo_item_name(todo)
    if error:
        flash(error, 'error')
        return render_template('list.html', lst=lst, todo=todo)

    lst['todos'].append({
        'id': str(uuid4()),
        'title': todo,
        'completed': False,
        'position': len(lst['todos']) + 1,
        })

    flash('The todo item has been created.', 'success')
    session.modified = True

    return redirect(url_for('display_list', list_id=lst['id']))

@app.route('/lists/<list_id>/todos/<todo_id>/move', methods=['POST'])
@require_todo
def reorder_todo_item(list_id, todo_id, lst=None, todo=None):
    ensure_todo_positions(lst)
    position = todo['position']
    direction = request.form['direction']
    swap_position = position + 1 if direction == 'down' else position - 1
    swap_todo = next((todo_item for todo_item in lst['todos'] if todo_item['position'] == swap_position), None)

    if swap_todo:
        todo['position'], swap_todo['position'] = swap_todo['position'], todo['position']

    lst['todos'].sort(key=lambda todo: todo['position'])
    session.modified = True

    return redirect(url_for('display_list', list_id=lst['id']))

@app.route('/lists/<list_id>/todos/<todo_id>/toggle', methods=['POST'])
@require_todo
def toggle_todo_completion(lst, todo, list_id, todo_id):
    ensure_todo_positions(lst)
    todo['completed'] = request.form['completed'] == 'True'
    flash('Todo marked as completed.', 'success')
    session.modified = True

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<list_id>/todos/<todo_id>/delete', methods=['POST'])
@require_todo
def delete_todo_item(lst, todo, list_id, todo_id):
    delete_todo(lst, todo)
    flash('Todo item successfully deleted.', 'success')
    session.modified = True

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<list_id>/complete_all', methods=['POST'])
@require_list
def complete_all_todos(lst, list_id):
    ensure_todo_positions(lst)
    mark_all_complete(lst)

    flash('Todo marked as completed.', 'success')
    session.modified = True

    return redirect(url_for('display_list', list_id=list_id))

@app.route('/lists/<list_id>/delete', methods=['POST'])
@require_list
def delete_list(lst, list_id):
    ensure_todo_positions(lst)
    session['lists'].remove(lst)

    flash('Todo list successfully deleted.', 'success')
    session.modified = True

    return redirect(url_for('get_lists'))

@app.route('/lists/<list_id>/rename', methods=['POST'])
@require_list
def rename_list(lst, list_id):
    ensure_todo_positions(lst)
    title = request.form['list_title'].strip()

    error = error_for_list_title(title, session['lists'])
    if error:
        flash(error, 'error')
        return render_template('edit_list.html', lst=lst)

    lst['title'] = title

    flash('Todo list successfully renamed.', 'success')
    session.modified = True

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