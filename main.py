import os
import logging
from typing import Annotated, Dict
from typing_extensions import TypedDict
from uuid import uuid4

from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# --- Import Agent Tools ---
from tools.analyze_id_card import analyze_id_card_tool
from tools.database_check import database_check_tool
from tools.notify_fraud import notify_fraud_tool
from tools.query_database import query_database_tool # <-- NEW TOOL

# --- Load Environment Variables ---
load_dotenv()

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Agent State Definition ---
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    extracted_data: Dict[str, str] | None

# --- Setup LLM ---
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
except Exception as e:
    logger.critical(f"Could not initialize Google Generative AI. Check API Key. Error: {e}")
    llm = None

# ==============================================================================
# WORKFLOW 1: FRAUD DETECTION AGENT
# ==============================================================================
fraud_tools = [analyze_id_card_tool, database_check_tool, notify_fraud_tool]
llm_with_fraud_tools = llm.bind_tools(fraud_tools) if llm else None

fraud_system_prompt = (
    "You are a specialized AI agent for an ID card-based fraud detection system."
    "Your workflow is strictly defined and must be followed precisely. You must answer in Bahasa Indonesia"
    "\n"
    "--- WORKFLOW ---"
    "1.  **Analyze Image**: You will be given the path to an ID card image. Your first action is to call `analyze_id_card_tool`."
    "2.  **Check Database**: Take the extracted details and use `database_check_tool`."
    "3.  **Handle Outcome**: "
    "    - If the status is 'duplicate', you MUST call `notify_fraud_tool`."
    "    - If the status is 'new_record_added' or 'error', your job is complete."
    "4.  **Report**: Provide a final, concise summary of the actions taken and the result."
    "--- END OF WORKFLOW ---"
)

def fraud_agent_node(state: AgentState):
    messages = [HumanMessage(content=fraud_system_prompt)] + state['messages']
    response = llm_with_fraud_tools.invoke(messages)
    return {"messages": [response]}

def fraud_tool_node(state: AgentState):
    tool_calls = state["messages"][-1].tool_calls
    tool_outputs = []
    state_updates = {}
    for call in tool_calls:
        tool_name = call['name']
        tool_args = call.get('args', {})
        selected_tool = next((t for t in fraud_tools if t.name == tool_name), None)
        if selected_tool:
            output = selected_tool.invoke(tool_args)
            if tool_name == 'analyze_id_card_tool' and output.get("status") == "success":
                state_updates['extracted_data'] = {k: v for k, v in output.items() if k != 'status'}
        else:
            output = f"Error: Tool '{tool_name}' not found."
        tool_outputs.append(ToolMessage(content=str(output), tool_call_id=call['id']))
    return {"messages": tool_outputs, **state_updates}

# ==============================================================================
# WORKFLOW 2: CHAT AGENT
# ==============================================================================
chat_tools = [query_database_tool]
llm_with_chat_tools = llm.bind_tools(chat_tools) if llm else None

chat_system_prompt = (
    "You are a helpful assistant for the fraud detection system. You must answer in Bahasa Indonesia."
    "Your primary job is to answer questions about the identity records stored in the database."
    "When a user asks to see, list, show, or query the data, you must use the `query_database_tool`."
    "For any other questions, answer them based on your general knowledge."
)

def chat_agent_node(state: AgentState):
    messages = [HumanMessage(content=chat_system_prompt)] + state['messages']
    response = llm_with_chat_tools.invoke(messages)
    return {"messages": [response]}

def chat_tool_node(state: AgentState):
    tool_calls = state["messages"][-1].tool_calls
    tool_outputs = []
    for call in tool_calls:
        output = query_database_tool.invoke(call.get('args', {}))
        tool_outputs.append(ToolMessage(content=str(output), tool_call_id=call['id']))
    return {"messages": tool_outputs}

# --- Graph Definitions ---
def should_continue(state: AgentState):
    return "tools" if state["messages"][-1].tool_calls else "end"

# Fraud Graph
fraud_graph_builder = StateGraph(AgentState)
fraud_graph_builder.add_node("agent", fraud_agent_node)
fraud_graph_builder.add_node("tools", fraud_tool_node)
fraud_graph_builder.set_entry_point("agent")
fraud_graph_builder.add_conditional_edges("agent", should_continue)
fraud_graph_builder.add_edge("tools", "agent")
fraud_graph = fraud_graph_builder.compile()

# Chat Graph
chat_graph_builder = StateGraph(AgentState)
chat_graph_builder.add_node("agent", chat_agent_node)
chat_graph_builder.add_node("tools", chat_tool_node)
chat_graph_builder.set_entry_point("agent")
chat_graph_builder.add_conditional_edges("agent", should_continue)
chat_graph_builder.add_edge("tools", "agent")
chat_graph = chat_graph_builder.compile()

# --- Flask Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files or not llm:
        return jsonify({"error": "Invalid request or LLM not initialized"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid4()}_{filename}")
    file.save(filepath)

    initial_message = HumanMessage(content=f"Analyze the ID card image located at: {filepath}")
    
    final_response = None
    for event in fraud_graph.stream({"messages": [initial_message]}):
        if "agent" in event and event["agent"].get("messages"):
            ai_message = event["agent"]["messages"][-1]
            if not ai_message.tool_calls and ai_message.content:
                final_response = ai_message.content
    
    os.remove(filepath)
    return jsonify({"response": final_response or "Agent did not produce a final response."})

@app.route('/chat', methods=['POST'])
def chat():
    """Handles chat inquiries from the user."""
    data = request.get_json()
    if not data or 'message' not in data or not llm:
        return jsonify({"error": "Invalid request or LLM not initialized"}), 400

    user_message = HumanMessage(content=data['message'])
    
    final_response = "Sorry, I could not process your request."
    for event in chat_graph.stream({"messages": [user_message]}):
        if "agent" in event and event["agent"].get("messages"):
            ai_message = event["agent"]["messages"][-1]
            if not ai_message.tool_calls and ai_message.content:
                final_response = ai_message.content
    
    return jsonify({"response": final_response})

if __name__ == '__main__':
    if not os.getenv("GOOGLE_API_KEY"):
        print("CRITICAL: GOOGLE_API_KEY environment variable not set.")
    else:
        app.run(host='0.0.0.0', port=3000, debug=True)
