from uuid import uuid4

class SessionPersistence:
    def __init__(self, session):
        self.session = session

        if 'lists' not in self.session:
            self.session['lists'] = []

    def all_lists(self):
        return self.session['lists']

    def find_list(self, list_id):
        found = (lst for lst in self.session['lists'])
        return next(found, None)

    def create_new_list(self, title):
        lists = self.all_lists()
        lists.append({
            'id': str(uuid4()),
            'title': title,
            'todos': [],
        })
        self.session.modified = True

    def rename_list_by_id(self, list_id, new_title):
        lst = self.find_list(list_id)
        if lst:
            lst['title'] = new_title
            self.session.modified = True

    def delete_list(self, list_id):
        self.session['lists'] = [
                                lst for lst in self.session['lists']
                                if lst['id'] != list_id
                                ]

        self.session.modified = True

    def create_new_todo(self, list_id, todo_name):
        lst = self.find_list(list_id)
        lst['todos'].append({
            'id': str(uuid4()),
            'title': todo_name,
            'completed': False,
            'position': len(lst['todos']) + 1,
            })

        self.session.modified = True

    def toggle_todo_completion(self, list_id, todo_id, status):
        lst = self.find_list(list_id)
        todo = next((todo for todo in lst['todos'] if todo['id'] == todo_id))
        todo['completed'] = status

        self.session.modified = True

    def delete_todo_from_list(self, lst, todo):
        lst['todos'].remove(todo)

        self.session.modified = True

    def toggle_all_todo_completion(self, lst):
        all_complete = all(todo['completed'] for todo in lst['todos'])
        for todo in lst['todos']:
            todo['completed'] = not all_complete

        self.session.modified = True

    def reorder_todo_item(self, lst, todo, direction):
        position = todo['position']
        swap_position = position + 1 if direction == 'down' else position - 1
        swap_todo = next((todo_item for todo_item in lst['todos'] if todo_item['position'] == swap_position), None)

        if swap_todo:
            todo['position'], swap_todo['position'] = swap_todo['position'], todo['position']

        lst['todos'].sort(key=lambda todo: todo['position'])

        self.session.modified = True