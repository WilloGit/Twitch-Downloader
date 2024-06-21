import requests

class ClipFetcher:
    def __init__(self, username, time_period):
        self.username = username
        self.time_period = self.convert_time_period(time_period)
        self.cursor = ""
        self.headers = {
            'Client-ID': 'kd1unb4b3q4t58fwlpcbzcbnm76a8fp',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def convert_time_period(self, period): 
        period_map = {
            "24h": "LAST_DAY",
            "7d": "LAST_WEEK",
            "30d": "LAST_MONTH",
            "all": "ALL_TIME"
        }
        return period_map.get(period, "LAST_WEEK")


    def fetch_clips(self, limit=30):
        url = "https://gql.twitch.tv/gql"
        query = f"""
        query {{
            user(login: "{self.username}") {{
                clips(first: {limit}, after: "{self.cursor}", criteria: {{ period: {self.time_period} }}) {{
                    edges {{
                        cursor
                        node {{
                            id
                            slug
                            title
                            createdAt
                            durationSeconds
                            thumbnailURL
                            viewCount
                            game {{
                                id
                                displayName
                            }}
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                        hasPreviousPage
                    }}
                }}
            }}
        }}
        """
        payload = {
            "query": query,
            "variables": {}
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            clips = data['data']['user']['clips']['edges']
            if clips:
                self.cursor = clips[-1]['cursor']
            
            return [clip['node'] for clip in clips]
        except requests.RequestException as e:
            print(f"Error fetching clips: {e}")
            return []
        except (KeyError, IndexError) as e:
            print(f"Error parsing clip data: {e}")
            return []

def get_clip_fetcher(username, time_period):
    return ClipFetcher(username, time_period)

def fetch_clips(clip_fetcher, limit=30):
    return clip_fetcher.fetch_clips(limit)
