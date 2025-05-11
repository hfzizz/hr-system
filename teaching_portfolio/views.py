from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import TeachingPortfolioForm
from .models import TeachingPortfolio
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import os
import tempfile
import re
import logging
import pdfplumber
from transformers import pipeline
import json
from .nlp_utils import summarize_text

logger = logging.getLogger(__name__)
logger.warning("parse_pdf view called")

# Load the summarization pipeline once (at module level for efficiency)
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

class TeachingFormView(LoginRequiredMixin, TemplateView):
    template_name = 'teaching_portfolio/form.html'

@login_required
def teaching_portfolio_form(request):
    portfolio, created = TeachingPortfolio.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = TeachingPortfolioForm(request.POST, instance=portfolio)
        if form.is_valid():
            form.save()
            messages.success(request, "Teaching Portfolio saved successfully!")
            return redirect('teaching_portfolio:list')
    else:
        form = TeachingPortfolioForm(instance=portfolio)
    return render(request, 'teaching_portfolio/form.html', {'form': form})

def extract_section(keyword, text):
    # Match until the next lettered subsection (b), c), etc.) or end of text
    pattern = rf"{re.escape(keyword)}\s*\n(.*?)(?=\n[a-z]\)|$)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""

@csrf_exempt
@require_POST
def parse_pdf(request):
    logger.warning("parse_pdf view called")
    if 'pdf' not in request.FILES:
        return JsonResponse({'status': 'error', 'message': 'No PDF file provided'}, status=400)
    pdf_file = request.FILES['pdf']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        for chunk in pdf_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
        logger.warning(f"Saved PDF to: {tmp_path}, size: {os.path.getsize(tmp_path)}")

    try:
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                logger.warning(f"Extracted page text: {page_text}")
                if page_text:
                    text += page_text + "\n"
        logger.warning(f"Full extracted text: {text[:500]}")  # Log first 500 chars

        # Now extract sections
        parsed_data = {
            # 1. Teaching Philosophy
            'teaching_philosophy_full': extract_section("1. Teaching Philosophy", text),

            # 2. Strategies, Objective, Methodology
            'learning_outcome_full': extract_section("a) Learning outcome (identify the learning outcomes you expect your students to achieve).", text),
            'instructional_methodology_full': extract_section("b) Instructional methodology (including the use of e-learning or experiential learning projects).", text),
            'other_means_to_enhance_learning_full': extract_section("c) Other means to enhance learning.", text),

            # 3. Teaching History - Other Teaching
            'other_teaching_full': extract_section("c) Other teaching (e.g. Lifelong Learning, in-service, EDPMMO, EDPSGO, etc). Please provide details.", text),

            # 4. Teaching Performance Indicators
            'academic_leadership_full': extract_section("4. Teaching Achievement and Academic Leadership", text),
            'contribution_teaching_materials_full': extract_section("b) Contribution to development of teaching materials (including published cases, textbooks, production of teaching materials, software, pedagogical articles, teaching methodologies, etc)", text),

            # 5. Future Plan
            'future_teaching_goals_full': extract_section("a) Teaching goals for the next 3 years", text),
            'future_steps_improve_teaching_full': extract_section("b) Steps taken to improve teaching", text),
        }

        return JsonResponse({'status': 'success', 'data': parsed_data, 'raw_text': text})
    except Exception as e:
        logger.error("Exception occurred: %s", e, exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    finally:
        os.remove(tmp_path)

def extract_text_pdfplumber(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

@csrf_exempt
@require_POST
def summarize_text_view(request):
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        if not text:
            return JsonResponse({'status': 'error', 'message': 'No text provided'}, status=400)
        summary = summarize_text(text)
        return JsonResponse({'status': 'success', 'summary': summary})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)