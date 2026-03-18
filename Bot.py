import os
import json
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai

# --- CONFIGURATION & SECRETS ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
HISTORY_FILE = "history.json"

genai.configure(api_key=GEMINI_API_KEY)

# --- FONT DOWNLOADER ---
def get_remote_font(url, size):
    """Downloads a font from a URL if it doesn't exist locally, ensuring fonts always work."""
    filename = url.split('/')[-1]
    try:
        if not os.path.exists(filename):
            print(f"Downloading font: {filename}...")
            r = requests.get(url)
            with open(filename, 'wb') as f:
                f.write(r.content)
        return ImageFont.truetype(filename, size)
    except Exception as e:
        print(f"Failed to load font {filename}: {e}. Using default.")
        return ImageFont.load_default()

# --- MEMORY SYSTEM ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def filter_recent_history(history):
    """Keeps only records from the last 90 days (7,776,000 seconds)."""
    ninety_days_ago = time.time() - (90 * 24 * 60 * 60)
    return [h for h in history if h.get("timestamp", 0) > ninety_days_ago]

# --- CORE FUNCTIONS ---
def generate_news(recent_topics):
    """Uses Google Gemini to generate a unique historical news report."""
    print("Generating news with Gemini...")
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Format the avoid list
    avoid_list_str = ", ".join(recent_topics) if recent_topics else "None"
    
    prompt = f"""
    You are a serious, professional news anchor for a major global news network (like BBC News). Pick a random famous historical event from anywhere in the world and any timeline.
    Act as if it literally JUST happened today as breaking news.
    
    CRITICAL: You MUST NOT report on any of these recent topics: {avoid_list_str}
    
    Respond STRICTLY in JSON format with these exact four keys:
    1. "topic": A 2-4 word summary of the event you chose (e.g., "Sinking of Titanic").
    2. "headline": A serious, punchy breaking news headline (under 80 characters).
    3. "description": A highly professional, journalistic news report detailing the event. Use formal language, maintain objective reporting standards, and do NOT use any emojis, slang, or internet speak. Include 2-3 relevant hashtags at the end.
    4. "search_term": The EXACT Wikipedia article title for this event to find its main photo (e.g., "Fall of the Berlin Wall", "Assassination of Julius Caesar").
    """
    
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

def fetch_historical_image(search_term):
    """Fetches a free public domain image by searching Wikipedia first, then Commons."""
    print(f"Fetching image for: {search_term}")
    
    # Strategy 1: Search Wikipedia for the closest article and get its main image
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={search_term}&utf8=&format=json&srlimit=3"
    try:
        search_res = requests.get(search_url).json()
        if 'query' in search_res and search_res['query']['search']:
            for result in search_res['query']['search']:
                title = result['title']
                img_req = f"https://en.wikipedia.org/w/api.php?action=query&titles={title}&prop=pageimages&format=json&pithumbsize=1000"
                res = requests.get(img_req).json()
                pages = res['query']['pages']
                for page_id in pages:
                    if 'thumbnail' in pages[page_id]:
                        img_url = pages[page_id]['thumbnail']['source']
                        if not img_url.lower().endswith(('.svg', '.pdf')):
                            print(f"Found Wikipedia Image: {img_url}")
                            r = requests.get(img_url)
                            return Image.open(BytesIO(r.content))
    except Exception as e:
        print(f"Wikipedia image search failed: {e}")

    # Strategy 2: Fallback to Wikimedia Commons directly
    print("Falling back to Wikimedia Commons...")
    commons_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={search_term}&gsrnamespace=6&gsrlimit=5&prop=imageinfo&iiprop=url&format=json"
    try:
        res = requests.get(commons_url).json()
        if 'query' in res and 'pages' in res['query']:
            pages = res['query']['pages']
            for page_id in pages:
                image_info = pages[page_id].get('imageinfo', [])
                if image_info:
                    img_url = image_info[0]['url']
                    if not img_url.lower().endswith(('.svg', '.pdf', '.tif', '.tiff')):
                        print(f"Found Commons Image: {img_url}")
                        img_response = requests.get(img_url)
                        return Image.open(BytesIO(img_response.content))
    except Exception as e:
        print(f"Commons search failed: {e}")
    
    print("No image found, using generated fallback pattern.")
    fallback = Image.new('RGB', (1080, 600), color=(220, 220, 220))
    draw = ImageDraw.Draw(fallback)
    for i in range(0, 1500, 40):
        draw.line([(i, 0), (0, i)], fill=(200, 200, 200), width=5)
    return fallback

