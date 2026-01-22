import boto3
import os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import aiofiles
from io import BytesIO
from PIL import Image
from typing import Tuple
import openai
import json
import re

# Load AWS + OpenAI credentials from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Configure CORS to allow frontend to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Initialize AWS Textract client
textract = boto3.client(
    'textract',
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    endpoint_url="https://textract.us-east-1.amazonaws.com"
)

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_KEY")

# Ensure 'temp' directory exists
if not os.path.exists('temp'):
    os.makedirs('temp')

# -----------------------------
# Helpers
# -----------------------------

def is_supported_format(content: bytes) -> Tuple[bool, str]:
    supported_formats = {
        b'\xff\xd8\xff\xe0': 'JPEG',
        b'\xff\xd8\xff\xe1': 'JPEG',
        b'\xff\xd8\xff\xdb': 'JPEG',
        b'\xff\xd8\xff\xe2': 'JPEG',
        b'\x89PNG': 'PNG',
        b'%PDF': 'PDF',
        b'II*\x00': 'TIFF',
        b'MM\x00*': 'TIFF',
    }

    file_signature = content[:4]
    for signature, format_name in supported_formats.items():
        if content.startswith(signature):
            return True, format_name

    if b'%PDF' in content[:1024]:
        return True, 'PDF'

    return False, 'Unknown'

def convert_to_supported_format(file_bytes: bytes, target_format: str = 'PNG') -> bytes:
    try:
        image = Image.open(BytesIO(file_bytes))
        original_format = image.format or 'Unknown'
        logging.info(f"Converting {original_format} image to {target_format}...")

        if target_format == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_image.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = rgb_image
        elif target_format == 'JPEG' and image.mode != 'RGB':
            image = image.convert('RGB')
        elif target_format in ('PNG', 'TIFF') and image.mode not in ('RGB', 'RGBA'):
            if image.mode in ('RGBA', 'LA', 'P'):
                if image.mode == 'P':
                    image = image.convert('RGBA')
            else:
                image = image.convert('RGB')

        output = BytesIO()
        image.save(output, format=target_format)
        output.seek(0)
        converted_bytes = output.read()

        logging.debug(f"Image converted to {target_format}: {len(file_bytes)} bytes -> {len(converted_bytes)} bytes")
        return converted_bytes
    except Exception as e:
        logging.error(f"Error converting image: {str(e)}")
        raise

def process_document(image_bytes: bytes):
    try:
        logging.debug(f"Processing document with {len(image_bytes)} bytes...")
        response = textract.detect_document_text(Document={'Bytes': image_bytes})
        logging.debug("Document processed.")
        return response
    except Exception as e:
        logging.error(f"Error processing document: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}

def extract_text_from_textract(textract_json: dict) -> str:
    """
    Extracts plain text from Textract response
    """
    lines = []
    for block in textract_json.get("Blocks", []):
        if block.get("BlockType") == "LINE":
            lines.append(block.get("Text", ""))
    return "\n".join(lines)

def _parse_openai_json(raw: str) -> dict:
    """Parse OpenAI response as JSON. Handles empty, whitespace, and markdown code blocks."""
    if not raw or not isinstance(raw, str):
        raise ValueError("OpenAI returned empty or invalid content")
    s = raw.strip()
    if not s:
        raise ValueError("OpenAI returned empty content")
    # Try direct parse first
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Strip markdown code blocks (e.g. ```json ... ``` or ``` ... ```)
    if "```" in s:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass
    raise ValueError(f"Could not parse OpenAI response as JSON. Raw content: {repr(s[:200])}")


def ask_openai_for_fields(text: str) -> dict:
    prompt = f"""
You are a helpful assistant.

Extract the following fields from the given text:

1. Facility Name
2. Person's Name
3. Person's Role
4. Email
5. Phone Number
6. Address


If any field is not found, write "Not found".

Text:
{text}

Output JSON only, with keys:
facility_name, person_name, person_role, email, phone, address
"""
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    content = response.choices[0].message.content
    return _parse_openai_json(content)

# -----------------------------
# API Route
# -----------------------------

@app.post("/extract-data/")
async def extract_data(file: UploadFile = File(...)):
    try:
        logging.debug(f"Reading uploaded file: {file.filename}...")
        content = await file.read()

        if not content:
            return JSONResponse(content={"error": "Uploaded file is empty"}, status_code=400)

        is_supported, detected_format = is_supported_format(content)

        if not is_supported:
            file_signature = content[:4].hex() if len(content) >= 4 else 'too short'
            logging.info(f"File format not directly supported. File signature: {file_signature}")

            try:
                test_image = Image.open(BytesIO(content))
                original_format = test_image.format or 'Unknown Image'
                logging.info(f"Detected convertible image format: {original_format}. Converting to PNG...")
                content = convert_to_supported_format(content, target_format='PNG')
                detected_format = 'PNG (converted from ' + original_format + ')'
                logging.info("Image converted successfully to PNG")
            except Exception as e:
                logging.warning(f"File cannot be converted: {str(e)}. File signature: {file_signature}")
                return JSONResponse(
                    content={
                        "error": "Unsupported file format. Please upload PNG, JPEG, PDF, or TIFF."
                    },
                    status_code=400
                )

        logging.debug(f"File read successfully, {len(content)} bytes, format: {detected_format}")

        textract_response = process_document(content)

        # Extract text from Textract response
        extracted_text = extract_text_from_textract(textract_response)

        # Send text to OpenAI to extract required fields
        extracted_fields = ask_openai_for_fields(extracted_text)

        return JSONResponse(content={
            "status": "success",
            "detected_format": detected_format,
            "fields": extracted_fields
        })

    except Exception as e:
        logging.error(f"Error processing uploaded file: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
