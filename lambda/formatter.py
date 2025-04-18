import json
import pymysql
import os
import urllib.request
import urllib.error
import concurrent.futures
import re

# Environment variables set in AWS Lambda
DB_HOST = os.environ['DB_HOST']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_NAME = os.environ['DB_NAME']
TOGETHER_API_KEY = os.environ['TOGETHER_API_KEY']

# Together.ai endpoint for chat-based completions
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"

# Optional: Create the LinkedIn profile sections table
def create_linkedin_profile_sections_table():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    with conn.cursor() as cursor:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS linkedin_profile_sections (
            id INT AUTO_INCREMENT PRIMARY KEY,
            section VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
    conn.commit()
    conn.close()

# Improved function to clean and standardize the output for most sections
def clean_output(content, section_type="general"):
    """
    Clean and standardize the output from the LLM to ensure consistent formatting:
    - Ensures each line is a proper bullet point
    - Standardizes capitalization and punctuation
    - Removes empty lines and redundant spaces
    - Ensures consistent ending periods
    - Special handling for education section
    - Special handling for experience section
    - Limits to appropriate number of bullet points based on section type
    """
    # If content is entirely "N/A", return it as is
    if content.strip().upper() == "N/A":
        return "N/A"
    
    # Special handling for education section
    if section_type.lower() == "education":
        return format_education_section(content)
    
    # Special handling for experience section
    if section_type.lower() == "experience":
        return format_experience_section(content)
    
    # Split the content into lines and process each one
    lines = content.strip().splitlines()
    cleaned_lines = []
    
    for line in lines:
        # Skip empty lines
        line = line.strip()
        if not line:
            continue
            
        # Remove any existing bullet points for consistency
        if line.startswith("- "):
            line = line[2:]
        elif line.startswith("• "):
            line = line[2:]
        elif line.startswith("* "):
            line = line[2:]
        elif line.startswith("-"):
            line = line[1:]
            
        # Capitalize first letter
        if line and len(line) > 0:
            line = line[0].upper() + line[1:]
            
        # Ensure proper ending punctuation
        if not line.endswith((".", "!", "?")):
            line = line.rstrip(".") + "."
            
        # Add consistent bullet point format
        line = "- " + line
        
        cleaned_lines.append(line)
    
    # Limit bullet points based on section type
    max_points = 20 if section_type.lower() == "experience" else 15
    if len(cleaned_lines) > max_points:
        cleaned_lines = cleaned_lines[:max_points]
    
    # Return the formatted content
    if not cleaned_lines:
        return "N/A"
    
    return "\n".join(cleaned_lines)

# Function to specifically format experience entries
def format_experience_section(content):
    """
    Specially formats experience section for LinkedIn:
    - Identifies and separates multiple job experiences
    - Preserves the hierarchy and structure of each job
    - Ensures proper bullet point formatting for responsibilities
    """
    # If content is N/A or empty, return N/A
    if content.strip().upper() == "N/A" or not content.strip():
        return "N/A"
    
    # Split by lines to identify different job experiences
    lines = content.strip().splitlines()
    formatted_entries = []
    current_entry = []
    
    # Company/position indicators that might signal a new experience entry
    new_entry_indicators = [
        "inc", "llc", "corp", "corporation", "co-op", "intern", "analyst", 
        "engineer", "manager", "director", "assistant", "specialist",
        "consultant", "associate", "laboratory", "lab", "company", "companies"
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Remove bullet points for processing
        if line.startswith("- "):
            line = line[2:]
        elif line.startswith("• "):
            line = line[2:]
        elif line.startswith("* "):
            line = line[2:]
        elif line.startswith("-"):
            line = line[1:]
        
        # Check if this line starts a new job experience
        # Look for company names, job titles, or locations
        is_new_entry = False
        
        # Check for patterns like "Company Name     Location"
        # or lines containing multiple capitalized words (likely a company/job title)
        if re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", line):
            capitalized_words = len(re.findall(r"\b[A-Z][a-z]+\b", line))
            if capitalized_words >= 2:
                # If we were building an entry, save it before starting new one
                if current_entry:
                    formatted_entries.append("\n".join(current_entry))
                    current_entry = []
                is_new_entry = True
        
        # Also check for common experience-related keywords
        if not is_new_entry:
            for indicator in new_entry_indicators:
                if indicator.lower() in line.lower():
                    # If we were building an entry, save it before starting new one
                    if current_entry:
                        formatted_entries.append("\n".join(current_entry))
                        current_entry = []
                    is_new_entry = True
                    break
        
        # Format the line appropriately
        if is_new_entry:
            # Format main experience line with proper formatting
            current_entry.append("- " + line)
        elif current_entry:
            # Format as a sub-bullet with proper capitalization and punctuation
            detail = line[0].upper() + line[1:] if line else line
            if not detail.endswith((".", "!", "?")):
                detail = detail.rstrip(".") + "."
            
            # Check if this is likely a date range or location (shorter line)
            if len(detail) < 30 and not re.search(r"[a-z]{10,}", detail.lower()):
                current_entry.append("  " + detail)
            else:
                current_entry.append("  - " + detail)
    
    # Add the last entry if exists
    if current_entry:
        formatted_entries.append("\n".join(current_entry))
    
    # If no entries were found, try basic formatting
    if not formatted_entries:
        return clean_output(content, "general")
        
    return "\n\n".join(formatted_entries)

# Function to specifically format education entries
def format_education_section(content):
    """
    Specially formats education section for LinkedIn:
    - Structures each education entry with institution, degree, and date
    - Adds relevant activities, honors, or coursework as sub-bullets
    - Ensures consistent formatting across multiple educational experiences
    """
    # If content is N/A or empty, return N/A
    if content.strip().upper() == "N/A" or not content.strip():
        return "N/A"
    
    # Split by lines to identify education entries
    lines = content.strip().splitlines()
    formatted_entries = []
    current_entry = []
    
    # Process education entries
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Remove bullet points for processing
        if line.startswith("- "):
            line = line[2:]
        elif line.startswith("• "):
            line = line[2:]
        elif line.startswith("* "):
            line = line[2:]
        elif line.startswith("-"):
            line = line[1:]
            
        # Check if this line starts a new education entry
        # A new entry typically contains university/college name or degree info
        new_entry_indicators = ["university", "college", "school", "institute", 
                                "bachelor", "master", "phd", "diploma", "certificate",
                                "b.s.", "b.a.", "m.s.", "m.a.", "mba"]
        
        is_new_entry = False
        for indicator in new_entry_indicators:
            if indicator.lower() in line.lower():
                # If we were building an entry, save it before starting new one
                if current_entry:
                    formatted_entries.append("\n".join(current_entry))
                    current_entry = []
                    
                # Format the main education line with proper capitalization
                # Extract and format degree, institution, and years if possible
                education_line = format_main_education_line(line)
                current_entry.append(education_line)
                is_new_entry = True
                break
                
        # If not a new entry, add as details to current entry
        if not is_new_entry and current_entry:
            # Format as a sub-bullet with proper capitalization and punctuation
            detail = line[0].upper() + line[1:] if line else line
            if not detail.endswith((".", "!", "?")):
                detail = detail.rstrip(".") + "."
            current_entry.append("  - " + detail)
    
    # Add the last entry if exists
    if current_entry:
        formatted_entries.append("\n".join(current_entry))
    
    # If no entries were found, try basic formatting
    if not formatted_entries:
        return clean_output(content, "general")
        
    return "\n\n".join(formatted_entries)

# Helper function to format the main education line
def format_main_education_line(line):
    """
    Format the main education line to highlight degree, institution and timeframe
    """
    # Capitalize important words and ensure proper ending
    words = line.split()
    capitalized_words = []
    
    for word in words:
        # Skip short prepositions, articles, and conjunctions
        if word.lower() in ["a", "an", "the", "in", "on", "at", "of", "for", "and", "or", "but"]:
            capitalized_words.append(word.lower())
        else:
            # Capitalize first letter, keep rest as is (preserves abbreviations like MBA, PhD)
            capitalized_words.append(word[0].upper() + word[1:] if word else word)
    
    formatted_line = " ".join(capitalized_words)
    
    # Ensure proper punctuation at the end
    if not formatted_line.endswith((".", "!", "?")):
        formatted_line = formatted_line.rstrip(".") + "."
        
    # Add the bullet point
    return "- " + formatted_line

# Function to format a section using Together.ai's Mistral model
def format_section(section, content):
    system_prompt = (
        "If a section is blank leave it as N/A. You are a professional resume-to-LinkedIn assistant. Your job is to reformat each resume section "
        "into LinkedIn-friendly language using:\n"
        "- First-person voice\n"
        "- Bullet points\n"
        "- Action verbs\n"
        "- A consistent and concise tone\n"
        "- No redundant phrasing (avoid starting all bullets with 'I')\n"
        "Avoid jargon unless necessary. Keep the format uniform across all sections.\n"
    )
    
    # Special handling for education section
    if section.lower() == "education":
        system_prompt += (
            "\nFor EDUCATION section specifically:\n"
            "- Format each institution with degree, field of study, and graduation year\n"
            "- Include relevant activities, honors, or coursework as sub-bullets\n"
            "- Lead with the most prestigious or recent education first\n"
            "- Highlight academic achievements, awards, or relevant projects\n"
            "- For example:\n"
            "  - Master of Business Administration, Harvard University (2018-2020)\n"
            "    - Graduated with honors, GPA 3.9/4.0\n"
            "    - President of Marketing Club\n"
            "  - Bachelor of Science in Computer Science, Stanford University (2014-2018)\n"
            "    - Dean's List all semesters\n"
            "    - Senior thesis on machine learning algorithms\n"
        )
    # Special handling for experience section
    elif section.lower() == "experience":
        system_prompt += (
            "\nFor EXPERIENCE section specifically:\n"
            "- IMPORTANT: Identify and preserve ALL separate job experiences (there may be multiple jobs)\n"
            "- For each job experience, format with company name, title, and date range\n"
            "- Keep each job's accomplishments as separate bullet points\n"
            "- Ensure descriptions focus on achievements and results, not just responsibilities\n"
            "- For example:\n"
            "  - Data Analyst at Tech Solutions Inc. (2018-2020)\n"
            "    - Implemented dashboards that increased sales team efficiency by 30%\n"
            "    - Led data migration project, reducing storage costs by $50K annually\n"
            "  - Junior Analyst at Research Corp. (2016-2018)\n"
            "    - Developed automated reports saving 10 hours of manual work weekly\n"
            "    - Collaborated with product team on feature prioritization\n"
        )
    else:
        system_prompt += (
            "\nExample format:\n"
            "- Developed and launched a new onboarding process, reducing ramp-up time by 25%\n"
            "- Collaborated with cross-functional teams to enhance product delivery\n"
            "- Leveraged data analysis to inform strategic decision-making\n"
        )

    user_prompt = f"Rewrite the following resume {section} section for LinkedIn:\n\n[{section.upper()}]\n{content}. Do not say something the student has not done"

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    payload = json.dumps({
        "model": "mistralai/Mistral-7B-Instruct-v0.1",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 512
    }).encode("utf-8")

    req = urllib.request.Request(TOGETHER_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as response:
            response_data = response.read()
            result = json.loads(response_data.decode("utf-8"))
            raw_output = result['choices'][0]['message']['content'].strip()
            return clean_output(raw_output, section.lower())

    except urllib.error.HTTPError as e:
        error_details = e.read().decode()
        return f"Error: {e.code} - {error_details}"
    except Exception as e:
        return f"Error: {str(e)}"

# Main Lambda function entry point
def lambda_handler(event, context):
    # Create table (only once)
    create_linkedin_profile_sections_table()

    # Connect to MySQL
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    with conn.cursor() as cursor:
        cursor.execute("SELECT section, content FROM resume_sections")
        rows = cursor.fetchall()

    # Run API calls in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        future_to_section = {
            executor.submit(format_section, section, content): (section, content)
            for section, content in rows
        }

        results = []
        for future in concurrent.futures.as_completed(future_to_section):
            section, content = future_to_section[future]
            try:
                formatted = future.result()
                results.append((section, formatted))
            except Exception as e:
                results.append((section, f"Error: {str(e)}"))

    # Insert into DB
    with conn.cursor() as cursor:
        for section, formatted in results:
            cursor.execute(
                "INSERT INTO linkedin_profile_sections (section, content) VALUES (%s, %s)",
                (section, formatted)
            )
    conn.commit()
    conn.close()

    return {
        'statusCode': 200,
        'body': json.dumps('All sections processed consistently and stored successfully.')
    }
