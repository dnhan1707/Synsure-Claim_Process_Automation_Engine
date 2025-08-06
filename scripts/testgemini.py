import asyncio
import sys
import os

# Add the parent directory to the Python path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service.model import testgemini

async def main():
    try:
        await testgemini()
    except Exception as e:
        print(f"Error running testgemini: {e}")

if __name__ == "__main__":
    asyncio.run(main())