import boto3
import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging
import aiofiles


#extra


# Load AWS credentials from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Set up logging for debugging and tracking
logging.basicConfig(level=logging.DEBUG)

# Initialize AWS Textract client with credentials from .env file
textract = boto3.client(
    'textract',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    endpoint_url="https://textract.us-east-1.amazonaws.com"  # Replace with the correct endpoint if needed
)


# Ensure 'temp' directory exists to store uploaded files
if not os.path.exists('temp'):
    os.makedirs('temp')

# Helper function to process the document using Textract
def process_document(file_bytes: bytes):
    try:
        logging.debug(f"Processing document...")

        # Start measuring time for AWS Textract processing
        response = textract.detect_document_text(
            Document={'Bytes': file_bytes}  # Pass file bytes directly here
        )

        # Log the response for debugging
        logging.debug("Document processed.")
        return response
    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


# API endpoint to upload and process the file
@app.post("/extract-data/")
async def extract_data(file: UploadFile = File(...)):
    try:
        # Save the uploaded file to a temporary location asynchronously
        file_location = f"temp/{file.filename}"
        logging.debug(f"Saving file to {file_location}...")

        # Use aiofiles to save the file asynchronously
        async with aiofiles.open(file_location, "wb") as buffer:
            content = await file.read()  # Read the file content as bytes
            await buffer.write(content)  # Write content to the temp directory

        # Process the file using AWS Textract
        textract_response = process_document(content)  # Pass the content directly as bytes
        
        return JSONResponse(content=textract_response)  # Return the response from Textract

    except Exception as e:
        logging.error(f"Error processing uploaded file: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


