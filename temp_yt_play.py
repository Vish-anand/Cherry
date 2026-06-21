
import sys
from playwright.sync_api import sync_playwright

query = 'project hail mary trailer'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, channel='chrome')
    page = browser.new_page()
    search_url = 'https://www.youtube.com/results?search_query=' + query.replace(' ', '+')
    page.goto(search_url)
    page.wait_for_load_state('networkidle', timeout=10000)
    
    # Click the first non-ad video result
    first_video = page.query_selector('ytd-video-renderer a#video-title')
    if first_video:
        href = first_video.get_attribute('href')
        if href:
            video_url = 'https://www.youtube.com' + href
            page.goto(video_url)
            page.wait_for_timeout(2000)
            print(f'Playing: {video_url}')
            # Keep browser open
            import time
            time.sleep(3)
        else:
            print('Found video but no href.')
    else:
        print('No video found, opening search results.')
    
    # Do NOT close browser — leave it open for the user
    browser.contexts[0].pages[0].bring_to_front()
    print('Done')
