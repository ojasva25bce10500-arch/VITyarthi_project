import mysql.connector
from contextlib import contextmanager
import getpass
import sys

CURRENT_USER_NAME = None
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'charset': 'utf8'
}
DATABASE_NAME = 'todo_list_db'

@contextmanager
def get_db_connection():
    conn = None
    try:
        password = getattr(get_db_connection, 'password', None)
        if password is None:
            password = getpass.getpass("Enter MySQL password for user 'root': ")
            setattr(get_db_connection, 'password', password)
        conn = mysql.connector.connect(**DB_CONFIG, password=password)
        if conn.is_connected():
            if not getattr(get_db_connection, 'connected_once', False):
                print("Database connection established.")
                setattr(get_db_connection, 'connected_once', True)
            yield conn
        else:
            raise mysql.connector.Error("Connection failed unexpectedly after password check.")
            
    except mysql.connector.Error as err:
        print(f"Database connection failed: {err}")
        print("Please check your MySQL service and credentials.")
        sys.exit(1)        
    finally:
        if conn and conn.is_connected():
            conn.close()

def create_database_and_table():
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}")
            db.commit()
            cursor.execute(f"USE {DATABASE_NAME}")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_name VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL,
                    status VARCHAR(10) NOT NULL DEFAULT 'Pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.commit()
            print("Database and 'tasks' table verified.")
        DB_CONFIG['database'] = DATABASE_NAME
            
    except Exception as e:
        print(f"An error occurred during table setup: {e}")

def execute_query(query, params=(), fetch_result=False, commit=True):
    try:
        with get_db_connection() as db:
            cursor = db.cursor(buffered=True)
            
            cursor.execute(query, params)
            
            if commit:
                db.commit()
                
            if fetch_result:
                return cursor.fetchall()
            return True
            
    except Exception as e:
        print(f"Database operation failed: {e}")
        return [] if fetch_result else False

def add_task(description):
    user = CURRENT_USER_NAME
    query = "INSERT INTO tasks (user_name, description) VALUES (%s, %s)"
    if execute_query(query, (user, description)):
        print(f"Task added for {user}: '{description}'")

def view_tasks():
    user = CURRENT_USER_NAME
    query = "SELECT id, description, status FROM tasks WHERE user_name = %s ORDER BY status, id"
    tasks = execute_query(query, (user,), fetch_result=True)
    
    if not tasks:
        print(f"--- {user}'s To-Do List is Empty! ---")
        return

    print(f"\n--- {user}'s To-Do List ---")
    for task_id, description, status in tasks:
        if status is not None and status.strip().lower() == "complete":
            status_symbol = "[X]"
        else:
            status_symbol = "[ ]"
            
        print(f"[{task_id:3}] {status_symbol} {description} ({status})")
    print("----------------------------\n")

def mark_complete(description_input):
    description = description_input.strip()
    user = CURRENT_USER_NAME

    if not description:
        print("Task description cannot be empty.")
        return
    update_query = "UPDATE tasks SET status = 'Complete' WHERE user_name = %s AND description = %s AND status != 'Complete'"    
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            
            cursor.execute(update_query, (user, description))
            rows_affected = cursor.rowcount
            db.commit()
            if rows_affected > 0:
                print(f"Task '{description}' marked as Complete!")
            else:
                check_query = "SELECT status FROM tasks WHERE user_name = %s AND description = %s"
                cursor.execute(check_query, (user, description))
                task = cursor.fetchone()
                if task:
                    if task[0] == 'Complete':
                        print(f"Task '{description}' was already Complete.")
                    else:
                         print(f"No pending task found matching the exact description: '{description}'")
                else:
                    print(f"Task '{description}' not found for user {user}.")            
    except Exception as e:
        print(f"Database operation failed during update: {e}")

def delete_task(description_input):
    description = description_input.strip()
    user = CURRENT_USER_NAME

    if not description:
        print("Task description cannot be empty.")
        return
        
    delete_query = "DELETE FROM tasks WHERE user_name = %s AND description = %s"
    
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute(delete_query, (user, description))
            rows_affected = cursor.rowcount
            db.commit()

            if rows_affected > 0:
                print(f"Task '{description}' deleted.")
            else:
                print(f"No task found matching the exact description: '{description}'")

    except Exception as e:
        print(f"Database operation failed during deletion: {e}")


def startup_prompt():
    global CURRENT_USER_NAME
    name = input("Please enter your name to start your personalized To-Do List: ").strip()
    if not name:
        name = "Guest"
    CURRENT_USER_NAME = name
    print(f"Welcome, {CURRENT_USER_NAME}!")

def main_menu():
    startup_prompt()
    create_database_and_table() 
    
    while True:
        print(f"\n===== {CURRENT_USER_NAME}'s Menu =====")
        print("1. View My Tasks")
        print("2. Add New Task")
        print("3. Mark Task Complete (by description)")
        print("4. Delete Task (by description)")
        print("5. Exit")
        
        choice = input("Enter your choice (1-5): ")

        if choice == '1':
            view_tasks()
        elif choice == '2':
            description = input("Enter the new task description: ").strip()
            if description:
                add_task(description)
            else:
                print("Task description cannot be empty.")
        elif choice == '3':
            description = input("Enter the EXACT description of the task to mark complete: ").strip()
            mark_complete(description)
        elif choice == '4':
            description = input("Enter the EXACT description of the task to delete: ").strip()
            delete_task(description)
        elif choice == '5':
            print(f"Exiting To-Do List, {CURRENT_USER_NAME}. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    main_menu()
