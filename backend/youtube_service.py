from youtube_transcript_api import YouTubeTranscriptApi
import re

class YouTubeService:
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
            r'youtube\.com\/embed\/([^&\n?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_transcript(self, video_url: str) -> dict:
        """Get transcript from YouTube video"""
        video_id = self.extract_video_id(video_url)
        
        if not video_id:
            return {"error": "Invalid YouTube URL"}
        
        try:
            ytt_api = YouTubeTranscriptApi()

            # transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_list = ytt_api.fetch(video_id).to_raw_data()
            full_text = " ".join([entry['text'] for entry in transcript_list])
            
            return {
                "success": True,
                "video_id": video_id,
                "full_text": full_text,
                "segments": transcript_list
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# TEST IT
if __name__ == "__main__":
    yt = YouTubeService()
    
    test_url = "https://www.youtube.com/watch?v=kqtD5dpn9C8"
    
    print("Fetching transcript...")
    result = yt.get_transcript(test_url)
    
    if result.get("success"):
        print(f"✅ Success!")
        print(f"Video ID: {result['video_id']}")
        print(f"Transcript length: {len(result['full_text'])} characters")
        print(f"Preview: {result['full_text'][:300]}...")
    else:
        print(f"❌ Error: {result.get('error')}")