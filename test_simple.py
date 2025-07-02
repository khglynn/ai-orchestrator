#!/usr/bin/env python3
"""
Simple test of AI orchestration - just Claude for now
"""
import os
import asyncio
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

async def test_claude():
    """Test Claude API"""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in .env file")
        return
    
    print("🔄 Testing Claude API...")
    
    try:
        # Create client
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        # Simple test prompt
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": "Say 'Hello, I'm working!' in exactly 5 words."}]
        )
        
        print("✅ Claude responded:", response.content[0].text)
        print(f"📊 Tokens used: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Simple AI Orchestration Test")
    print("=" * 40)
    asyncio.run(test_claude())
