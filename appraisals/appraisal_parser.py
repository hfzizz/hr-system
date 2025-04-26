import spacy
import re
from PyPDF2 import PdfReader
from .models import Appraisal  # Import your Appraisal model

nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def parse_appraisal(pdf_file):
    """Parse appraisal PDF and extract relevant fields."""
    try:
        # Extract text from PDF
        appraisal_text = extract_text_from_pdf(pdf_file)
        doc = nlp(appraisal_text)

        # Initialize parsed data structure
        parsed_data = {
            'section_a': {
                'achievements': [],
                'goals': [],
                'challenges': [],
            },
            'section_b': {
                'ratings': {},
                'comments': {},
            },
            'section_c': {
                'development_needs': [],
                'training_requirements': [],
                'career_aspirations': '',
            }
        }

        # Define section markers/headers
        sections = {
            'achievements': r'achievements?|accomplishments?|completed tasks',
            'goals': r'goals?|objectives?|targets?|plans?',
            'challenges': r'challenges?|difficulties?|obstacles?',
            'development': r'development needs?|areas for improvement',
            'training': r'training|learning|development requirements?',
            'career': r'career aspirations?|career goals?|future plans?'
        }

        # Process text by sections
        current_section = None
        current_content = []

        for line in appraisal_text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check for section headers
            section_found = False
            for section, pattern in sections.items():
                if re.search(pattern, line.lower()):
                    # Save previous section content
                    if current_section and current_content:
                        if current_section in ['achievements', 'goals', 'challenges']:
                            parsed_data['section_a'][current_section].extend(current_content)
                        elif current_section in ['development', 'training']:
                            parsed_data['section_c'][f'{current_section}_needs'].extend(current_content)
                        elif current_section == 'career':
                            parsed_data['section_c']['career_aspirations'] = ' '.join(current_content)

                    # Start new section
                    current_section = section
                    current_content = []
                    section_found = True
                    break

            if not section_found and current_section:
                current_content.append(line)

        # Extract ratings (assuming format like "Rating X: Y" or "X Rating: Y")
        rating_pattern = r'([\w\s]+)rating:?\s*(\d+(?:\.\d+)?)'
        ratings = re.finditer(rating_pattern, appraisal_text, re.IGNORECASE)
        for match in ratings:
            category = match.group(1).strip().lower()
            rating = float(match.group(2))
            parsed_data['section_b']['ratings'][category] = rating

        # Extract comments (assuming format like "Comments: ..." or "Remarks: ...")
        comment_pattern = r'(?:comments?|remarks?):\s*([^.]*(?:\.[^.]*)*)'
        comments = re.finditer(comment_pattern, appraisal_text, re.IGNORECASE)
        for match in comments:
            comment = match.group(1).strip()
            if comment:
                parsed_data['section_b']['comments']['general'] = comment

        return parsed_data

    except Exception as e:
        print(f"Error parsing appraisal: {str(e)}")
        return {}
