import requests
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def fetch_leetcode_stats(username):
    url = 'https://leetcode.com/graphql/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
    }
    payload = {
        'query': '''
        query userProblemsSolved($username: String!) {
          matchedUser(username: $username) {
            submitStats {
              acSubmissionNum {
                difficulty
                count
              }
            }
          }
        }
        ''',
        'variables': {'username': username}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('data', {}).get('matchedUser', {}).get('submitStats', {}).get('acSubmissionNum', [])
            if stats:
                result = {}
                for item in stats:
                    difficulty = item.get('difficulty').lower()
                    count = item.get('count')
                    result[difficulty] = count
                return result
    except Exception as e:
        logger.error(f"Error fetching LeetCode stats for {username}: {e}")
    return None

def fetch_codeforces_stats(username):
    url = f'https://codeforces.com/api/user.status?handle={username}'
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                submissions = data.get('result', [])
                solved_problems = set()
                for sub in submissions:
                    if sub.get('verdict') == 'OK':
                        prob = sub.get('problem', {})
                        prob_id = f"{prob.get('contestId')}{prob.get('index')}"
                        solved_problems.add(prob_id)
                return {
                    'all': len(solved_problems)
                }
    except Exception as e:
        logger.error(f"Error fetching Codeforces stats for {username}: {e}")
    return None

from django.core.cache import cache

def get_profile_stats(profile):
    # Use dynamic cache key based on usernames to auto-invalidate if usernames change
    lc_user = (profile.leetcode_username or '').strip().lower()
    cf_user = (profile.codeforces_username or '').strip().lower()
    cache_key = f"profile_stats_{profile.id}_{lc_user}_{cf_user}"
    
    cached_stats = cache.get(cache_key)
    if cached_stats is not None:
        return cached_stats

    stats = {}
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        if profile.leetcode_username:
            futures['leetcode'] = executor.submit(fetch_leetcode_stats, profile.leetcode_username.strip())
        if profile.codeforces_username:
            futures['codeforces'] = executor.submit(fetch_codeforces_stats, profile.codeforces_username.strip())
            
        for platform, future in futures.items():
            try:
                stats[platform] = future.result()
            except Exception as e:
                logger.error(f"Failed to fetch stats for {platform}: {e}")
                stats[platform] = None
                
    # Cache the result for 300 seconds (5 minutes)
    cache.set(cache_key, stats, 300)
    return stats

