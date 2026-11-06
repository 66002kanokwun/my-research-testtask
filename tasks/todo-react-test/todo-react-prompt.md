Build a small todo list web app with React (frontend only, in-memory state, nothing persisted).
Features:
- Add a todo from a text input. Empty or whitespace-only input must show an error message
  and must not add anything. After a successful add the input is cleared.
- Toggle a todo done / not done with a checkbox.
- Edit a todo title: clicking edit shows an input pre-filled with the current title and a save button;
  saving updates the title.
- Delete a todo.
- Filter the list: all / active / done.
- Show the number of remaining (not done) todos.
Split the UI into small components (TodoForm, TodoList, TodoItem, FilterBar).
Use hooks (useState, useMemo).
src/App.jsx must default-export the root component.
Required data-testid attributes (the app is graded by automated tests that use them):
- todo-input: the text input for a new todo
- add-button: the button that adds the todo
- error-message: rendered ONLY while there is an error
- todo-item: root element of each todo (one per todo)
- todo-title: element showing the title of a todo (not rendered while that todo is being edited)
- todo-toggle: the checkbox (input type="checkbox") inside each todo-item
- todo-edit: button that starts editing a todo
- todo-edit-input: the input shown while editing, pre-filled with the current title
- todo-save: button that saves the edit
- todo-delete: button that deletes a todo
- filter-all, filter-active, filter-done: the three filter buttons
- remaining-count: element whose text contains the number of not-done todos
Also write your own tests, and make sure npm install, npm run build and the tests all pass.
CRITICAL INSTRUCTION: You MUST include ALL the data-testid attributes specified above. The automated grading tests will fail if any testid is missing or misspelled.