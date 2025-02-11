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
            
            # Find all potential ad entries
            ad_entries = soup.find_all(['h2', 'h3', 'h4']) + soup.find_all('div', class_='entry-title')
            
            for entry in ad_entries:
                text = entry.get_text().strip()
                
                # Skip if text is too short or doesn't look like an ad title
                if len(text) < 5 or text.isdigit():
                    continue
                
                # Try to extract brand and title
                # Common patterns: "Brand Name - Ad Title" or "Brand Name: Ad Title"
                parts = re.split(r'[-:]', text, maxsplit=1)
                
                if len(parts) > 1:
                    brand = parts[0].strip()
                    title = parts[1].strip()
                else:
                    # If no clear separator, try to extract brand from the beginning
                    words = text.split()
                    brand = ' '.join(words[:2])  # Assume first two words might be the brand
                    title = ' '.join(words[2:])
                
                # Clean up the data
                brand = re.sub(r'\s+', ' ', brand).strip()
                title = re.sub(r'\s+', ' ', title).strip()
                
                if brand and title:
                    self.data.append({
                        'year': year,
                        'brand': brand,
                        'title': title
                    })
            
        except Exception as e:
            print(f"Error scraping year {year}: {str(e)}")
        
        # Random delay between requests to be more polite
        time.sleep(random.uniform(3, 7))

    def scrape(self):
        """Main scraping method."""
        try:
            year_links = self.extract_year_links()
            
            for year_info in year_links:
                try:
                    self.extract_ads_from_year_page(year_info['year'], year_info['url'])
                except Exception as e:
                    print(f"Failed to scrape year {year_info['year']}: {str(e)}")
                    continue
            
            # Convert to DataFrame and save to CSV
            if self.data:
                df = pd.DataFrame(self.data)
                df = df.drop_duplicates()
                df.to_csv('superbowl_ads.csv', index=False)
                print(f"Scraped {len(df)} ads and saved to superbowl_ads.csv")
            else:
                print("No data was collected. Please check the error messages above.")
        
        except Exception as e:
            print(f"Fatal error during scraping: {str(e)}")

if __name__ == "__main__":
    scraper = SuperBowlAdScraper()
    scraper.scrape() 