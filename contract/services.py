import spacy
import logging
from pprint import pformat

logger = logging.getLogger(__name__)

class ResearchStatusTracker:
    def __init__(self):
        # Load the English language model
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            # If model not found, download it
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
            self.nlp = spacy.load('en_core_web_sm')

    def compare_research_items(self, text1, text2):
        """Compare two research items using Spacy's similarity"""
        try:
            # Process both texts
            doc1 = self.nlp(text1.lower())
            doc2 = self.nlp(text2.lower())
            
            # Calculate similarity (0 to 1 score)
            similarity = doc1.similarity(doc2)
            
            # Consider items similar if similarity > 0.85
            result = similarity > 0.85
            
            # Debug output
            print(f"\nComparing Research Items:")
            print(f"Text 1: {text1}")
            print(f"Text 2: {text2}")
            print(f"Similarity Score: {similarity}")
            print(f"Match Result: {result}")
            
            return result

        except Exception as e:
            logger.error(f"Spacy error: {e}")
            # Fallback to simple string comparison
            return text1.lower() == text2.lower()

    def process_research_status(self, appraisals):
        """Process research items from all appraisals"""
        print("\n=== Starting Research Status Processing ===")
        research_tracker = {}
        
        # Sort appraisals by date
        sorted_appraisals = sorted(appraisals, key=lambda x: x.date_created)
        
        for appraisal in sorted_appraisals:
            print(f"\nProcessing Appraisal from {appraisal.date_created.date()}")
            
            # Get research items
            ongoing = self._parse_research_items(appraisal.ongoing_research)
            history = self._parse_research_items(appraisal.last_research)
            
            print(f"Found Ongoing Research Items: {ongoing}")
            print(f"Found History Research Items: {history}")
            
            # Update status
            self._update_research_status(research_tracker, ongoing, history, appraisal.date_created)
            
            print("\nCurrent Research Tracker State:")
            for item, data in research_tracker.items():
                print(f"- {item}: {data['status']} (Last Updated: {data['last_updated'].date()})")

        result = self._format_research_output(research_tracker)
        
        print("\n=== Final Research Status ===")
        print("History Research:")
        print(result['history_research'] or "None")
        print("\nOngoing Research:")
        print(result['ongoing_research'] or "None")
        print("\n===============================")
        
        return result

    def _parse_research_items(self, text):
        if not text:
            return []
        items = [item.strip() for item in text.split('\n') if item.strip()]
        return items

    def _update_research_status(self, tracker, ongoing_items, history_items, date):
        print("\nUpdating Research Status:")
        
        # Process history items first
        for history_item in history_items:
            print(f"\nProcessing History Item: {history_item}")
            self._process_single_item(tracker, history_item, 'history', date)

        # Then process ongoing items
        for ongoing_item in ongoing_items:
            print(f"\nProcessing Ongoing Item: {ongoing_item}")
            self._process_single_item(tracker, ongoing_item, 'ongoing', date)

    def _process_single_item(self, tracker, item, status, date):
        matched = False
        for existing_item in list(tracker.keys()):
            print(f"Comparing with existing item: {existing_item}")
            if self.compare_research_items(item, existing_item):
                if date > tracker[existing_item]['last_updated']:
                    old_status = tracker[existing_item]['status']
                    tracker[existing_item]['status'] = status
                    tracker[existing_item]['last_updated'] = date
                    print(f"Updated status from {old_status} to {status}")
                else:
                    print(f"Keeping existing status as date is not newer")
                matched = True
                break
        
        if not matched:
            tracker[item] = {
                'status': status,
                'last_updated': date
            }
            print(f"Added new item with status: {status}")

    def _format_research_output(self, tracker):
        history_research = []
        ongoing_research = []
        
        for item, data in tracker.items():
            if data['status'] == 'history':
                history_research.append(item)
            else:
                ongoing_research.append(item)
                
        return {
            'history_research': '\n'.join(history_research),
            'ongoing_research': '\n'.join(ongoing_research)
        }