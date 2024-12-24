from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'YOUR_MONGODB_URI')
DB_NAME = 'qubic'
COLLECTION_NAME = 'network_stats'

# API Configuration
QUBIC_API_KEY = os.getenv('QUBIC_API_KEY')
QUBIC_USERNAME = os.getenv('QUBIC_USERNAME', 'YOUR_QUBIC_USERNAME')
QUBIC_PASSWORD = os.getenv('QUBIC_PASSWORD', 'YOUR_QUBIC_PASSWORD')

# Vercel Configuration
VERCEL_PROJECT_ID = os.getenv('VERCEL_PROJECT_ID', 'YOUR_VERCEL_PROJECT_ID')
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN', 'YOUR_VERCEL_TOKEN')

# Cache Configuration
CACHE_DURATION = 300  # 5 minutes cache duration

# API URLs
QUBIC_API_BASE = 'https://api.qubic.li'
APOOL_API_BASE = 'https://client.apool.io'
SOLUTIONS_API_BASE = 'https://pool.qubic.solutions'
MINERLAB_API_BASE = 'https://minerlab-qubic.azure-api.net/rest/v1'
EXCHANGE_RATE_API = 'https://open.er-api.com/v6/latest/USD'

# CORS Configuration
CORS_ORIGINS = [
    'https://tool.qubic.site',     # Production domain
    'https://qubic-tools.vercel.app',  # Test domain
    'http://localhost:*',          # Local development environment
    'http://127.0.0.1:*'          # Local development environment
]

# CORS Configuration Options
CORS_OPTIONS = {
    'origins': CORS_ORIGINS,
    'methods': ['GET', 'POST', 'OPTIONS'],
    'allow_headers': ['Content-Type', 'Authorization'],
    'expose_headers': ['Content-Range', 'X-Total-Count'],
    'supports_credentials': True,
    'max_age': 600,  # Preflight request cache time (seconds)
}

# Headers Configuration
DEFAULT_HEADERS = {
    'authority': 'api.qubic.li',
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json-patch+json',
    'origin': 'https://app.qubic.li',
    'referer': 'https://app.qubic.li/',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}
