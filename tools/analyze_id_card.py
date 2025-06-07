import os
import base64
import logging
from typing import Dict

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from PIL import Image
import io
import json

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Schema for Tool Input ---
class AnalyzeIdCardInput(BaseModel):
    """Input schema for the ID card analysis tool."""
    image_path: str = Field(description="The file path to the ID card image to be analyzed.")

# --- The Tool Definition ---
@tool("analyze_id_card_tool", args_schema=AnalyzeIdCardInput)
def analyze_id_card_tool(image_path: str) -> Dict[str, str]:
    """
    Analyzes an ID card image to extract identity number, full name, and date of birth.
    Returns the extracted information in a structured JSON format.
    """
    if not os.path.exists(image_path):
        return {"status": "error", "error": f"File not found at path: {image_path}"}

    # --- Initialize the Gemini Vision Model ---
    # Make sure your GOOGLE_API_KEY is set in your environment
    try:
        # Using gemini-2.0-flash as it's fast and supports vision
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    except Exception as e:
        logger.error(f"Failed to initialize the language model: {e}")
        return {"status": "error", "error": "Could not initialize Gemini model. Check API key."}

    # --- Prepare the Image and Prompt for the Model ---
    try:
        # Open the image and convert it to a compatible format (e.g., PNG)
        with Image.open(image_path) as img:
            # Convert image to bytes
            byte_arr = io.BytesIO()
            img.convert("RGB").save(byte_arr, format='PNG')
            image_bytes = byte_arr.getvalue()
            
            # Encode image in base64
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')

    except Exception as e:
        logger.error(f"Failed to process the image: {e}")
        return {"status": "error", "error": f"Invalid or corrupted image file: {image_path}"}
    
    # --- Construct the Prompt with the Image ---
    # This prompt guides the model to perform OCR and extract specific fields in a JSON format.
    prompt_text = """
    Analyze the attached image of an ID card.
    Extract the following information precisely:
    1.  "identity_number": The national identity number (e.g., NIK in Indonesia).
    2.  "full_name": The full name of the person.
    3.  "date_of_birth": The date of birth.

    Return the information ONLY in a valid JSON object format, like this:
    {"identity_number": "...", "full_name": "...", "date_of_birth": "..."}
    Do not include any other text or explanations.
    """

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
            },
        ]
    )

    # --- Invoke the Model and Parse the Response ---
    try:
        logger.info(f"Sending image '{image_path}' to Gemini for analysis...")
        response = llm.invoke([message])
        
        # The response content should be a JSON string
        response_content = response.content
        
        # Clean the response to ensure it is valid JSON
        # The model sometimes wraps the JSON in ```json ... ```
        if "```json" in response_content:
            response_content = response_content.split("```json")[1].split("```")[0].strip()

        # Parse the JSON string into a Python dictionary
        extracted_data = json.loads(response_content)
        
        # --- Validate the Extracted Data ---
        required_keys = ["identity_number", "full_name", "date_of_birth"]
        if not all(key in extracted_data for key in required_keys):
            raise ValueError("The model did not return all the required fields.")

        extracted_data["status"] = "success"
        logger.info(f"Successfully extracted data: {extracted_data}")
        return extracted_data

    except json.JSONDecodeError:
        error_msg = "Failed to parse the model's response as JSON."
        logger.error(f"{error_msg} Raw response: {response_content}")
        return {"status": "error", "error": error_msg}
    except Exception as e:
        logger.error(f"An unexpected error occurred during model invocation: {e}")
        return {"status": "error", "error": str(e)}

