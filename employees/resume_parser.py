import spacy
import re
import json
from PyPDF2 import PdfReader
from employees.models import Employee
from django.forms.models import model_to_dict
from django.db.models import JSONField

# Load the spaCy NER model
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def parse_resume(pdf_file):
    """Parse resume PDF and extract employee-related fields in JSONB format."""
    try:
        print("\n=== Resume Parser ===")
        print(f"Starting to parse resume from: {pdf_file}")
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(pdf_file)
        print(f"Extracted text length: {len(resume_text)}")
        print(f"First 500 chars of text: {resume_text[:500]}")
        
        doc = nlp(resume_text)
        print(f"Created spaCy document with {len(doc)} tokens")

        # Initialize parsed data in JSONB format
        parsed_data = {
            'personal_info': {
                'first_name': '',
                'last_name': '',
                'email': '',
                'phone_number': '',
                'address': '',
                'ic_no': '',
                'date_of_birth': '',
                'gender': ''
            },
            'education': [],
            'experience': [],
            'skills': [],
            'employment': {
                'department': '',
                'post': '',
                'appointment_type': '',
                'employee_status': '',
                'hire_date': '',
                'salary': ''
            },
            'documents': [],
            'qualifications': []
        }

        # Regular expressions for common patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'(\+?\d[\d\s().-]{7,}\d)'
        ic_pattern = r'\b\d{2}[-.]?\d{6}\b|\b\d{8}\b|(?i)\b(?:ic|nric|id)\s*[:#]?\s*(\d{2}[-.]?\d{6}|\d{8})\b'
        date_pattern = r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'

        # Extract email
        emails = re.findall(email_pattern, resume_text)
        print(f"Found emails: {emails}")
        if emails:
            parsed_data['personal_info']['email'] = emails[0]

        # Extract phone number
        phones = re.findall(phone_pattern, resume_text)
        print(f"Found phones: {phones}")
        if phones:
            parsed_data['personal_info']['phone_number'] = phones[0]

        # Extract IC number
        ic_numbers = re.findall(ic_pattern, resume_text)
        print(f"Found IC numbers: {ic_numbers}")
        if ic_numbers:
            parsed_data['personal_info']['ic_no'] = ic_numbers[0]

        # Extract dates (potential birth dates)
        dates = re.findall(date_pattern, resume_text)
        print(f"Found dates: {dates}")
        if dates:
            parsed_data['personal_info']['date_of_birth'] = dates[0]

        # Extract name and address using spaCy
        print("\nFound entities:")
        for ent in doc.ents:
            print(f"- {ent.text} ({ent.label_})")
            if ent.label_ == "PERSON" and not parsed_data['personal_info']['first_name']:
                name_parts = ent.text.split()
                if len(name_parts) >= 2:
                    parsed_data['personal_info']['first_name'] = name_parts[0]
                    parsed_data['personal_info']['last_name'] = ' '.join(name_parts[1:])
                    print(f"Extracted name: {name_parts[0]} {' '.join(name_parts[1:])}")
            elif ent.label_ in ["GPE", "LOC"]:
                if parsed_data['personal_info']['address']:
                    parsed_data['personal_info']['address'] += f", {ent.text}"
                else:
                    parsed_data['personal_info']['address'] = ent.text
                print(f"Added address part: {ent.text}")

        # Extract education information
        education_sections = re.findall(r'(?i)education.*?(?=\n\n|\Z)', resume_text, re.DOTALL)
        print(f"\nFound {len(education_sections)} education sections")
        for section in education_sections:
            print(f"Education section text: {section[:200]}")
            education_entry = {
                'institution': '',
                'degree': '',
                'field_of_study': '',
                'start_date': '',
                'end_date': '',
                'grade': ''
            }
            parsed_data['education'].append(education_entry)

        # Extract work experience
        experience_sections = re.findall(r'(?i)experience.*?(?=\n\n|\Z)', resume_text, re.DOTALL)
        print(f"\nFound {len(experience_sections)} experience sections")
        for section in experience_sections:
            print(f"Experience section text: {section[:200]}")
            experience_entry = {
                'company': '',
                'position': '',
                'start_date': '',
                'end_date': '',
                'description': ''
            }
            parsed_data['experience'].append(experience_entry)

        # Extract skills
        skills_sections = re.findall(r'(?i)skills.*?(?=\n\n|\Z)', resume_text, re.DOTALL)
        print(f"\nFound {len(skills_sections)} skills sections")
        for section in skills_sections:
            skills = re.findall(r'[A-Za-z0-9\s]+(?=,|\n|$)', section)
            parsed_data['skills'].extend([skill.strip() for skill in skills])
            print(f"Extracted skills: {skills}")

        # Remove any empty values from personal_info
        parsed_data['personal_info'] = {k: v for k, v in parsed_data['personal_info'].items() if v}
        
        # Convert to JSONB-compatible format
        jsonb_data = json.dumps(parsed_data)
        
        print("\nFinal parsed data:")
        print(json.dumps(parsed_data, indent=2))
        return parsed_data

    except Exception as e:
        print(f"Error in parse_resume: {str(e)}")
        return {}

