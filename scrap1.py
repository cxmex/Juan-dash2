import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import quote

class InstagramFollowerBot:
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
    
    def get_random_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    def search_google_for_instagram(self, username):
        """Search Google for Instagram profile information"""
        query = f"instagram.com/{username} followers"
        google_url = f"https://www.google.com/search?q={quote(query)}"
        
        try:
            headers = self.get_random_headers()
            response = self.session.get(google_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return self.parse_google_results(response.text, username)
            else:
                print(f"Google search failed with status code: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"Error searching Google: {e}")
            return None
    
    def parse_google_results(self, html_content, username):
        """Parse Google search results for Instagram follower info"""
        soup = BeautifulSoup(html_content, 'html.parser')
        results = []
        
        # Look for Instagram links in search results
        instagram_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if 'instagram.com' in href and username in href:
                instagram_links.append(href)
        
        # Look for follower mentions in search snippets
        follower_patterns = [
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|K|m|M)?\s*followers',
            r'followers:\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|K|m|M)?',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:k|K|m|M)?\s*seguidores'  # Spanish
        ]
        
        for pattern in follower_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                results.extend(matches)
        
        return {
            'instagram_links': instagram_links[:5],  # Top 5 links
            'follower_mentions': results[:10],  # Top 10 mentions
            'search_snippets': self.extract_relevant_snippets(soup, username)
        }
    
    def extract_relevant_snippets(self, soup, username):
        """Extract relevant text snippets mentioning the username"""
        snippets = []
        
        # Look in search result descriptions
        for desc in soup.find_all(['span', 'div'], class_=re.compile(r'.*desc.*|.*snippet.*', re.I)):
            text = desc.get_text()
            if username.lower() in text.lower() and any(word in text.lower() for word in ['follow', 'instagram', 'profile']):
                snippets.append(text.strip())
        
        return snippets[:5]  # Top 5 relevant snippets
    
    def try_direct_instagram_check(self, username):
        """Attempt to get basic info from Instagram profile page (may be limited)"""
        instagram_url = f"https://www.instagram.com/{username}/"
        
        try:
            headers = self.get_random_headers()
            response = self.session.get(instagram_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Look for follower count in page source
                follower_patterns = [
                    r'"edge_followed_by":{"count":(\d+)}',
                    r'followers","value":"([^"]+)"',
                    r'content="([^"]*followers[^"]*)"'
                ]
                
                for pattern in follower_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        return matches[0]
            
            return None
            
        except requests.RequestException as e:
            print(f"Error accessing Instagram directly: {e}")
            return None
    
    def find_followers(self, username):
        """Main method to find follower count for Instagram username"""
        print(f"🔍 Searching for follower information for Instagram user: @{username}")
        print("-" * 60)
        
        # Method 1: Google Search
        print("📊 Method 1: Google Search Analysis")
        google_results = self.search_google_for_instagram(username)
        
        if google_results:
            print(f"Found {len(google_results['instagram_links'])} Instagram links")
            print(f"Found {len(google_results['follower_mentions'])} follower mentions")
            
            if google_results['follower_mentions']:
                print("\n🎯 Potential follower counts found:")
                for count in google_results['follower_mentions']:
                    print(f"  • {count}")
            
            if google_results['search_snippets']:
                print("\n📝 Relevant snippets:")
                for snippet in google_results['search_snippets']:
                    print(f"  • {snippet[:100]}...")
        
        # Add delay to be respectful
        time.sleep(2)
        
        # Method 2: Direct Instagram check (limited)
        print("\n📱 Method 2: Direct Instagram Check (Limited)")
        direct_result = self.try_direct_instagram_check(username)
        
        if direct_result:
            print(f"Direct check result: {direct_result}")
        else:
            print("Direct check: No accessible data (Instagram blocks most scraping)")
        
        return {
            'google_search': google_results,
            'direct_check': direct_result
        }

# Usage example
def main():
    bot = InstagramFollowerBot()
    
    # Search for your profile
    username = "horaciomex"
    results = bot.find_followers(username)
    
    print("\n" + "="*60)
    print("🎯 SUMMARY")
    print("="*60)
    
    if results['google_search'] and results['google_search']['follower_mentions']:
        print(f"Most likely follower count for @{username}:")
        counts = results['google_search']['follower_mentions']
        print(f"  • {counts[0]} (from Google search results)")
    else:
        print(f"Could not determine exact follower count for @{username}")
        print("This might be due to:")
        print("  • Privacy settings")
        print("  • Recent changes not indexed by Google")
        print("  • Anti-scraping measures")
    
    print(f"\n💡 For accurate, real-time data, consider:")
    print("  • Instagram Basic Display API")
    print("  • Manual check on Instagram app/website")
    print("  • Third-party analytics tools")

if __name__ == "__main__":
    main()