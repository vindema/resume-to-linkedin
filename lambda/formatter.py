import json
import pymysql
import os
import requests

DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']
HF_API_TOKEN = os.environ['HF_API_TOKEN']

# Hugging Face model URL (Mistral)
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

def format_section(section, content):
    prompt = f"Rewrite this resume's {section} section for LinkedIn. Use first person, bullet points, and action verbs:\n\n{content}"

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}"
    }

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "do_sample": False
        }
    }

    response = requests.post(HF_API_URL, headers=headers, json=payload)

    # Defensive check
    if response.status_code != 200:
        return f"Error: {response.status_code} - {response.text}"

    result = response.json()
    if isinstance(result, list):
        return result[0]['generated_text'].strip()
    elif "generated_text" in result:
        return result["generated_text"].strip()
    else:
        return "Error: Unexpected HF response"

def lambda_handler(event, context):
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    with conn.cursor() as cursor:
        cursor.execute("SELECT section, content FROM resume_sections")
        rows = cursor.fetchall()

        for section, content in rows:
            formatted = format_section(section, content)
            cursor.execute(
                "INSERT INTO linkedin_profile_sections (section, content) VALUES (%s, %s)",
                (section, formatted)
            )

    conn.commit()
    conn.close()

    return {
        'statusCode': 200,
        'body': json.dumps('Sections formatted with Hugging Face and stored')
    }
