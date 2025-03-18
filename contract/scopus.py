import spacy
import requests
from datetime import datetime

class ScopusPublicationsFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.elsevier.com/content/search/scopus"
        self.headers = {
            "X-ELS-APIKey": api_key,
            "Accept": "application/json"
        }
        # Load English language model for text processing
        self.nlp = spacy.load("en_core_web_sm")
        
    def format_citation_apa(self, pub):
        """Format publication in APA style"""
        try:
            authors = pub.get('authors', [])
            if not authors:
                authors_str = "No author"
            elif len(authors) > 5:
                authors_str = ', '.join(authors[:5]) + ' et al.'
            elif len(authors) == 1:
                authors_str = authors[0]
            else:
                authors_str = ', '.join(authors[:-1]) + ' & ' + authors[-1]
            
            year = pub.get('year', 'n.d.')
            title = pub.get('title', '')
            journal = pub.get('journal', '')
            volume = pub.get('volume', '')
            issue = pub.get('issue', '')
            pages = pub.get('pages', '')
            
            citation = f"{authors_str} ({year}). {title}"
            if journal:
                citation += f". {journal}"
                if volume:
                    citation += f", {volume}"
                    if issue:
                        citation += f"({issue})"
                if pages:
                    citation += f", {pages}"
            citation += "."
            
            return citation
        except Exception as e:
            print(f"Error formatting citation: {str(e)}")
            return f"Error formatting citation: {str(e)}"

    def fetch_publications(self, scopus_id):
        """Fetch publications for a given Scopus author ID"""
        try:
            params = {
                'query': f'AU-ID({scopus_id})',
                'field': 'dc:title,dc:creator,prism:publicationName,prism:volume,prism:issueIdentifier,prism:pageRange,prism:coverDate,prism:doi,citedby-count',
                'sort': '-coverDate',
                'count': 25,  # Reduced from 100 to stay within limits
                'start': 0    # Start from first result
            }
            
            print(f"Making request to Scopus API with params: {params}")
            
            response = requests.get(
                self.base_url,
                headers={
                    "X-ELS-APIKey": self.api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                params=params
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text[:500]}")
            
            if response.status_code != 200:
                raise Exception(f"API request failed with status code: {response.status_code}")
            
            data = response.json()
            
            if 'search-results' not in data:
                raise Exception("Invalid API response format")
            
            entries = data.get('search-results', {}).get('entry', [])
            print(f"Found {len(entries)} entries in response")
            
            publications = []
            
            for entry in entries:
                # Extract authors more carefully
                authors = []
                if 'author' in entry:
                    for author in entry['author']:
                        author_name = author.get('authname', '')
                        if author_name:
                            authors.append(author_name)
                
                pub_data = {
                    'title': entry.get('dc:title', ''),
                    'authors': authors,
                    'year': entry.get('prism:coverDate', '')[:4] if entry.get('prism:coverDate') else '',
                    'journal': entry.get('prism:publicationName', ''),
                    'volume': entry.get('prism:volume', ''),
                    'issue': entry.get('prism:issueIdentifier', ''),
                    'pages': entry.get('prism:pageRange', ''),
                    'citation_count': entry.get('citedby-count', '0'),
                    'doi': entry.get('prism:doi', '')
                }
                
                # Format citation in APA style
                pub_data['formatted_citation'] = self.format_citation_apa(pub_data)
                publications.append(pub_data)
            
            return publications
            
        except Exception as e:
            print(f"Error in fetch_publications: {str(e)}")
            raise Exception(f"Error fetching publications: {str(e)}") 