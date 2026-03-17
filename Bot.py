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
    You are a serious, professional news anchor for a major global news network (like BBC News). Pick a random famous historical event from anywhere in the world and any timeline.
    Act as if it literally JUST happened today as breaking news.
    
    Respond STRICTLY in JSON format with these exact three keys:
    1. "headline": A serious, punchy breaking news headline (under 80 characters).
    2. "description": A highly professional, journalistic news report detailing the event. Use formal language, maintain objective reporting standards, and do NOT use any emojis, slang, or internet speak. Include 2-3 relevant hashtags at the end.
    3. "search_term": A short, broad keyword to find a public domain historical painting or photo of this event (e.g., "Sinking of Titanic", "Julius Caesar painting", "Trojan Horse"). Keep it under 4 words.
    """
    
    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    return json.loads(response.text)

def fetch_historical_image(search_term):
    """Fetches a free public domain image directly from Wikimedia Commons."""
    print(f"Fetching image for: {search_term}")
    
    # Use Wikimedia Commons direct file search for higher reliability
    search_url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch={search_term} filetype:bitmap&gsrnamespace=6&gsrlimit=3&prop=imageinfo&iiprop=url&format=json"
    
    try:
        res = requests.get(search_url).json()
        if 'query' in res and 'pages' in res['query']:
            pages = res['query']['pages']
            # Loop through the results to find a valid image url
            for page_id in pages:
                image_info = pages[page_id].get('imageinfo', [])
                if image_info:
                    img_url = image_info[0]['url']
                    # Ensure it's not a tiny icon, SVG, or PDF
                    if not img_url.lower().endswith(('.svg', '.pdf', '.tif', '.tiff')):
                        print(f"Found image: {img_url}")
                        img_response = requests.get(img_url)
                        return Image.open(BytesIO(img_response.content))
    except Exception as e:
        print(f"Image search failed: {e}")
    
    print("No image found on Wikimedia, using generated fallback pattern.")
    # Fallback: Create a subtle gray patterned image if search fails
    fallback = Image.new('RGB', (1080, 600), color=(220, 220, 220))
    draw = ImageDraw.Draw(fallback)
    for i in range(0, 1500, 40):
        draw.line([(i, 0), (0, i)], fill=(200, 200, 200), width=5)
    return fallback

def get_font(font_names, size):
    """Helper to try loading multiple fonts, falling back to default."""
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except IOError:
            continue
    return ImageFont.load_default()

def create_breaking_news_card(base_image, headline):
    """Generates the modern white Breaking News card design."""
    print("Creating Modern Breaking News Card...")
    
    # 1. Setup Base Canvas (1080x1080 - standard square)
    canvas = Image.new('RGB', (1080, 1080), 'white')
    draw = ImageDraw.Draw(canvas)
    
    # 2. Process and Paste the Historical Image (Top Half)
    base_image = base_image.convert("RGBA")
    # Crop and resize to fill 1080x600 perfectly without stretching
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
    
    # 3. Add Fading White Gradient Overlay (Bottom of the image)
    gradient = Image.new('RGBA', (1080, 200))
    draw_grad = ImageDraw.Draw(gradient)
    for y in range(200):
        # Alpha goes from 0 to 255 (Transparent to Solid White)
        alpha = int((y / 200) * 255)
        draw_grad.line([(0, y), (1080, y)], fill=(255, 255, 255, alpha))
    canvas.paste(gradient, (0, 400), gradient)
    
    # 4. Draw BBC News Logo (Top Right)
    bbc_red = (184, 0, 0)
    font_bbc = get_font(["arialbd.ttf", "Arial_Bold.ttf", "Impact"], 30)
    x_start = 880
    y_start = 40
    sq_size = 45
    spacing = 4
    for i, letter in enumerate(["B", "B", "C"]):
        x = x_start + i * (sq_size + spacing)
        draw.rectangle([x, y_start, x + sq_size, y_start + sq_size], fill=bbc_red)
        # Center letter
        bbox = draw.textbbox((0, 0), letter, font=font_bbc)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((x + (sq_size - w) / 2, y_start + (sq_size - h) / 2 - 4), letter, fill="white", font=font_bbc)

    # 5. Draw "BREAKING NEWS" Title
    font_breaking = get_font(["Impact", "impact.ttf", "arialbd.ttf", "Arial.ttf"], 130)
    text_bbox = draw.textbbox((0, 0), "BREAKING NEWS", font=font_breaking)
    title_w = text_bbox[2] - text_bbox[0]
    draw.text(((1080 - title_w) / 2, 560), "BREAKING NEWS", fill="black", font=font_breaking)
    
    # 6. Draw Red Geometric Ribbons & Dots
    red_color = "#C8102E"
    # Left Chevron
    draw.polygon([(40, 720), (70, 750), (40, 780), (10, 780), (40, 750), (10, 720)], fill=red_color)
    # Main Ribbon Bar
    draw.polygon([(85, 720), (650, 720), (590, 780), (85, 780)], fill=red_color)
    # Right Side Dots
    for x_dot in range(730, 950, 40):
        for y_dot in range(730, 780, 20):
            draw.ellipse([x_dot, y_dot, x_dot + 6, y_dot + 6], fill="#A0A0A0")

    # 7. Draw Headline (Wrapped text)
    font_headline = get_font(["arialbi.ttf", "Arial_Bold_Italic.ttf", "arialbd.ttf", "Arial.ttf"], 45)
    words = headline.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        bbox = draw.textbbox((0, 0), " ".join(current_line), font=font_headline)
        if (bbox[2] - bbox[0]) > 900: # Max width for text
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    
    y_text = 820
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_headline)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((1080 - w) / 2, y_text), line, fill="black", font=font_headline)
        y_text += h + 15

    # 8. Draw Footer
    footer_y = 960
    font_small = get_font(["arial.ttf", "Arial.ttf"], 20)
    font_bold_small = get_font(["arialbd.ttf", "Arial_Bold.ttf"], 24)
    font_button = get_font(["arialbd.ttf", "Arial_Bold.ttf"], 28)
    
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