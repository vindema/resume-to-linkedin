# 💼 Resume to LinkedIn Formatter (Auto-Generated Profile Builder)

This project automatically extracts sections from an uploaded resume, reformats them into a LinkedIn-style profile using an LLM, and displays the result in a user-friendly Streamlit dashboard.

## 🧠 Tech Stack

- **Frontend:** Streamlit  
- **Backend:** AWS Lambda functions (2)  
- **Database:** Amazon RDS (MySQL)  
- **LLM:** Together AI Inference API (`mistralai/Mistral-7B-Instruct-v0.1`)  
- **Storage:** AWS S3 (for raw uploads, optional)  
- **Trigger Mechanism:** Lambda → Lambda chain via insert event  

---

## 🚀 Features

- Upload a resume (PDF/Text)
- Extract sections like Experience, Education, Projects, etc.
- Format each section for a professional LinkedIn profile
- View the auto-generated LinkedIn sections in Streamlit
- Database-backed pipeline with automatic reformatting

---

### 1. ✅ **IAM Role for Lambda**
Make sure your Lambda function has an IAM role with the following permissions:
- `AmazonTextractFullAccess`
- `AmazonS3ReadOnlyAccess`
- `AWSLambdaVPCAccessExecutionRole` (if accessing RDS in a VPC)

## MySQL 
- Create the following tables: 'resume_sections' and 'linkedin_profile_sections'

CREATE TABLE resume_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    section VARCHAR(255),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE linkedin_profile_sections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    section VARCHAR(100),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

# Install Dependencies
- pip install -r requirements.txt

# Setting Up the .env File
- Replace all the placeholder texts for each key in the .env file with the corresponding information

## How to Run The Project
- python3 -m venv venv
- source venv/bin/activate
- cd resume-to-linkedin
- streamlit run app.py --server.port 8501 --server.address 0.0.0.0
