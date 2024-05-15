import requests
import urllib.parse as urlparse
import os

def get_crunchbase_company_url_from_linkedin(linkedin_company_data):
    try:
        return linkedin_company_data.get("crunchbaseFundingData", {}).get("organizationUrl", "")
    except Exception as e:
        print(repr(e))
        print("Crunchbase data not found in LinkedIn company dictionary")
        return ""

def search_crunchbase_autocomplete(company_name, crunchbase_api_key):
    crunchbase_url = "https://api.crunchbase.com/api/v4/autocompletes"
    params = {
        'user_key': crunchbase_api_key,
        'query': urlparse.quote_plus(company_name),
        'collection_ids': 'organization.companies'
    }
    response = requests.get(crunchbase_url, params=params)
    if response.status_code == 200:
        return response.json().get("entities", [])
    else:
        print(f"Failed to search Crunchbase autocomplete: {response.status_code}")
        return []

def fetch_linkedin_url_from_crunchbase(permalink, crunchbase_api_key):
    linkedin_check_url = f"https://api.crunchbase.com/api/v4/entities/organizations/{permalink}?field_ids=linkedin"
    response = requests.get(linkedin_check_url, params={'user_key': crunchbase_api_key})
    if response.status_code == 200:
        json_response = response.json()
        return json_response["properties"].get("linkedin", {}).get("value")
    return None

def find_matching_crunchbase_permalink(companies, linkedin_company_url, crunchbase_api_key):
    for company in companies:
        permalink = company["identifier"]["permalink"]
        if linkedin_company_url:
            linkedin_url = fetch_linkedin_url_from_crunchbase(permalink, crunchbase_api_key)
            if linkedin_url == linkedin_company_url:
                return permalink
        else:
            return permalink
    return ""

def fetch_crunchbase_data(crunchbase_company_url, crunchbase_api_key):
    crunchbase_search_url = f"https://api.crunchbase.com/api/v4/entities/organizations/{crunchbase_company_url}?user_key={crunchbase_api_key}"
    response = requests.get(crunchbase_search_url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch Crunchbase data: {response.status_code}")
        return {}

def search_crunchbase(company):
    company_name = company.get("name")
    linkedin_company_url = company.get("linkedin_url")
    crunchbase_company_url = company.get("crunchbase_company_url", "")
    crunchbase_api_key = os.getenv("CRUNCHBASE_API_KEY")

    crunchbase_data = {}

    if not crunchbase_company_url and linkedin_company_url:
        crunchbase_company_url = get_crunchbase_company_url_from_linkedin(linkedin_company_url)

    if not crunchbase_company_url:
        companies = search_crunchbase_autocomplete(company_name, crunchbase_api_key)
        crunchbase_company_url = find_matching_crunchbase_permalink(companies, linkedin_company_url, crunchbase_api_key)
        print("Crunchbase permalink found: ", crunchbase_company_url)

    if crunchbase_company_url:
        crunchbase_data = fetch_crunchbase_data(crunchbase_company_url, crunchbase_api_key)
        if crunchbase_data:
            print("Crunchbase data found: ", crunchbase_data)

    return crunchbase_data
