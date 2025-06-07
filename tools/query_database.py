import sqlite3
import logging
from typing import List, Dict, Any
from pydantic import BaseModel
from langchain_core.tools import tool
from rich.console import Console
from rich.table import Table

# --- Configuration ---
DB_FILE = "identity_database.db"

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# This tool takes no input, so we use an empty Pydantic model.
class QueryDatabaseInput(BaseModel):
    """Input schema for the database query tool."""
    pass

@tool("query_database_tool", args_schema=QueryDatabaseInput)
def query_database_tool() -> str:
    """
    Queries the database to fetch all existing identity records.
    Use this tool when the user asks to see or list all data in the database.
    Returns the data as a neatly formatted string table.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        # This allows accessing columns by name, making the code more readable.
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT identity_number, full_name, date_of_birth, timestamp FROM records")
        records = cursor.fetchall()

        if not records:
            return "The database is currently empty. No records found."

        # --- Use the 'Rich' library to create a beautiful table for the output ---
        table = Table(title="Identity Records in Database", show_header=True, header_style="bold magenta")
        table.add_column("Identity Number", style="cyan", no_wrap=True)
        table.add_column("Full Name", style="green")
        table.add_column("Date of Birth", style="yellow")
        table.add_column("Timestamp (UTC)", style="dim")

        for record in records:
            table.add_row(
                record["identity_number"],
                record["full_name"],
                record["date_of_birth"],
                record["timestamp"]
            )
        
        # To return the table as a string, we capture the console output.
        console = Console(record=True, width=120)
        console.print(table)
        return console.export_text()

    except sqlite3.Error as e:
        logger.error(f"A database error occurred during query: {e}")
        return f"An error occurred while querying the database: {e}"
    finally:
        if conn:
            conn.close()
