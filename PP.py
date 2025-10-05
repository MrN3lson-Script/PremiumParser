import requests
from bs4 import BeautifulSoup
import sys
import os
import re
from urllib.parse import urljoin, urlparse
from colorama import Fore, Style, init

init(autoreset=True)

COLOR_HEADER = Fore.CYAN + Style.BRIGHT
COLOR_PROMPT = Fore.YELLOW
COLOR_SUCCESS = Fore.GREEN
COLOR_ERROR = Fore.RED
COLOR_RESULT_TITLE = Fore.MAGENTA + Style.BRIGHT
COLOR_LINK = Fore.BLUE
COLOR_FILE = Fore.BLUE + Style.BRIGHT
COLOR_OPTION = Fore.WHITE
COLOR_HIGHLIGHT = Fore.RED

MAX_OUTPUT_LENGTH = 10000

class PremiumParser:
    def __init__(self, url, save_dir):
        self.url = url
        self.save_dir = save_dir
        self.domain = urlparse(self.url).netloc.replace('www.', '').replace('.', '_')
        self.html_content = self._fetch_html()

    def _fetch_html(self):
        print(f"{COLOR_PROMPT}Loading page: {self.url}...")
        try:
            headers = {'User-Agent': 'PremiumParser/1.0 (Python)'}
            response = requests.get(self.url, headers=headers, timeout=10)
            response.raise_for_status()
            print(f"{COLOR_SUCCESS}Page successfully loaded.")
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"{COLOR_ERROR}Error loading page: {e}")
            return None

    def _save_to_file(self, content, title):
        if not content or content.startswith(COLOR_ERROR):
            print(f"{COLOR_ERROR}Nothing to save: content is empty or an error message.")
            return
            
        file_name_base = re.sub(r'[^\w\-_\.]', '', self.domain)
        file_name = f"parser-{file_name_base}-{title.lower().replace(' ', '_')}.txt"
        file_path = os.path.join(self.save_dir, file_name)
        
        try:
            clean_content = re.sub(r'\x1b\[[0-9;]*m', '', content)
            
            os.makedirs(self.save_dir, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(clean_content)
            print(f"{COLOR_SUCCESS}Result saved to file: {COLOR_FILE}{file_path}{Style.RESET_ALL}")
        except IOError as e:
            print(f"{COLOR_ERROR}Error writing file {file_path}: {e}")

    def get_only_text(self):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
        
        print(f"{COLOR_PROMPT}Extracting text only...")
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        return text

    def get_full_html(self):
        print(f"{COLOR_PROMPT}Returning full HTML code...")
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
        return self.html_content

    def get_all_javascript(self):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
            
        print(f"{COLOR_PROMPT}Extracting all JavaScript (JS)...")
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        internal_js = [script.string for script in soup.find_all('script') if script.string and not script.get('src')]
        external_js_urls = [script.get('src') for script in soup.find_all('script') if script.get('src')]
        
        output = []
        if internal_js:
            output.append(f"{COLOR_RESULT_TITLE}--- Internal JavaScript (JS) ---")
            output.extend(internal_js)
            output.append("-" * 30)
        
        if external_js_urls:
            output.append(f"{COLOR_RESULT_TITLE}--- External Script URLs ---")
            output.extend([f"{COLOR_LINK}{url}{Style.RESET_ALL}" for url in external_js_urls])

        if not output:
            return f"{COLOR_ERROR}No embedded or external JavaScript found on the page."

        return '\n'.join(map(str, output))

    def get_all_css(self):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
            
        print(f"{COLOR_PROMPT}Extracting all CSS...")
        soup = BeautifulSoup(self.html_content, 'html.parser')

        internal_css = [style.string for style in soup.find_all('style') if style.string]
        external_css_urls = [link.get('href') for link in soup.find_all('link', rel='stylesheet') if link.get('href')]

        output = []
        if internal_css:
            output.append(f"{COLOR_RESULT_TITLE}--- Internal CSS (<style>) ---")
            output.extend(internal_css)
            output.append("-" * 30)
            
        if external_css_urls:
            output.append(f"{COLOR_RESULT_TITLE}--- External Stylesheet URLs (<link rel=\"stylesheet\">) ---")
            output.extend([f"{COLOR_LINK}{url}{Style.RESET_ALL}" for url in external_css_urls])
            
        if not output:
            return f"{COLOR_ERROR}No embedded or external CSS found on the page."
            
        return '\n'.join(map(str, output))

    def get_all_media_links(self):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
        
        print(f"{COLOR_PROMPT}Extracting all media links...")
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        media_links = {
            'images': [],
            'videos': [],
            'audio': [],
            'other_media': []
        }
        
        for img in soup.find_all('img', src=True):
            absolute_url = urljoin(self.url, img['src'])
            media_links['images'].append(absolute_url)
            
        for video in soup.find_all('video'):
            if video.get('src'):
                absolute_url = urljoin(self.url, video['src'])
                media_links['videos'].append(absolute_url)
                
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src']
            if 'youtube.com' in src or 'vimeo.com' in src:
                absolute_url = urljoin(self.url, src)
                media_links['videos'].append(absolute_url)
        
        for audio in soup.find_all('audio', src=True):
            absolute_url = urljoin(self.url, audio['src'])
            media_links['audio'].append(absolute_url)

        for source in soup.find_all('source', src=True):
             absolute_url = urljoin(self.url, source['src'])
             if absolute_url not in media_links['other_media']:
                 media_links['other_media'].append(absolute_url)

        output = []
        
        for category, links in media_links.items():
            if links:
                title = category.capitalize()
                output.append(f"{COLOR_RESULT_TITLE}--- {title} ({len(links)} found) ---")
                output.extend([f"{COLOR_LINK}{url}{Style.RESET_ALL}" for url in links])
                output.append("-" * 30)
        
        if not any(media_links.values()):
            return f"{COLOR_ERROR}No media links found on the page."
            
        return '\n'.join(output)
        
    def get_all_links(self):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
            
        print(f"{COLOR_PROMPT}Extracting all links (<a> tag)...")
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        all_links = [a.get('href') for a in soup.find_all('a', href=True)]
        
        unique_links = set()
        for link in all_links:
            if link and not link.startswith('#'):
                absolute_url = urljoin(self.url, link)
                unique_links.add(absolute_url)
        
        if not unique_links:
            return f"{COLOR_ERROR}No links (<a> tag) found on the page."
            
        output = [f"{COLOR_RESULT_TITLE}--- ALL HYPERLINKS ({len(unique_links)} found) ---"]
        output.extend([f"{COLOR_LINK}{url}{Style.RESET_ALL}" for url in sorted(list(unique_links))])
        output.append("-" * 30)
        
        return '\n'.join(output)

    def search_site_data(self, search_term):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
        
        print(f"{COLOR_PROMPT}Searching for '{search_term}' in HTML and JavaScript...")
        
        soup = BeautifulSoup(self.html_content, 'html.parser')
        
        html_search_content = self.html_content 
        
        js_content = '\n'.join([script.string for script in soup.find_all('script') if script.string])
        
        output = []
        search_term_lower = search_term.lower()

        html_matches = [line.strip() for line in html_search_content.splitlines() if search_term_lower in line.lower()]
        if html_matches:
            output.append(f"{COLOR_RESULT_TITLE}--- Matches in HTML ({len(html_matches)} lines found) ---")
            
            for line in html_matches:
                highlighted_line = re.sub(re.escape(search_term), f"{COLOR_HIGHLIGHT}\\g<0>{Style.RESET_ALL}", line, flags=re.IGNORECASE)
                output.append(highlighted_line)
            output.append("-" * 30)

        js_matches = [line.strip() for line in js_content.splitlines() if search_term_lower in line.lower()]
        if js_matches:
            output.append(f"{COLOR_RESULT_TITLE}--- Matches in JavaScript ({len(js_matches)} lines found) ---")
            
            for line in js_matches:
                highlighted_line = re.sub(re.escape(search_term), f"{COLOR_HIGHLIGHT}\\g<0>{Style.RESET_ALL}", line, flags=re.IGNORECASE)
                output.append(highlighted_line)
            output.append("-" * 30)

        if not output:
            return f"{COLOR_ERROR}Search term '{search_term}' not found in HTML or JavaScript content."

        return '\n'.join(output)

    def search_line_content(self, search_word):
        if not self.html_content:
            return f"{COLOR_ERROR}Failed to get HTML content."
            
        print(f"{COLOR_PROMPT}Searching raw HTML content for lines containing '{search_word}'...")
        
        search_word_lower = search_word.lower()
        lines = self.html_content.splitlines()
        
        matching_lines = []
        for line in lines:
            if search_word_lower in line.lower():
                highlighted_line = re.sub(
                    re.escape(search_word), 
                    f"{COLOR_HIGHLIGHT}\\g<0>{Style.RESET_ALL}", 
                    line, 
                    flags=re.IGNORECASE
                )
                matching_lines.append(highlighted_line.strip())

        if not matching_lines:
            return f"{COLOR_ERROR}Word '{search_word}' not found in any line of the raw HTML content."
            
        output = [f"{COLOR_RESULT_TITLE}--- LINES CONTAINING '{search_word}' ({len(matching_lines)} found) ---"]
        output.extend(matching_lines)
        output.append("-" * 30)
        
        return '\n'.join(output)


def main():
    print(f"""{COLOR_HEADER}Starting PremiumParser
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&%%#((&&*,,,,,&&,,..&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&%/***/#%&&&&&&&&,,,,%&&&%#&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&(**/&&&&&&/,,,,,,,,,,,(&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&(//&&&&/,,,,,,,,,,,,,,,,,,,,,,,#&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&//%&&&*******,,,,,,,,,,,,,,,,,,,,,,,,&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&(/%&&/************,,,****,,,,,,,,,,,,,,,,#&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&%((&&(***********#&&&&&&&&&&&&&&&/,,,,,,,,,,,%&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&#(%&&**********%&&&&&&&&&&&&&&&&&&&&&(,,,,,,,,,,&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&%(%&&*********%&&&&&%****,,,,,,(&&&&&&&&(,,,,,,,,,&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&((&&/********&&&&&/***&&&&&&&%#,,,&&&&&&&&,,,,,,,,/&&&&&&&&&&&&&
&&&&&&&&&&&&&&&%(%&&///*****&&&&&***&&&&&&&&&&&&/,,&&&&&&&(,,,,,,,,&&&&&&&&&&&&&
&&&&&&&&&&&&&&&%(&&#//////*/&&&&&**#&&&&&&&&&&&&&,,#&&&&&&&,,,,,,,,&&&&&&&&&&&&&
&&&&&&&&&%((&&&%(%%#////////&&&%%***&&&&&&&&&%&&/,,&&&&&&&%,,,,,,,,&&&&&&&&&&&&&
&&&&&&&&&&&&&&%%(&&#////////#%%%&&/**(%%%&&&&%%,,*&&&&&&&&,,,,,,,,,&&&&&&&&&&&&&
&&&&&&&&&((((&&%#&%#/////////%&&&&&%%**********/(***/&&&&*,,,,,,,,%&&&&&&&&&&&&&
&&&&&&&&###(((&%#&&#///////////&%%&&&&%%%&&&&&&&&&&(%%&%***,,,,,,#&&&&&&&&&&&&&&
&&&&&&&&%&%&&&%%#&&%/////////////%&&&&&&&&&&&&&&%&%&&/********,*%&&&&&&&&&&&&&&&
&&&&&&&&&%##%&%%#%&%((///////////////%&&&&&%&%&&%(************/&&&&&&&&&&&&&&&&&
&&&&&&&&%%####&%#&%%((((///////////////////********************/&&&&&&&&&&&&&&&&
&&&&&&&&&%%%%&&%#&&%((((((//%///////////////*************(&&*****,%&&&&&&&&&&&&&
&&&&&&&&&&&&&&&%%&%%((((((((%%%%&(//////////////*****#&%%&&&&%#******&&&&&&&&&&&
&&&&&&&&&&&&&&&%%&&%((((((((%%%%%%%%%%%%%%%&&&%%%%&%%%%%&&%%%&&&&*****%&&&&&&&&&
&&&&&&&&&&&&&&&%%&&%((((((((%%%%%%%%%%%%%%%%%%%%%%&&%%%&&&&&&&&&&&%&&&&&&&&&&&&&
&&&&&&&&&&&&&&&%%&&%#(((((((%%%%%%%%%%%%%%%%%%%%%&&&%&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&%%&&%###(((((%%%%%%%%%%%%%%%%%&%%&&&&&&%&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&%%&&%######((&%&%%%%%%%%%%%%%%&%&%&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&%&&%#######(%%&&&&&&&&&%%&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&%&&%########%%&&%&&&%&&&%%&%%%%&%&&&&&&&&&&&&&%&%&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&%#######%&&%&&%%&&&&&%%%%%%%&&&&&&&&&&&&&&&&%&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&%%%%###&&&&&&&&&&&&%%%%%%%%%%%%&&&&&&&%&&&&&&%&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&%%%%&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&%&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&""")
    
    url = input(f"{COLOR_PROMPT}Enter the URL to parse (e.g., https://example.com): {Style.RESET_ALL}")
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
        
    save_dir = input(f"{COLOR_PROMPT}Enter the path to the save directory (e.g., ./results or C:\\parser_data): {Style.RESET_ALL}")
        
    parser = PremiumParser(url, save_dir)
    
    if not parser.html_content:
        print(f"\n{COLOR_ERROR}Parser terminating due to load error.")
        return

    while True:
        print(f"\n{COLOR_HEADER}{'='*40}")
        print(f"{COLOR_HEADER}Select a function to execute:")
        print(f"{COLOR_HEADER}1:{COLOR_OPTION} Get only TEXT")
        print(f"{COLOR_HEADER}2:{COLOR_OPTION} Get FULL HTML")
        print(f"{COLOR_HEADER}3:{COLOR_OPTION} Get all JAVASCRIPT")
        print(f"{COLOR_HEADER}4:{COLOR_OPTION} Get all CSS")
        print(f"{COLOR_HEADER}5:{COLOR_OPTION} Get all MEDIA LINKS")
        print(f"{COLOR_HEADER}6:{COLOR_OPTION} Get all HYPERLINKS (<a> tag)")
        print(f"{COLOR_HEADER}7:{COLOR_OPTION} Search SITE DATA (HTML & JS)")
        print(f"{COLOR_HEADER}8:{COLOR_OPTION} Search LINE CONTENT (Raw HTML)")
        print(f"{COLOR_HEADER}9:{COLOR_OPTION} Exit")
        print(f"{COLOR_HEADER}{'='*40}")
        
        choice = input(f"{COLOR_PROMPT}Your choice (1-9): {Style.RESET_ALL}")

        result = ""
        title = ""
        
        if choice == '1':
            result = parser.get_only_text()
            title = "TEXT"
        elif choice == '2':
            result = parser.get_full_html()
            title = "HTML"
        elif choice == '3':
            result = parser.get_all_javascript()
            title = "JAVASCRIPT"
        elif choice == '4':
            result = parser.get_all_css()
            title = "CSS"
        elif choice == '5':
            result = parser.get_all_media_links()
            title = "MEDIA"
        elif choice == '6':
            result = parser.get_all_links()
            title = "HYPERLINKS"
        elif choice == '7':
            search_term = input(f"{COLOR_PROMPT}Enter search term: {Style.RESET_ALL}")
            if search_term:
                result = parser.search_site_data(search_term)
                title = f"SEARCH-{search_term[:10]}"
            else:
                print(f"{COLOR_ERROR}Search term cannot be empty.")
                continue
        elif choice == '8':
            search_word = input(f"{COLOR_PROMPT}Enter word to search for in lines: {Style.RESET_ALL}")
            if search_word:
                result = parser.search_line_content(search_word)
                title = f"LINE-{search_word[:10]}"
            else:
                print(f"{COLOR_ERROR}Search word cannot be empty.")
                continue
        elif choice == '9':
            print(f"{COLOR_HEADER}Thank you for using PremiumParser. Goodbye!")
            sys.exit(0)
        else:
            print(f"{COLOR_ERROR}Invalid choice. Please enter a number from 1 to 9.")
            continue
        
        print("\n" + f"{COLOR_RESULT_TITLE}{'#'*40}")
        print(f"{COLOR_RESULT_TITLE}Result: {title}")
        print(f"{COLOR_RESULT_TITLE}{'#'*40}{Style.RESET_ALL}")
        
        if len(result) > MAX_OUTPUT_LENGTH and not result.startswith(COLOR_ERROR):
            print(result[:MAX_OUTPUT_LENGTH] + f"\n... ({COLOR_PROMPT}Truncated: showing first {MAX_OUTPUT_LENGTH} characters{Style.RESET_ALL})")
        else:
            print(result)

        if not result.startswith(COLOR_ERROR):
            parser._save_to_file(result, title)

if __name__ == "__main__":
    main()
