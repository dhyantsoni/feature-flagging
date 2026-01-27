"""
Simple test endpoint to verify @vercel/python works
"""

def handler(request):
    return {
        'statusCode': 200,
        'body': 'Hello from Vercel Python Runtime!'
    }
