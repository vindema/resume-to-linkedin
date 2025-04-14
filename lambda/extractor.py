import json
import boto3
import pymysql
import os

# ENV variables for DB access
DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']

def extract_sections(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    sections = {
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": [],
        "computer knowledge": []
    }

    current_section = None

    # Keywords to look for 
    section_keywords = {
        "experience": ["experience", "work experience", "professional experience"],
        "education": ["education", "academic background"],
        "skills": ["skills", "technical skills"],
        "certifications": ["certifications", "licenses"],
        "projects": ["projects", "personal projects"],
        "computer knowledge": ["computer knowledge", "technologies"]
    }

    def identify_section(line):
        ''' Check if line contains known section keywords '''
        lower = line.lower()
        for sec, keywords in section_keywords.items():
            if any(keyword in lower for keyword in keywords):
                return sec
        return None

    # Group lines that belong to same section
    for line in lines:
        section = identify_section(line)
        if section:
            current_section = section
            continue
        if current_section:
            sections[current_section].append(line)

    # Join sections and clean up
    for sec in sections:
        sections[sec] = "\n".join(sections[sec]) if sections[sec] else "N/A"

    return sections

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    textract = boto3.client('textract')

    # Get S3 file from event
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = record['object']['key']
    tmp_file = f"/tmp/{key}"
    s3.download_file(bucket, key, tmp_file)

    # Extract text with Textract
    with open(tmp_file, 'rb') as document:
        image_bytes = document.read()
    response = textract.detect_document_text(Document={'Bytes': image_bytes})

    lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
    text = "\n".join(lines)

    # Extract sections and convert to JSON
    structured_data = extract_sections(text)
    structured_json = json.dumps(structured_data)

    # Store each section in RDS
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    with conn.cursor() as cursor:
        for section, content in structured_data.items():
            cursor.execute(
                "INSERT INTO resume_sections (section, content) VALUES (%s, %s)",
                (section, content)
            )
    conn.commit()
    conn.close()

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Resume successfully extracted and stored',
            'structured_data': structured_data
        })
    }
