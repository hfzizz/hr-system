from transformers import pipeline

# Use a lightweight model
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")

def summarize_text(text, min_length=70, max_length=300):
    return summarizer(text, min_length=min_length, max_length=max_length, do_sample=False)[0]['summary_text']
