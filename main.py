import boto3
import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import aiofiles
import re

# Load AWS credentials from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# CORS setup for React to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace "*" with "http://localhost:3000" in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging for debugging and tracking
logging.basicConfig(level=logging.DEBUG)

# Initialize AWS Textract client with credentials from .env file
textract = boto3.client(
    'textract',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    endpoint_url="https://textract.us-east-1.amazonaws.com"
)

# Ensure 'temp' directory exists to store uploaded files
if not os.path.exists('temp'):
    os.makedirs('temp')

# Helper function to process the document using Textract
def process_document(file_bytes: bytes):
    try:
        logging.debug(f"Processing document...")

        # Call Textract to process the document
        response = textract.detect_document_text(
            Document={'Bytes': file_bytes}  # Pass file bytes directly
        )

        # Log response for debugging
        logging.debug("Document processed.")
        return response
    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

# Helper function to extract fields from the Textract response
def extract_fields_from_text(text: str):
    # Regular expressions to match phone number and email
    phone_regex = r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"
    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    # Search for phone numbers and email addresses
    phone_number = re.findall(phone_regex, text)
    email = re.findall(email_regex, text)

    # Extract the name from the first line (assumption)
    name = text.split('\n')[0] if text else "Not found"

    return {
        "name": name,
        "phone_number": phone_number[0] if phone_number else "Not found",
        "email": email[0] if email else "Not found"
    }

# API endpoint to upload and process the file
@app.post("/extract-data/")
async def extract_data(file: UploadFile = File(...)):
    try:
        # Save the uploaded file to a temporary location asynchronously
        file_location = f"temp/{file.filename}"
        logging.debug(f"Saving file to {file_location}...")

        async with aiofiles.open(file_location, "wb") as buffer:
            content = await file.read()  # Read file content as bytes
            await buffer.write(content)  # Save it locally

        # Process the file using AWS Textract
        textract_response = process_document(content)  # Pass file bytes directly

        # Extract text from the Textract response and parse it
        text = ''
        for item in textract_response.get("Blocks", []):
            if item["BlockType"] == "LINE":
                text += item["Text"] + "\n"

        # Extract name, phone number, and email from the text
        extracted_fields = extract_fields_from_text(text)

        return JSONResponse(content=extracted_fields)  # Return the parsed fields

    except Exception as e:
        logging.error(f"Error processing uploaded file: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)









