import json
import google.generativeai as genai
import time
from typing import Dict, Any
import os
from tqdm import tqdm

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY environment variable")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def create_gemini_prompt(ad_data: Dict[str, Any]) -> str:
    """Create a prompt for Gemini based on the ad data."""
    return f"""Analyze this Super Bowl advertisement:

Title: {ad_data['title']}
Brand: {ad_data['brand']}
Year: {ad_data['year']}
Original Title: {ad_data['original_title']}
Description: {ad_data['description']}

Please provide the following in a JSON format:
1. A concise summary of the ad in 100 words or less
2. The primary product/industry category (use a consistent category from this list: Automotive, Food & Beverage, Technology, Entertainment, Financial Services, Retail, Telecommunications, Consumer Goods, Healthcare, Travel, Sports & Fitness, or Other)
3. Exactly 3 theme tags from this predefined set: Humor, Celebrity, Emotional, Action, Family, Animals, Innovation, Nostalgia, Music, Sports, Suspense, Social Message, Patriotic, Cinematic, Fantasy

Format your response as valid JSON with these exact keys:
{
    "summary": "your summary here",
    "category": "category here",
    "theme_tags": ["tag1", "tag2", "tag3"]
}"""

def process_with_gemini(ad_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single ad with Gemini API and handle retries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(create_gemini_prompt(ad_data))
            # Parse the JSON response
            gemini_data = json.loads(response.text)
            
            # Validate the response format
            required_keys = {'summary', 'category', 'theme_tags'}
            if not all(key in gemini_data for key in required_keys):
                raise ValueError("Missing required keys in Gemini response")
            if len(gemini_data['theme_tags']) != 3:
                raise ValueError("Theme tags must be exactly 3")
            
            return gemini_data
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to process ad {ad_data['title']} after {max_retries} attempts: {str(e)}")
                return {
                    'summary': ad_data.get('description', ''),
                    'category': 'Other',
                    'theme_tags': ['Unknown', 'Unknown', 'Unknown']
                }
            time.sleep(2 ** attempt)  # Exponential backoff

def enhance_data(input_file: str = 'superbowl_ads.json', output_file: str = 'enhanced_superbowl_ads.json'):
    """Enhance the scraped data with Gemini-generated insights."""
    # Load the original data
    with open(input_file, 'r', encoding='utf-8') as f:
        ads_data = json.load(f)
    
    # Process each ad with Gemini
    enhanced_data = []
    for ad in tqdm(ads_data, desc="Processing ads"):
        gemini_insights = process_with_gemini(ad)
        
        # Create enhanced ad data
        enhanced_ad = ad.copy()
        enhanced_ad.update({
            'description': gemini_insights['summary'],
            'category': gemini_insights['category'],
            'theme_tags': gemini_insights['theme_tags']
        })
        enhanced_data.append(enhanced_ad)
        
        # Be nice to the API
        time.sleep(1)
    
    # Save enhanced data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessed {len(enhanced_data)} ads and saved to {output_file}")
    
    # Print some statistics
    categories = {}
    tags = {}
    for ad in enhanced_data:
        categories[ad['category']] = categories.get(ad['category'], 0) + 1
        for tag in ad['theme_tags']:
            tags[tag] = tags.get(tag, 0) + 1
    
    print("\nCategory Distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"{cat}: {count}")
    
    print("\nTop Theme Tags:")
    for tag, count in sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"{tag}: {count}")

if __name__ == "__main__":
    enhance_data() 