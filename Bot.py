import os
import json
import time
import random
import requests
import urllib.parse
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
    """Downloads a font safely with a secondary backup to prevent tiny default text."""
    filename = url.split('/')[-1]
    try:
        if not os.path.exists(filename):
            print(f"Downloading font: {filename}...")
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if r.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(r.content)
            else:
                raise Exception(f"HTTP {r.status_code} Error")
        return ImageFont.truetype(filename, size)
    except Exception as e:
        print(f"Failed to load font {filename}: {e}. Trying secondary fallback...")
        # Emergency secondary fallback to PT Sans if primary fails
        fallback_url = "https://github.com/google/fonts/raw/main/ofl/ptsans/PTSans-Bold.ttf"
        fb_filename = "PTSans-Bold.ttf"
        try:
            if not os.path.exists(fb_filename):
                r = requests.get(fallback_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                if r.status_code == 200:
                    with open(fb_filename, 'wb') as f:
                        f.write(r.content)
            return ImageFont.truetype(fb_filename, size)
        except Exception:
            print("All font downloads failed. Using default.")
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
    4. "image_prompt": A highly detailed prompt to generate an image of this event. Describe the scene, lighting, and action. Do NOT include any text, letters, or words in this image prompt. (e.g., "The massive wooden Trojan horse standing outside the gates of Troy at twilight, dramatic lighting, epic scale").
    """
    
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

def generate_historical_image(image_prompt, topic=""):
    """Generates or fetches an image using 3 different fallback systems to guarantee success."""
    print(f"Fetching/Generating image for: {topic}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*'
    }

    # FOOLPROOF METHOD 1: Lexica.art AI Image Search (Extremely reliable and fast)
    try:
        print("Attempt 1: Searching Lexica.art AI database...")
        lexica_query = urllib.parse.quote(f"{topic} historical event illustration")
        lexica_url = f"https://lexica.art/api/v1/search?q={lexica_query}"
        res = requests.get(lexica_url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if data.get('images'):
                img_url = data['images'][0]['src']
                print(f"Lexica AI image found: {img_url}")
                img_res = requests.get(img_url, headers=headers, timeout=15)
                if img_res.status_code == 200:
                    return Image.open(BytesIO(img_res.content))
    except Exception as e:
        print(f"Lexica search failed: {e}")

    # FOOLPROOF METHOD 2: Pollinations AI Generation
    try:
        print("Attempt 2: Generating fresh AI image via Pollinations...")
        clean_prompt = image_prompt.replace('\n', ' ').replace('"', '').replace("'", "")
        # Truncate prompt to prevent 'URI Too Long' server errors
        clean_prompt = clean_prompt[:150] if len(clean_prompt) > 150 else clean_prompt
        full_prompt = f"{clean_prompt}, 2D illustration, high quality digital art"
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        seed = random.randint(1, 1000000)
        poll_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=600&nologo=true&seed={seed}"
        
        res = requests.get(poll_url, headers=headers, timeout=30)
        if res.status_code == 200 and 'image' in res.headers.get('Content-Type', '').lower():
            print("Successfully generated Pollinations AI image!")
            return Image.open(BytesIO(res.content))
        else:
            print(f"Pollinations returned status {res.status_code}")
    except Exception as e:
        print(f"Pollinations generation failed: {e}")

    # FOOLPROOF METHOD 3: Wikimedia Commons Fallback
    if topic:
        try:
            print("Attempt 3: Falling back to real historical photo from Wikimedia...")
            search_term = urllib.parse.quote(topic)
            commons_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={search_term}&gsrnamespace=6&gsrlimit=3&prop=imageinfo&iiprop=url&format=json"
            res = requests.get(commons_url, headers=headers, timeout=15).json()
            if 'query' in res and 'pages' in res['query']:
                for page_id in res['query']['pages']:
                    image_info = res['query']['pages'][page_id].get('imageinfo', [])
                    if image_info:
                        img_url = image_info[0]['url']
                        if not img_url.lower().endswith(('.svg', '.pdf', '.tif', '.tiff')):
                            print(f"Wikimedia image found: {img_url}")
                            r = requests.get(img_url, headers=headers, timeout=15)
                            if r.status_code == 200:
                                return Image.open(BytesIO(r.content))
        except Exception as e:
            print(f"Wikimedia fallback failed: {e}")

    # ULTIMATE FALLBACK: Gray Pattern
    print("All image fetching failed. Using generated fallback pattern.")
    fallback = Image.new('RGB', (1080, 600), color=(220, 220, 220))
    draw = ImageDraw.Draw(fallback)
    for i in range(0, 1500, 40):
        draw.line([(i, 0), (0, i)], fill=(200, 200, 200), width=5)
    return fallback

def create_breaking_news_card(base_image, headline):
    """Generates the modern white Breaking News card design with robust fonts."""
    print("Creating Modern Breaking News Card...")
    
    # Official stable Google Fonts URLs (Swapped to Lato which is highly static and reliable)
    font_anton_url = "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf"
    font_lato_bold_url = "https://github.com/google/fonts/raw/main/ofl/lato/Lato-Bold.ttf"

    font_breaking = get_remote_font(font_anton_url, 140)
    font_bbc = get_remote_font(font_lato_bold_url, 30)
    font_headline = get_remote_font(font_lato_bold_url, 45)

    # 1. Setup Base Canvas (1080x1080 - standard square)
    canvas = Image.new('RGB', (1080, 1080), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # 2. Process and Paste the Generated Image (Top Half)
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
        
        # 2. Get an image using AI generation
        base_img = generate_historical_image(news_data['image_prompt'], news_data.get('topic', ''))
        
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