def create_breaking_news_card(base_image, headline):
    """Generates the modern white Breaking News card design with robust fonts."""
    print("Creating Modern Breaking News Card...")
    
    # Download required fonts from Google Fonts directly
    font_anton_url = "https://raw.githubusercontent.com/googlefonts/anton/main/fonts/ttf/Anton-Regular.ttf"
    font_roboto_bold_url = "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf"
    font_roboto_ital_url = "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-BoldItalic.ttf"
    font_roboto_reg_url = "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf"

    font_breaking = get_remote_font(font_anton_url, 140)
    font_bbc = get_remote_font(font_roboto_bold_url, 30)
    font_headline = get_remote_font(font_roboto_ital_url, 45)
    font_small = get_remote_font(font_roboto_reg_url, 20)
    font_bold_small = get_remote_font(font_roboto_bold_url, 24)
    font_button = get_remote_font(font_roboto_bold_url, 28)

    # 1. Setup Base Canvas (1080x1080 - standard square)
    canvas = Image.new('RGB', (1080, 1080), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # 2. Process and Paste the Historical Image (Top Half)
    base_image = base_image.convert("RGBA")
    img_ratio = base_image.width / base_image.height
    target_ratio = 1080 / 600
    if img_ratio > target_ratio:
        new_width = int(base_image.height * target_ratio)
        left = (base_image.width - new_width) / 2
        base_image = base_image.crop((left, 0, left + new_width, base_image.height))
    else:
        new_height = int(base_image.width / target_ratio)
        top = (base_image.height - new_height) / 2
        base_image = base_image.crop((0, top, base_image.width, top + new_height))
        
    base_image = base_image.resize((1080, 600))
    canvas.paste(base_image, (0, 0))
    
    # 3. Add Fading White Gradient Overlay
    gradient = Image.new('RGBA', (1080, 200))
    draw_grad = ImageDraw.Draw(gradient)
    for y in range(200):
        alpha = int((y / 200) * 255)
        draw_grad.line([(0, y), (1080, y)], fill=(255, 255, 255, alpha))
    canvas.paste(gradient, (0, 400), gradient)
    
    # 4. Draw BBC News Logo
    bbc_red = (184, 0, 0)
    x_start = 880
    y_start = 40
    sq_size = 45
    spacing = 4
    for i, letter in enumerate(["B", "B", "C"]):
        x = x_start + i * (sq_size + spacing)
        draw.rectangle([x, y_start, x + sq_size, y_start + sq_size], fill=bbc_red)
        bbox = draw.textbbox((0, 0), letter, font=font_bbc)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (sq_size - w) / 2, y_start + (sq_size - h) / 2 - 4), letter, fill="white", font=font_bbc)

    # 5. Draw "BREAKING NEWS" Title
    text_bbox = draw.textbbox((0, 0), "BREAKING NEWS", font=font_breaking)
    title_w = text_bbox[2] - text_bbox[0]
    draw.text(((1080 - title_w) / 2, 540), "BREAKING NEWS", fill="black", font=font_breaking)
    
    # 6. Draw Red Geometric Ribbons & Dots
    red_color = "#C8102E"
    draw.polygon([(40, 720), (70, 750), (40, 780), (10, 780), (40, 750), (10, 720)], fill=red_color)
    draw.polygon([(85, 720), (650, 720), (590, 780), (85, 780)], fill=red_color)
    for x_dot in range(730, 950, 40):
        for y_dot in range(730, 780, 20):
            draw.ellipse([x_dot, y_dot, x_dot + 6, y_dot + 6], fill="#A0A0A0")

    # 7. Draw Headline (Wrapped text)
    words = headline.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        bbox = draw.textbbox((0, 0), " ".join(current_line), font=font_headline)
        if (bbox[2] - bbox[0]) > 900:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    
    y_text = 810
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_headline)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((1080 - w) / 2, y_text), line, fill="black", font=font_headline)
        y_text += h + 15

    # 8. Draw Footer
    footer_y = 960
    
    # Globe Icon Box
    draw.rounded_rectangle([60, footer_y, 140, footer_y + 80], radius=15, fill=red_color)
    draw.ellipse([75, footer_y + 15, 125, footer_y + 65], outline="white", width=2)
    draw.ellipse([90, footer_y + 15, 110, footer_y + 65], outline="white", width=2)
    draw.line([75, footer_y + 40, 125, footer_y + 40], fill="white", width=2)
    
    # Footer Text
    draw.text((160, footer_y + 15), "More Information At", fill="#666666", font=font_small)
    draw.text((160, footer_y + 40), "www.bcnews.com", fill="black", font=font_bold_small)
    
    # Read More Button
    draw.rounded_rectangle([700, footer_y + 15, 900, footer_y + 65], radius=10, fill=red_color)
    bbox = draw.textbbox((0, 0), "Read More", font=font_button)
    bw = bbox[2] - bbox[0]
    draw.text((700 + (200 - bw) / 2, footer_y + 25), "Read More", fill="white", font=font_button)
    
    # Right Arrow
    draw.line([930, footer_y + 40, 990, footer_y + 40], fill="black", width=2)
    draw.line([970, footer_y + 25, 990, footer_y + 40], fill="black", width=2)
    draw.line([970, footer_y + 55, 990, footer_y + 40], fill="black", width=2)

    # Save Final Image
    output_path = "news_card.jpg"
    final_image = canvas.convert("RGB")
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
        # Load memory
        history = load_history()
        history = filter_recent_history(history)
        recent_topics = [h["topic"] for h in history]
        
        # 1. Generate the news (passing the memory)
        news_data = generate_news(recent_topics)
        print(f"Generated Topic: {news_data['topic']}")
        print(f"Generated Headline: {news_data['headline']}")
        
        # 2. Get an image
        base_img = fetch_historical_image(news_data['search_term'])
        
        # 3. Create the graphic
        card_path = create_breaking_news_card(base_img, news_data['headline'])
        
        # 4. Post it
        post_to_facebook(card_path, news_data['description'])
        
        # 5. Save to memory so it doesn't repeat
        history.append({
            "timestamp": time.time(),
            "topic": news_data['topic']
        })
        save_history(history)
        print("Memory updated successfully.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()