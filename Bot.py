import os
import json
import random
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- CONFIGURATION & SECRETS ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")

genai.configure(api_key=GEMINI_API_KEY)

def generate_news():
    """Uses Google Gemini to generate a satirical historical news report."""
    print("Generating news with Gemini...")
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
    You are a satirical news generator. Pick a random famous historical event from anywhere in the world and any timeline (e.g., Julius Caesar's assassination, invention of the wheel, building of the pyramids, sinking of Titanic, fall of Troy).
    Act as if it literally JUST happened today as breaking news.
    
    Respond STRICTLY in JSON format with these exact three keys:
    1. "headline": A sensational, punchy breaking news headline (under 80 characters).
    2. "description": A witty, sarcastic Facebook post description reporting on the event with modern news tropes (include some hashtags).
    3. "search_term": A 1 or 2 word keyword to search for a historical image related to this event (e.g., "Caesar", "Pyramids", "Troy").
    """
    
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

def fetch_historical_image(search_term):
    """Fetches a free public domain image from Wikimedia Commons."""
    print(f"Fetching image for: {search_term}")
    url = f"https://en.wikipedia.org/w/api.php?action=query&titles={search_term}&prop=pageimages&format=json&pithumbsize=800"
    
    try:
        res = requests.get(url).json()
        pages = res['query']['pages']
        for page_id in pages:
            if 'thumbnail' in pages[page_id]:
                img_url = pages[page_id]['thumbnail']['source']
                img_response = requests.get(img_url)
                return Image.open(BytesIO(img_response.content))
    except Exception as e:
        print(f"Image search failed: {e}")
    
    # Fallback: Create a solid dark grey image if search fails
    return Image.new('RGB', (800, 600), color=(40, 40, 40))

def create_breaking_news_card(base_image, headline):
    """Overlays a Breaking News banner and text onto the image."""
    print("Creating Breaking News Card...")
    # Resize and crop to 800x600 for consistency
    base_image = base_image.convert("RGBA")
    base_image = base_image.resize((800, 600))
    
    draw = ImageDraw.Draw(base_image)
    
    # Draw Red "BREAKING NEWS" Banner
    red_banner_y = 450
    draw.rectangle([(0, red_banner_y), (800, 500)], fill=(200, 0, 0, 255))
    
    # Draw White Headline Banner
    draw.rectangle([(0, 500), (800, 600)], fill=(255, 255, 255, 255))
    
    # Load default fonts (Pillow default font is small, but it guarantees no missing file errors on GitHub Actions)
    # We will use the default font but scale it up manually by drawing multiple times if needed, 
    # but for safety in automated environments, we'll try to load a standard system font or use default.
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_headline = ImageFont.truetype("arial.ttf", 28)
    except IOError:
        font_large = ImageFont.load_default()
        font_headline = ImageFont.load_default()

    # Add Text
    draw.text((20, red_banner_y + 10), "BREAKING NEWS", fill=(255, 255, 255, 255), font=font_large)
    
    # Simple text wrapping for headline
    words = headline.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        # rough estimation of width, since default font varies
        if len(" ".join(current_line)) > 45: 
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    lines.append(" ".join(current_line))
    
    y_text = 515
    for line in lines:
        draw.text((20, y_text), line.upper(), fill=(0, 0, 0, 255), font=font_headline)
        y_text += 35

    # Save to a file
    output_path = "news_card.jpg"
    final_image = base_image.convert("RGB")
    final_image.save(output_path, quality=95)
    return output_path

def post_to_facebook(image_path, description):
    """Uploads the photo and posts it to the Facebook Page."""
    print("Posting to Facebook...")
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    
    payload = {
        'caption': description,
        'access_token': FB_ACCESS_TOKEN
    }
    
    with open(image_path, 'rb') as img:
        files = {'file': img}
        response = requests.post(url, data=payload, files=files)
        
    if response.status_code == 200:
        print("Successfully posted to Facebook!")
    else:
        print(f"Failed to post. Error: {response.text}")

def main():
    try:
        # 1. Generate the news
        news_data = generate_news()
        print(f"Generated: {news_data['headline']}")
        
        # 2. Get an image
        base_img = fetch_historical_image(news_data['search_term'])
        
        # 3. Create the graphic
        card_path = create_breaking_news_card(base_img, news_data['headline'])
        
        # 4. Post it
        post_to_facebook(card_path, news_data['description'])
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()