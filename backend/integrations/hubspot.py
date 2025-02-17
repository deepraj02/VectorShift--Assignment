import json
import secrets
import base64
import hashlib
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis
import urllib


CLIENT_ID = '28a2528a-d2bb-42cb-8fc2-721acbff07e3'
CLIENT_SECRET = '2817da06-bac5-4a60-a37b-51046501b9ec'
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
SCOPES = 'oauth crm.objects.companies.read'

authorization_url = (
    f"https://app.hubspot.com/oauth/authorize?client_id={urllib.parse.quote(CLIENT_ID)}"
    f"&scope={urllib.parse.quote(SCOPES)}"
    f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
    
)

async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }
    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.query_params.get('error_description'))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(urllib.parse.unquote(encoded_state).replace('\\"', '"'))

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')

    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': CLIENT_SECRET,
                    'redirect_uri': REDIRECT_URI,
                    'code': code
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                }
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)
    
    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

def create_integration_item_metadata_object(contact: dict) -> IntegrationItem: 
    return IntegrationItem(
        id=contact.get('vid'),
        name=f"{contact.get('properties', {}).get('firstname', {}).get('value', '')} {contact.get('properties', {}).get('lastname', {}).get('value', '')}",
        type='Contact',
        parent_id=None,
        parent_path_or_name=None,
    )   

async def get_items_hubspot(credentials) -> list[IntegrationItem]:
    credentials = json.loads(credentials)
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://api.hubapi.com/contacts/v1/lists/all/contacts/all',
            params={'count': 100},
            headers={'Authorization': f'Bearer {credentials.get("access_token")}'}
        )

    if response.status_code == 200:
        contacts = response.json().get('contacts', [])
        list_of_integration_item_metadata = [
            create_integration_item_metadata_object(contact)
            for contact in contacts
        ]
        return list_of_integration_item_metadata
    else:
        raise HTTPException(status_code=response.status_code, detail='Failed to fetch HubSpot contacts')