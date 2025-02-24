from transformers import pipeline
import re

def extract_resume_data(file_path):
    # Load the NER pipeline
    ner_pipeline = pipeline("ner", model="dslim/bert-base-NER", grouped_entities=True)

    # Read the resume file
    with open(file_path, 'r', encoding='utf-8') as f:
        resume_text = f.read()

    # Extract entities
    entities = ner_pipeline(resume_text)
    extracted_data = {
        "name": None,
        "email": None,
        "phone_number": None,
        "skills": [],
    }

    # Parse entities
    for entity in entities:
        if entity["entity_group"] == "PER":
            extracted_data["name"] = entity["word"]
        elif entity["entity_group"] == "EMAIL":
            extracted_data["email"] = entity["word"]
        elif entity["entity_group"] == "PHONE":
            extracted_data["phone_number"] = entity["word"]
        elif entity["entity_group"] == "SKILL":
            extracted_data["skills"].append(entity["word"])

    # Format phone number (optional)
    if extracted_data["phone_number"]:
        extracted_data["phone_number"] = re.sub(r'\D', '', extracted_data["phone_number"])

    return extracted_data
