import json
import pymysql
import os
import urllib.request

DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']
HF_API_TOKEN = os.environ['HF_API_TOKEN']

HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

def format_section(section, content):
    prompt = f"Rewrite this resume's {section} section for LinkedIn. Use first person, bullet points, and action verbs:\n\n{content}"

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = json.dumps({
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 300,
            "do_sample": False
        }
    }).encode("utf-8")

    req = urllib.request.Request(HF_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            result = json.loads(response_data.decode("utf-8"))

            if isinstance(result, list):
                return result[0].get('generated_text', 'Error: No text returned').strip()
            elif "generated_text" in result:
                return result["generated_text"].strip()
            else:
                return "Error: Unexpected HF response"

    except urllib.error.HTTPError as e:
        error_details = e.read().decode()
        return f"Error: {e.code} - {error_details}"

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
