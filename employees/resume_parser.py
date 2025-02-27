import spacy
import re
from PyPDF2 import PdfReader
from employees.models import Employee
from django.forms.models import model_to_dict

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
    """Parse resume PDF and extract employee-related fields."""
    try:
        print(f"Starting to parse resume from: {pdf_file}")  # Debug print
        
        # Extract text from PDF
        resume_text = extract_text_from_pdf(pdf_file)
        print(f"Extracted text (first 100 chars): {resume_text[:100]}")  # Debug print
        doc = nlp(resume_text)

        # Initialize parsed data
        parsed_data = {
            'first_name': '',
            'last_name': '',
            'email': '',
            'phone_number': '',
            'address': '',
            'ic_no': ''
        }

        # Regular expressions for common patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'(?:\+?(\d{1,3}[-.\s]?)?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        ic_pattern = r'\b\d{2}[-.]?\d{6}\b'

        # Extract email
        emails = re.findall(email_pattern, resume_text)
        print("Found emails:", emails)
        if emails:
            parsed_data['email'] = emails[0]

        # Extract phone number
        phones = re.findall(phone_pattern, resume_text)
        print("Found phones:", phones)
        if phones:
            parsed_data['phone_number'] = phones[0]

        # Extract IC number
        ic_numbers = re.findall(ic_pattern, resume_text)
        print("Found IC numbers:", ic_numbers)
        if ic_numbers:
            parsed_data['ic_no'] = ic_numbers[0]

        # Extract name and address using spaCy
        print("Found entities:", [(ent.text, ent.label_) for ent in doc.ents])
        for ent in doc.ents:
            if ent.label_ == "PERSON" and not parsed_data['first_name']:
                name_parts = ent.text.split()
                if len(name_parts) >= 2:
                    parsed_data['first_name'] = name_parts[0]
                    parsed_data['last_name'] = ' '.join(name_parts[1:])
                    print(f"Found name: {parsed_data['first_name']} {parsed_data['last_name']}")
            elif ent.label_ in ["GPE", "LOC"]:
                if parsed_data['address']:
                    parsed_data['address'] += f", {ent.text}"
                else:
                    parsed_data['address'] = ent.text
                print(f"Found address part: {ent.text}")

        # Remove any empty values
        parsed_data = {k: v for k, v in parsed_data.items() if v}
        
        print(f"Final parsed data: {parsed_data}")  # Debug print
        return parsed_data

    except Exception as e:
        print(f"Error in parse_resume: {str(e)}")  # Debug print
        return {}

