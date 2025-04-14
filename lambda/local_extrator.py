import json
import boto3
import pymysql
import os

# ENV variables for DB access
os.environ['AWS_ACCESS_KEY_ID'] = 'YOUR ACCESS KEY ID HERE'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'YOUR SECRET ACCESS KEY HERE'
os.environ['AWS_REGION'] = 'us-east-2'

def extract_sections(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    sections = {
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "projects": []
    }

    current_section = None

    # Keywords to look for 
    section_keywords = {
        "experience": ["experience", "work experience", "professional experience"],
        "education": ["education", "academic background"],
        "skills": ["skills", "technical skills", "computer knowledge", "technologies"],
        "certifications": ["certifications", "licenses"],
        "projects": ["projects", "personal projects"]
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

# Load resume and parse with Textract
def extract_text_from_pdf(file_path):
    #textract = boto3.client('textract')
    textract = boto3.client('textract', region_name='us-east-2')  # ← your region
    with open(file_path, 'rb') as f:
        response = textract.detect_document_text(Document={'Bytes': f.read()})
    lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
    return "\n".join(lines)

# Locally test it
if __name__ == "__main__":
    resume_path = "RESUME HERE"
    text = extract_text_from_pdf(resume_path)
    sections = extract_sections(text)
    
    print(json.dumps(sections, indent=2))  # Pretty print output
