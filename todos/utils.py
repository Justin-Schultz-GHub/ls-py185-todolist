def error_for_list_title(title, lists):
    if any(lst['title'] == title for lst in lists):
        return 'The title must be unique.'
    elif not 1 <= len(title) <= 100:
        return 'The title must be between 1 and 100 characters'
    else:
        return None

def find_todo_by_id(todo_id, todos):
    for todo in todos:
        if todo['id'] == todo_id:
            return todo

    return None

def error_for_todo_item_name(todo):
    return (
            'Todo names must be between 1 and 100 characters'
            if not 1 <= len(todo) <= 100
            else None
            )

def is_list_complete(lst):
    return bool(lst['todos']) and all(todo['completed'] for todo in lst['todos'])

def sort_todo_lists(lists):
    return sorted(lists,
                key=lambda lst: (is_list_complete(lst), lst['title'].lower())
                )