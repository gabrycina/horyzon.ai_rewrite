import re
import requests
import os

def clean_company_names(companies_names):
    parentheses_pattern = re.compile(r"\((.*?)\)", re.IGNORECASE)
    unwanted_words = {"uk", "plc"}

    def clean_name(name):
        name = re.sub(parentheses_pattern, "", name).strip()
        name = " ".join(word for word in name.split() if word.lower() not in unwanted_words)
        return name

    return [clean_name(company_name) for company_name in companies_names]

def clean_linkedin_url(url):
    if url.endswith("/jobs"):
        url = url[:-5]

    url = "/".join(url.split("/")[:5])
    url = url.partition("?")[0]

    return url

def search_linkedin(company):
    name = company["name"]
    linkedin_company_url = clean_linkedin_url(company["linkedin_url"])

    try:
        res = requests.get(
            f"https://api.linkedin.com/v2/companies/{linkedin_company_url.split('/')[-1]}",
            headers={'Authorization': f'Bearer {os.getenv("PPLX_API_KEY")}'}
        )
        res.raise_for_status()
        company_linkedin = res.json()        
        company_linkedin["source"] = linkedin_company_url
        print("LinkedIn results: ", company_linkedin)
    except requests.RequestException as e:
        print(f"Error during LinkedIn API request for {name}: {e}")
        return None

    return company_linkedin

