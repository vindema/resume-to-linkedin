import streamlit as st
import boto3
import pymysql
import tempfile
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Get AWS + DB config from env
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306))
}

# Initialize S3
s3 = boto3.client('s3', 
                  region_name=AWS_REGION,
                  aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                  aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

def upload_to_s3(file):
    s3.upload_fileobj(file, S3_BUCKET, file.name + ".pdf")
    return file.name

def get_profile_data():
    conn = pymysql.connect(**DB_CONFIG)
    with conn.cursor() as cursor:
        cursor.execute("SELECT section, content FROM linkedin_profile_sections")
        rows = cursor.fetchall()
    conn.close()
    return {section.capitalize(): content for section, content in rows}

# UI starts here
st.set_page_config(page_title="Resume to LinkedIn", page_icon="📄", layout="wide")
st.title("📄 Resume ➡️ LinkedIn Profile Generator")
st.markdown("Upload your resume, and get LinkedIn-ready content in seconds.")

uploaded_file = st.file_uploader("Upload your resume (PDF)", type="pdf")

if uploaded_file:
    with st.spinner("Uploading..."):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp.seek(0)
            filename = upload_to_s3(tmp) + ".pdf"
    st.success(f"Uploaded `{filename}` to S3. Processing in background...")

st.markdown("---")
st.subheader("📋 LinkedIn-Optimized Sections")
st.markdown("Wait 15 seconds after uploading and Refresh your page to show your formatted LinkedIn sections!")

profile_data = get_profile_data()

if profile_data:
    for section, content in profile_data.items():
        with st.expander(section):
            st.text_area(f"{section} Section", value=content, height=200, key=section)
else:
    st.info("No processed data found yet. Try again in a few seconds after uploading.")

st.markdown("---")
st.caption("🔒 Your data is private. This is a demo built on AWS services.")
