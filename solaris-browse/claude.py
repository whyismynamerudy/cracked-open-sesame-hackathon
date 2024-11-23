from anthropic import Anthropic
from dotenv import load_dotenv
import os

def main():
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        print("Error: CLAUDE_API_KEY not found in environment variables")
        return
    
    try:
        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)
        
        # Perform a simple health check request
        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": "Respond with 'OK' if you can read this."
            }]
        )
        
        print("Claude API Health Check:")
        print(f"Status: Connected successfully")
        print(f"Response: {response.content}")
        
    except Exception as e:
        print("Claude API Health Check:")
        print(f"Status: Error")
        print(f"Details: {str(e)}")

if __name__ == "__main__":
    main()
