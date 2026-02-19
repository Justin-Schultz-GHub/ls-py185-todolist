def error_for_list_title(title, lists):
    if any(lst['title'] == title for lst in lists):
        return 'The title must be unique.'
    elif not 1 <= len(title) <= 100:
        return 'The title must be between 1 and 100 characters'
    else:
        return None

def error_for_todo_item_name(todo):
    return (
            'Todo names must be between 1 and 100 characters'
            if not 1 <= len(todo) <= 100
            else None
            )

def is_list_complete(lst):
    return lst['todos_count'] > 0 and lst['todos_remaining'] == 0

def sort_todo_lists(lists):
    return sorted(lists,
                key=lambda lst: (is_list_complete(lst), lst['title'].lower())
                )