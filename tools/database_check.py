import sqlite3
import logging
from typing import Dict
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# --- Configuration ---
DB_FILE = "identity_database.db"

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Schema for Tool Input ---
class DatabaseCheckInput(BaseModel):
    """Input schema for the database check tool."""
    identity_number: str = Field(description="The identity number to check against the database.")
    full_name: str = Field(description="The full name of the individual.")
    date_of_birth: str = Field(description="The individual's date of birth.")

# --- The Tool Definition ---
@tool("database_check_tool", args_schema=DatabaseCheckInput)
def database_check_tool(identity_number: str, full_name: str, date_of_birth: str) -> Dict[str, str]:
    """
    Checks if an identity record exists in the local SQLite database.
    If the record does not exist, it adds it.
    Returns 'duplicate' if the record exists, 'new_record_added' if it was added,
    or 'error' if something went wrong.
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # --- 1. Check for existing record ---
        # Query the database for a record with the given identity number.
        cursor.execute("SELECT identity_number FROM records WHERE identity_number = ?", (identity_number,))
        existing_record = cursor.fetchone()

        if existing_record:
            # If a record is found, it's a potential duplicate.
            logger.warning(f"Duplicate record found for ID: {identity_number}")
            return {
                "status": "duplicate",
                "message": f"An identical record with ID number {identity_number} already exists."
            }
        else:
            # --- 2. If no record, insert new data ---
            # If no record exists, proceed to add the new information.
            logger.info(f"No existing record found for ID: {identity_number}. Adding new record.")
            insert_query = """
            INSERT INTO records (identity_number, full_name, date_of_birth)
            VALUES (?, ?, ?);
            """
            cursor.execute(insert_query, (identity_number, full_name, date_of_birth))
            conn.commit()
            
            return {
                "status": "new_record_added",
                "message": f"New identity record for {full_name} has been successfully added to the database."
            }

    except sqlite3.Error as e:
        # Handle potential database errors (e.g., file not found, table missing)
        logger.error(f"A database error occurred: {e}")
        return {
            "status": "error",
            "error": f"Database operation failed: {e}"
        }
    
    finally:
        # Ensure the database connection is always closed.
        if conn:
            conn.close()
