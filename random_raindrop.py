#!/usr/bin/env python3

import json
import os
import random
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

def load_dotenv():
    """Load environment variables from .env file"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    if line.startswith('export '):
                        line = line[7:]
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')

load_dotenv()

CACHE_FILE = os.path.expanduser("~/.alfred_random_raindrop_cache.json")
CACHE_DURATION = 300

class RaindropManager:
    def __init__(self):
        self.raindrop_token = os.getenv("RAINDROP_TOKEN")

    def get_raindrop_articles(self, collection_id=0):
        """Fetch articles from Raindrop.io"""
        if not self.raindrop_token:
            return []

        try:
            url = f"https://api.raindrop.io/rest/v1/raindrops/{collection_id}"
            params = {"sort": "-created", "perpage": "50"}

            request_url = f"{url}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(request_url)
            req.add_header("Authorization", f"Bearer {self.raindrop_token}")

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            articles = []
            for item in data.get("items", []):
                title = item.get("title", "Untitled")
                url = item.get("link", "")

                if url and title:
                    collection_name = self.get_collection_name(collection_id)
                    articles.append({"title": title, "url": url, "source": collection_name})

            return articles

        except Exception as e:
            self.log_error(f"Raindrop.io error: {str(e)}")
            return []

    def get_collections(self):
        """Get available collections"""
        if not self.raindrop_token:
            return []

        try:
            url = "https://api.raindrop.io/rest/v1/collections"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {self.raindrop_token}")

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())

            collections = []
            for item in data.get("items", []):
                collections.append({
                    "id": item.get("_id"),
                    "title": item.get("title", "Untitled Collection")
                })

            # Add default "All Bookmarks" collection
            collections.append({"id": 0, "title": "All Bookmarks"})
            
            return collections

        except Exception as e:
            self.log_error(f"Collections error: {str(e)}")
            return [{"id": 0, "title": "All Bookmarks"}]

    def get_collection_name(self, collection_id):
        """Get collection name for display"""
        if collection_id == 0:
            return "Raindrop.io"
        
        collections = self.get_collections()
        for collection in collections:
            if collection["id"] == collection_id:
                return f"Raindrop ({collection['title']})"
        
        return "Raindrop.io"

    def load_cache(self):
        """Load cached articles if still valid"""
        try:
            if os.path.exists(CACHE_FILE):
                with open(CACHE_FILE, "r") as f:
                    cache_data = json.load(f)

                cache_time = datetime.fromisoformat(cache_data.get("timestamp", ""))
                if datetime.now() - cache_time < timedelta(seconds=CACHE_DURATION):
                    return cache_data.get("articles", [])
        except Exception:
            pass
        return None

    def save_cache(self, articles):
        """Save articles to cache"""
        try:
            cache_data = {"timestamp": datetime.now().isoformat(), "articles": articles}
            with open(CACHE_FILE, "w") as f:
                json.dump(cache_data, f)
        except Exception as e:
            self.log_error(f"Cache save error: {str(e)}")

    def get_all_articles(self, force_refresh=False):
        """Get all articles from Raindrop.io"""
        if not force_refresh:
            cached_articles = self.load_cache()
            if cached_articles:
                return cached_articles

        articles = []
        # Get from main collection (all bookmarks)
        articles.extend(self.get_raindrop_articles(0))
        
        # Optionally get from specific collections
        collections = self.get_collections()
        for collection in collections[:5]:  # Limit to first 5 custom collections
            if collection["id"] != 0:  # Skip "All Bookmarks" as we already got it
                articles.extend(self.get_raindrop_articles(collection["id"]))

        if articles:
            self.save_cache(articles)

        return articles

    def log_error(self, message):
        """Log error messages"""
        try:
            log_file = os.path.expanduser("~/.alfred_random_raindrop.log")
            with open(log_file, "a") as f:
                f.write(f"{datetime.now().isoformat()}: {message}\n")
        except Exception:
            pass

def main():
    """Select and output one random Raindrop.io article URL"""
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    
    raindrop_manager = RaindropManager()
    
    # Get articles (no filtering for single-service version)
    articles = raindrop_manager.get_all_articles()
    
    # Pick one random article and output the URL
    if articles:
        random_article = random.choice(articles)
        print(random_article["url"])
    else:
        print("No articles found")

if __name__ == "__main__":
    main()