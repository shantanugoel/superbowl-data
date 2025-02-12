import json
import google.generativeai as genai
import time
from typing import Dict, Any
import os
from tqdm import tqdm
import argparse

# Configure Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY environment variable")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def create_gemini_prompt(ad_data: Dict[str, Any]) -> str:
    """Create a prompt for Gemini based on the ad data."""
    video_info = ""
    if ad_data.get('video_url'):
        video_info = f"\nVideo URL: {ad_data['video_url']}\nPlease watch this video and base your analysis primarily on the video content."
    
    prompt = f"""Analyze this Super Bowl advertisement and provide a JSON response:{video_info}

Title: {ad_data['title']}
Brand: {ad_data['brand']}
Year: {ad_data['year']}
Original Title: {ad_data['original_title']}
Description: {ad_data['description']}

Based on the above information and the video content (if available), create a JSON response with exactly these three fields:
1. A concise summary of the ad in 100 words or less (focus on describing what actually happens in the video if available)
2. The primary product/industry category (choose one: Automotive, Food & Beverage, Technology, Entertainment, Financial Services, Retail, Telecommunications, Consumer Goods, Healthcare, Travel, Sports & Fitness, Other)
3. Exactly 3 theme tags (choose from: Humor, Celebrity, Emotional, Action, Family, Animals, Innovation, Nostalgia, Music, Sports, Suspense, Social Message, Patriotic, Cinematic, Fantasy)

Respond ONLY with a valid JSON object in this exact format, no other text:
{{"summary": "your 100-word summary here", "category": "chosen category here", "theme_tags": ["tag1", "tag2", "tag3"]}}"""
    return prompt

def extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract JSON from Gemini response text."""
    try:
        # Try to find JSON-like content between curly braces
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json.loads(json_str)
        raise ValueError("No JSON content found in response")
    except Exception as e:
        raise ValueError(f"Failed to parse JSON: {str(e)}")

def process_with_gemini(ad_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single ad with Gemini API and handle retries."""
    max_retries = 3
    
    # Clean up video URL if present
    if ad_data.get('video_url'):
        # Convert embed URLs to watch URLs for better Gemini processing
        video_url = ad_data['video_url']
        if 'youtube.com/embed/' in video_url:
            video_id = video_url.split('/embed/')[-1].split('?')[0]
            ad_data['video_url'] = f'https://www.youtube.com/watch?v={video_id}'
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(create_gemini_prompt(ad_data))
            
            # Extract and parse the JSON response
            gemini_data = extract_json_from_response(response.text)
            
            # Validate the response format
            required_keys = {'summary', 'category', 'theme_tags'}
            if not all(key in gemini_data for key in required_keys):
                raise ValueError("Missing required keys in Gemini response")
            if not isinstance(gemini_data['theme_tags'], list) or len(gemini_data['theme_tags']) != 3:
                raise ValueError("Theme tags must be exactly 3")
            
            # Validate category
            valid_categories = {
                'Automotive', 'Food & Beverage', 'Technology', 'Entertainment',
                'Financial Services', 'Retail', 'Telecommunications', 'Consumer Goods',
                'Healthcare', 'Travel', 'Sports & Fitness', 'Other'
            }
            if gemini_data['category'] not in valid_categories:
                raise ValueError(f"Invalid category: {gemini_data['category']}")
            
            # Validate theme tags
            valid_tags = {
                'Humor', 'Celebrity', 'Emotional', 'Action', 'Family', 'Animals',
                'Innovation', 'Nostalgia', 'Music', 'Sports', 'Suspense',
                'Social Message', 'Patriotic', 'Cinematic', 'Fantasy'
            }
            if not all(tag in valid_tags for tag in gemini_data['theme_tags']):
                raise ValueError("Invalid theme tags")
            
            return gemini_data
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"\nFailed to process ad: {ad_data['title']}")
                print(f"Error: {str(e)}")
                return {
                    'summary': ad_data.get('description', ''),
                    'category': 'Other',
                    'theme_tags': ['Unknown', 'Unknown', 'Unknown']
                }
            time.sleep(2 ** attempt)  # Exponential backoff

def needs_update(ad: Dict[str, Any]) -> bool:
    """Check if an ad needs to be updated."""
    # Check if description is empty or very short
    if not ad.get('description') or len(ad['description'].strip()) < 10:
        return True
    
    # Check if any theme tags are Unknown
    if 'theme_tags' not in ad or 'Unknown' in ad['theme_tags']:
        return True
    
    # Check if category is Other or missing
    if 'category' not in ad or ad['category'] == 'Other':
        return True
    
    return False

def enhance_data(input_file: str = 'superbowl_ads.json', output_file: str = 'enhanced_superbowl_ads.json', update_missing: bool = False):
    """Enhance the scraped data with Gemini-generated insights."""
    # Load the data
    if update_missing and os.path.exists(output_file):
        print(f"Loading existing enhanced data from {output_file}")
        with open(output_file, 'r', encoding='utf-8') as f:
            ads_data = json.load(f)
        
        # Filter ads that need updating
        ads_to_update = [i for i, ad in enumerate(ads_data) if needs_update(ad)]
        if not ads_to_update:
            print("No ads need updating.")
            return
        
        print(f"Found {len(ads_to_update)} ads that need updating")
        
        # Process only ads that need updating
        for idx in tqdm(ads_to_update, desc="Processing ads"):
            gemini_insights = process_with_gemini(ads_data[idx])
            
            # Update the existing ad data
            ads_data[idx].update({
                'description': gemini_insights['summary'],
                'category': gemini_insights['category'],
                'theme_tags': gemini_insights['theme_tags']
            })
            
            # Be nice to the API
            time.sleep(1)
    else:
        # Load original data for full processing
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
        
        ads_data = enhanced_data
    
    # Save enhanced data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ads_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessed ads and saved to {output_file}")
    
    # Print some statistics
    categories = {}
    tags = {}
    for ad in ads_data:
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
    parser = argparse.ArgumentParser(description='Enhance Super Bowl ads data using Gemini API')
    parser.add_argument('--missing', action='store_true', help='Update only ads with missing or unknown data')
    args = parser.parse_args()
    
    enhance_data(update_missing=args.missing) 