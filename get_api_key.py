import requests
import json
import os
from dotenv import load_dotenv

def get_api_key(email, password, twoFactorCode):
    """
    Get Qubic API key by logging in with email and password
    """
    try:
        # Login to get token
        login_url = "https://api.qubic.li/Auth/Login"
        login_data = {
            "userName": email,
            "password": password,
            "twoFactorCode": twoFactorCode
        }
        
        headers = {
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
        
        response = requests.post(login_url, headers=headers, json=login_data)
        response.raise_for_status()
        
        # Print response content
        print("Response status:", response.status_code)
        print("Response content:", response.text)
        
        # Get token
        response_data = response.json()
        print("Response JSON:", response_data)
        
        if not response_data.get('success'):
            raise Exception("Login failed")
            
        token = response_data.get('token')
        if not token:
            raise Exception("Failed to get token from response")
            
        # Update .env file
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        
        # Read existing .env file content
        existing_content = ""
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                existing_content = f.read()
        
        # Update or add QUBIC_API_KEY
        if 'QUBIC_API_KEY=' in existing_content:
            # Replace existing API KEY
            lines = existing_content.splitlines()
            new_lines = []
            for line in lines:
                if line.startswith('QUBIC_API_KEY='):
                    new_lines.append(f'QUBIC_API_KEY={token}')
                else:
                    new_lines.append(line)
            new_content = '\n'.join(new_lines)
        else:
            # Add new API KEY
            new_content = existing_content.rstrip() + f'\nQUBIC_API_KEY={token}\n'
        
        # Write to .env file
        with open(env_path, 'w') as f:
            f.write(new_content)
            
        print("Successfully updated API key in .env file")
        return token
        
    except requests.exceptions.RequestException as e:
        print(f"Error during API request: {str(e)}")
        if hasattr(e, 'response'):
            print(f"Response content: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == '__main__':
    # Set your email and password here
    email = "YOUR_QUBICLI_EMAIL"    # Replace with your email
    password = "YOUR_QUBICLI_PASSWORD"        # Replace with your password
    twoFactorCode = ""              # Replace with your 2FA code if enabled
    
    api_key = get_api_key(email, password, twoFactorCode)
    if api_key:
        print("Successfully obtained API key")
    else:
        print("Failed to obtain API key")
