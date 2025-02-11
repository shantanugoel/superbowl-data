import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from typing import List, Dict
import time
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import json
import string

class SuperBowlAdScraper:
    def __init__(self):
        self.base_url = "https://www.superbowl-ads.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        self.data = []
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self.headers)
        return session

    def clean_brand_name(self, brand: str, year: str) -> str:
        """Clean brand name by removing year, punctuation and converting to uppercase."""
        # Remove the year if present
        brand = re.sub(rf'\b{year}\b', '', brand, flags=re.IGNORECASE)
        
        # Remove any text containing "Super Bowl" or variations
        brand = re.sub(r'\b(?:Super\s*Bowl|SB|Bowl)\s*(?:[IVXLC]+|\d+)?\b', '', brand, flags=re.IGNORECASE)
        
        # Remove all punctuation except ampersand
        translator = str.maketrans('', '', string.punctuation.replace('&', ''))
        brand = brand.translate(translator)
        
        # Convert to uppercase and clean extra whitespace
        brand = ' '.join(brand.upper().split())
        
        return brand

    def clean_title(self, text: str, year: str) -> tuple[str, str]:
        """Extract and clean brand and title from text."""
        # Skip if contains superbowl-ads.com in title
        if 'superbowl-ads.com' in text.lower():
            return None, None
            
        # Remove the year if it's at the start of the text
        text = re.sub(rf'^\s*{year}\s+', '', text, flags=re.IGNORECASE)
        
        # Try to extract brand and title using common patterns
        # Pattern 1: "Brand Name - Ad Title"
        # Pattern 2: "Brand Name: Ad Title"
        parts = re.split(r'[-:]', text, maxsplit=1)
        
        if len(parts) > 1:
            brand = parts[0].strip()
            title = parts[1].strip()
        else:
            # If no clear separator, try to extract brand from the beginning
            words = text.split()
            if len(words) < 3:  # Need at least brand (1-2 words) and title (1+ words)
                return None, None
            brand = ' '.join(words[:2])  # Assume first two words might be the brand
            title = ' '.join(words[2:])
        
        return brand, title

    def extract_video_info(self, url: str) -> Dict[str, str]:
        """Extract video URL and description from ad page."""
        try:
            soup = self.get_soup(url)
            
            # Try to find video URL
            video_url = None
            # Check for YouTube embed
            youtube_frame = soup.find('iframe', src=lambda x: x and 'youtube.com' in x)
            if youtube_frame:
                video_url = youtube_frame.get('src', '')
            else:
                # Check for video links
                video_links = soup.find_all('a', href=lambda x: x and any(vid in x.lower() for vid in ['youtube.com', 'vimeo.com']))
                if video_links:
                    video_url = video_links[0].get('href', '')
            
            # Try to find description
            description = ''
            content_div = soup.find('div', class_=['entry-content', 'post-content'])
            if content_div:
                # Get all paragraphs but exclude those that might be navigation or metadata
                paragraphs = [p.get_text().strip() for p in content_div.find_all('p')
                            if not any(x in p.get_text().lower() for x in ['previous post', 'next post', 'category'])]
                description = ' '.join(paragraphs)
            
            return {
                'video_url': video_url,
                'description': description
            }
        except Exception as e:
            print(f"Error extracting video info from {url}: {str(e)}")
            return {'video_url': None, 'description': ''}

    def get_soup(self, url: str) -> BeautifulSoup:
        """Fetch a URL and return BeautifulSoup object."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            # Sleep longer on error
            time.sleep(random.uniform(10, 15))
            raise

    def extract_year_links(self) -> List[Dict[str, str]]:
        """Extract links to all year pages."""
        soup = self.get_soup(self.base_url)
        year_links = []
        
        # Look for links containing years between 1998 and 2025
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text().strip()
            
            # Match only if the text is exactly a year number between 1998 and 2025
            if text.isdigit() and 1998 <= int(text) <= 2025:
                year = text
                full_url = urljoin(self.base_url, href)
                year_links.append({
                    'year': year,
                    'url': full_url
                })
        
        return sorted(year_links, key=lambda x: x['year'], reverse=True)

    def extract_ads_from_year_page(self, year: str, url: str):
        """Extract ad information from a year page."""
        print(f"Scraping year {year} from {url}")
        try:
            soup = self.get_soup(url)
            
            # Find all article items
            articles = soup.find_all('article', class_='cactus-post-item')
            
            for article in articles:
                # Find the title element within the article
                title_elem = article.find(['h2', 'h3', 'h4', 'div'], class_=['entry-title', 'post-title'])
                if not title_elem:
                    continue
                
                # Get the link to the ad page
                link_tag = title_elem.find('a', href=True)
                if not link_tag:
                    continue
                
                text = title_elem.get_text().strip()
                ad_url = urljoin(self.base_url, link_tag.get('href', ''))
                
                # Skip if text is too short
                if len(text) < 5:
                    continue
                
                # Skip "Most Memorable Super Bowl Ads"
                if text.lower().startswith('most memorable super bowl ads'):
                    continue
                
                # Clean and extract brand and title
                brand, title = self.clean_title(text, year)
                if not brand or not title:
                    continue
                
                # Clean up the brand name
                brand = self.clean_brand_name(brand, year)
                title = title.strip()
                
                if brand and title:
                    # Get additional information from the ad page
                    print(f"  Fetching details for {brand} ad...")
                    video_info = self.extract_video_info(ad_url)
                    
                    self.data.append({
                        'year': year,
                        'brand': brand,
                        'title': title,
                        'page_url': ad_url,
                        'video_url': video_info['video_url'],
                        'description': video_info['description']
                    })
            
        except Exception as e:
            print(f"Error scraping year {year}: {str(e)}")
        
        # Random delay between requests to be more polite
        time.sleep(random.uniform(3, 7))

    def scrape(self):
        """Main scraping method."""
        try:
            year_links = self.extract_year_links()
            total_years = len(year_links)
            
            for i, year_info in enumerate(year_links, 1):
                try:
                    print(f"\nProcessing year {year_info['year']} ({i}/{total_years})")
                    self.extract_ads_from_year_page(year_info['year'], year_info['url'])
                except Exception as e:
                    print(f"Failed to scrape year {year_info['year']}: {str(e)}")
                    continue
            
            # Save to JSON
            if self.data:
                # Remove duplicates while preserving order
                seen = set()
                unique_data = []
                for item in self.data:
                    key = (item['year'], item['brand'], item['title'])
                    if key not in seen:
                        seen.add(key)
                        unique_data.append(item)
                
                with open('superbowl_ads.json', 'w', encoding='utf-8') as f:
                    json.dump(unique_data, f, indent=2, ensure_ascii=False)
                print(f"\nScraped {len(unique_data)} ads and saved to superbowl_ads.json")
            else:
                print("\nNo data was collected. Please check the error messages above.")
        
        except Exception as e:
            print(f"Fatal error during scraping: {str(e)}")

if __name__ == "__main__":
    scraper = SuperBowlAdScraper()
    scraper.scrape() 