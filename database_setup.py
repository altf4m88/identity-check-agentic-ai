import sqlite3
import os

# --- Configuration ---
DB_FILE = "identity_database.db"

def insert_seed_data(cursor):
    """
    Inserts initial seed data into the records table
    """
    seed_data = [
        ('3273220107000001', 'Johnny Paylater', '2000-01-07'),
        ('3273220107000000', 'Jane Smith', '1995-03-15'),
        ('3273220107000003', 'Bob Wilson', '1988-12-25')
    ]
    
    insert_query = """
    INSERT INTO records (identity_number, full_name, date_of_birth)
    VALUES (?, ?, ?);
    """
    
    try:
        cursor.executemany(insert_query, seed_data)
        print("Successfully inserted seed data.")
    except sqlite3.IntegrityError as e:
        print(f"Error inserting seed data: {e}")

def setup_database():
    """
    Sets up the SQLite database.
    Creates the database file and the 'records' table if they don't already exist.
    """
    # Check if the database file already exists to avoid overwriting it.
    if os.path.exists(DB_FILE):
        print(f"Database file '{DB_FILE}' already exists. Setup not required.")
        return

    try:
        # Connect to the SQLite database.
        # This will create the database file if it does not exist.
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # --- Create the 'records' table ---
        # This table will store the information extracted from ID cards.
        # - identity_number: The unique ID number from the card. It is the PRIMARY KEY.
        # - full_name: The full name of the individual.
        # - date_of_birth: The individual's date of birth.
        # - timestamp: The date and time when the record was added.
        create_table_query = """
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identity_number TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)

        # Insert seed data after creating the table
        insert_seed_data(cursor)

        # Commit the changes to the database
        conn.commit()
        print(f"Successfully created table 'records' in '{DB_FILE}'.")

    except sqlite3.Error as e:
        print(f"An error occurred while setting up the database: {e}")

    finally:
        # Close the connection if it was opened
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    print("Initializing database setup...")
    setup_database()
