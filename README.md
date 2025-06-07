# Agentic AI for Fraud Detection

This project is a conversational AI agent designed for a simple fraud detection workflow. The agent analyzes uploaded ID card images, checks the extracted information against a local database, and sends email notifications for potential fraud.

It is built using Python with **LangChain**, **LangGraph**, and Google's **Gemini 2.0 Flash** model, all served via a **Flask** web interface.

---

## Core Architecture & Workflow

The agent operates as a state machine managed by `LangGraph`. This allows it to handle a sequence of tasks while maintaining context.

The workflow is as follows:

1.  **Image Upload**: The user uploads an image of an ID card through a simple web interface.

2.  **ID Card Analysis**: The agent uses the `analyze_id_card_tool` to process the image with a multimodal AI model. This tool extracts key information: the identity number, full name, and date of birth.

3.  **Database Verification (RAG)**: The extracted information is passed to the `database_check_tool`. This tool functions as a Retrieval-Augmented Generation (RAG) system by querying a local SQLite database to see if an identical record already exists.
    * If a matching record is found, it indicates a potential duplicate or fraudulent attempt.
    * If no match is found, the new record is considered legitimate for this workflow and is added to the database.

4.  **Fraud Notification**: If the database check finds an existing identical record, the agent will use the `notify_fraud_tool` to send an email to a designated security or administrator address, flagging the potential fraud.

5.  **User Feedback**: The agent communicates the results of the entire process back to the user through the web interface.

---

## Project Structure


.
├── main.py                 # Core agent logic, state management, and Flask web server
├── database_setup.py       # Script to initialize the SQLite database
├── requirements.txt        # Python dependencies
├── .env                    # For storing environment variables (API keys, email credentials)
│
├── tools/
│   ├── init.py
│   ├── analyze_id_card.py  # Tool for extracting text from an ID card image
│   ├── database_check.py   # Tool for querying and updating the SQLite database
│   └── notify_fraud.py     # Tool for sending email notifications
│
└── templates/
└── index.html          # Simple HTML front-end for image uploads


---

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the root directory and add the following:
    ```
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    EMAIL_HOST="smtp.example.com"
    EMAIL_PORT=587
    EMAIL_USER="your-email@example.com"
    EMAIL_PASS="your-email-password"
    ```

5.  **Initialize the database:**
    Run the setup script to create the `identity_database.db` file and the `records` table.
    ```bash
    python database_setup.py
    ```

---

## How to Run

1.  **Start the Flask application:**
    ```bash
    python main.py
    ```

2.  **Open your web browser:**
    Navigate to `http://127.0.0.1:5000`.

3.  **Upload an ID card image** and the agent will automatically begin the fraud detection process.
