import httpx
import re
from html.parser import HTMLParser

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.in_script_or_style = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.in_script_or_style = False

    def handle_data(self, data):
        if not self.in_script_or_style:
            stripped = data.strip()
            if stripped:
                self.text.append(stripped)

    def get_text(self):
        return ' '.join(self.text)

async def scrape_url(url: str) -> str:
    """Fetches a URL and extracts visible text content."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            parser = TextExtractor()
            parser.feed(response.text)
            text_content = parser.get_text()
            
            # Clean up excessive whitespace
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            return text_content[:5000] # Return up to 5000 chars to avoid blowing up context
    except Exception as e:
        return f"Failed to scrape {url}: {str(e)}"
