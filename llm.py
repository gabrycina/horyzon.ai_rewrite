import json
import os
import re
import urllib
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
from openai import OpenAI
from constants import Actions, PromptText
from tqdm import tqdm

# Load environment variables
load_dotenv()


class LLM:

    # TODO: move to env file
    def __init__(self, api_key):
        mongo_uri = os.getenv("MONGO_URI")
        self.mongo_db_client = MongoClient(
            mongo_uri)['mydatabase']['mycollection']
        self.client = OpenAI(api_key=api_key)
        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.piloterr_api_key = os.getenv("PILOTERR_API_KEY")
        self.crunchbase_api_key = os.getenv("CRUNCHBASE_API_KEY")

    def perform_action(self, action, *args, **kwargs):
        """Perform an action based on the given action enum."""
        if action == Actions.SEARCH_COMPANIES:
            return self.search_companies(*args, **kwargs)
        elif action == Actions.SEARCH_USER_DATA_ITEMS:
            return self.search_user_data_items(*args, **kwargs)
        elif action == Actions.LAUNCH_SEARCH_APIS:
            return self.launch_search_apis(*args, **kwargs)
        elif action == Actions.EXTRACT_INFO:
            return self.extract_info(*args, **kwargs)
        else:
            raise ValueError(f"Unknown action: {action}")

    def search_companies(self, industry, region, size):
        """Search for companies using the given industry and region, then find LinkedIn URLs."""

        prompt = f"""
        Can you provide me with a list of 15 companies operating in the {industry} industry, located in this region {region} and
        that have an approximate size of {size}.
        No need to give a numbered list.
        The company name must be short and concise.
        Answer in json format with this format {{industry: list_of_companies}}.
        """
        system_prompt = "You are a professional market researcher"

        # Use the LLM to get a list of companies
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.openai_client.chat.completions.create(
            model="sonar-medium-online",
            messages=messages,
            response_format={"type": "json_object"}
        )

        try:
            dict_companies = json.loads(response.choices[0].message.content)
            key = list(dict_companies.keys())[0]
            companies_names = dict_companies[key]

            # Clean the company names
            companies_names = [re.sub(r"\((.*?)\)", "", company_name).strip()
                               for company_name in companies_names]
            companies_names = [" ".join(word for word in company_name.split() if word.lower() not in ["uk", "plc"])
                               for company_name in companies_names]
        except Exception as e:
            print(repr(e))
            return []

        # List to hold companies information
        companies = []

        # Iterate over the companies to find their LinkedIn URLs
        for company_name in tqdm(companies_names[:10]):
            try:
                # Construct the Google search query
                google_query = f"{company_name} {industry} in {region} site:www.linkedin.com/company/"

                # Prepare the Apify Actor input
                run_input = {
                    # Adjusted to a list for the updated search method signature
                    "queries": [google_query],
                    "maxPagesPerQuery": 1,
                    "resultsPerPage": 10,
                    "mobileResults": False,
                    "languageCode": "",
                    "maxConcurrency": 10,
                    "saveHtml": False,
                    "saveHtmlToKeyValueStore": False,
                    "includeUnfilteredResults": False,
                    "customDataFunction": """async ({ input, $, request, response, html }) => {
                        return {
                            pageTitle: $('title').text(),
                        };
                    };"""
                }

                # Run the Actor and wait for it to finish
                query_run = self.apify_client.actor(
                    "nFJndFXA5zjCTuudP").call(run_input=run_input)

                # Extract data from the search query
                search_data = list(self.apify_client.dataset(
                    query_run["defaultDatasetId"]).iterate_items())[0]

                # Extract the first LinkedIn URL
                url_links = [organic_res["url"]
                             for organic_res in search_data["organicResults"] if "linkedin" in organic_res["url"]]
                linkedin_company_url = url_links[0]

                # Clean the LinkedIn URL
                if linkedin_company_url.endswith("/jobs"):
                    linkedin_company_url = linkedin_company_url.strip("/jobs")
                linkedin_company_url = "/".join(
                    linkedin_company_url.split("/")[:5])
                linkedin_company_url = linkedin_company_url.partition("?")[0]

                # Append company info to the list
                companies.append({
                    "company_name": company_name,
                    "linkedin_url": linkedin_company_url
                })
            except Exception as e:
                print(f"Failed to process {company_name}: {repr(e)}")

        return companies

    def search_user_data_items(self, user_query):
        system_prompt = PromptText.SYSTEM_ANALYST.value

        # Step 1: User Data Items
        user_data_items_prompt = PromptText.USER_DATA_ITEMS.value.format(
            user_query=user_query)

        user_data_response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_data_items_prompt}
            ],
            max_tokens=500,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        dict_data_items = json.loads(
            user_data_response.choices[0].message.content)

        # Initialize the final dictionary to hold data item prompts
        data_items_prompts = {}

        # Step 2: Process Each Data Item
        for idx, data_item in enumerate(dict_data_items['data_items']):
            dict_data_item = {}

            # Description Prompt
            data_item_description_prompt = PromptText.DATA_ITEM_DESCRIPTION.value.format(
                data_item=data_item)

            data_item_description_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_item_description_prompt}
                ],
                max_tokens=150,
                temperature=0.7,
                response_format={"type": "text"}
            )

            data_item_description = data_item_description_response.choices[0].message.content.strip(
            )

            # Format Prompt
            data_item_format_prompt = PromptText.DATA_ITEM_FORMAT.value.format(
                data_item=data_item, data_item_description=data_item_description)

            data_item_format_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_item_format_prompt}
                ],
                max_tokens=150,
                temperature=0.1,
                response_format={"type": "text"}
            )

            data_item_format = data_item_format_response.choices[0].message.content.strip(
            ).lower()

            # Information List Prompt
            data_item_info_list_prompt = PromptText.DATA_ITEM_INFO_LIST.value.format(
                data_item=data_item)

            data_item_info_list_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_item_info_list_prompt}
                ],
                max_tokens=300,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            data_item_info_list = json.loads(
                data_item_info_list_response.choices[0].message.content)

            # Build the data item dictionary
            dict_data_item["data_item_name"] = data_item.strip()
            dict_data_item["data_item_description"] = data_item_description
            dict_data_item["data_item_format"] = data_item_format
            dict_data_item["data_item_info_list"] = data_item_info_list.get(
                "key_information", [])

            # Update the main dictionary with the processed data item
            data_items_prompts[f"data_item{idx+1}"] = dict_data_item

        return data_items_prompts

    def launch_search_apis(self, list_cookies, dict_company):
        company_name = dict_company["company_name"]
        company_name_cleaned = re.sub(r'[^ \w+]', '', company_name)
        linkedin_company_url = dict_company["linkedin_url"]

        company_db_object = self.mongo_db_client.find_one(
            {"_id": linkedin_company_url})
        if not company_db_object:
            dict1 = {k: v for k, v in dict_company.items()
                     if "linkedin_url" not in k}
            dict2 = {"_id": linkedin_company_url,
                     "data_items": {}, "search_data": {}}
            dict2.update(dict1)
            print("Intended insert: ", dict2)
            self.mongo_db_client.insert_one(dict2)
            company_db_object = self.mongo_db_client.find_one(
                {"_id": linkedin_company_url})

        dict_api_results = {}

        # LinkedIn search
        if "linkedin_search_results" not in company_db_object["search_data"]:
            try:
                linkedin_search_url = f"https://api.linkedin.com/v2/companies/{linkedin_company_url.split('/')[-1]}"
                headers = {'Authorization': f'Bearer {self.piloterr_api_key}',
                           'Cookie': '; '.join(list_cookies)}
                response = requests.get(linkedin_search_url, headers=headers)
                dict_company_linkedin = response.json()

                dict_api_results["linkedin"] = dict_company_linkedin

                if "error" not in dict_company_linkedin:
                    dict_company_linkedin["source"] = linkedin_company_url
                    self.mongo_db_client.update_one(
                        {"_id": linkedin_company_url},
                        {"$push": {
                            "search_data.linkedin_search_results": dict_company_linkedin}}
                    )
                print("Piloterr results: ", dict_company_linkedin)

            except Exception as e:
                print(repr(e))
                dict_company_linkedin = None

        # Crunchbase search
        crunchbase_company_url = dict_company.get("crunchbase_company_url", "")
        if "crunchbase_search_results" not in company_db_object["search_data"]:
            if not crunchbase_company_url and dict_company_linkedin:
                try:
                    crunchbase_company_url = dict_company_linkedin.get(
                        "crunchbaseFundingData", {}).get("organizationUrl", "")
                except Exception as e:
                    print(repr(e))
                    print("Crunchbase data not found in LinkedIn company dictionary")

            if not crunchbase_company_url:
                crunchbase_url = "https://api.crunchbase.com/api/v4/autocompletes"
                params = {
                    'user_key': self.crunchbase_api_key,
                    'query': urllib.parse.quote_plus(company_name_cleaned),
                    'collection_ids': 'organization.companies'
                }
                response = requests.get(crunchbase_url, params=params)
                if response.status_code == 200:
                    companies = response.json()["entities"]
                    for company in companies:
                        permalink = company["identifier"]["permalink"]
                        if linkedin_company_url:
                            linkedin_check_url = f"https://api.crunchbase.com/api/v4/entities/organizations/{permalink}?field_ids=linkedin"
                            response2 = requests.get(linkedin_check_url)
                            if response2.status_code == 200:
                                json_response = response2.json()
                                if json_response["properties"].get("linkedin", {}).get("value") == linkedin_company_url:
                                    crunchbase_company_url = permalink
                                    break
                        else:
                            crunchbase_company_url = permalink
                            break
                print("Crunchbase permalink found: ", crunchbase_company_url)

            if crunchbase_company_url:
                crunchbase_search_url = f"https://api.crunchbase.com/api/v4/entities/organizations/{crunchbase_company_url}?user_key={self.crunchbase_api_key}"
                try:
                    response = requests.get(crunchbase_search_url)
                    if response.status_code == 200:
                        crunchbase_data = response.json()
                        dict_api_results["crunchbase"] = crunchbase_data
                        self.mongo_db_client.update_one(
                            {"_id": linkedin_company_url},
                            {"$push": {
                                "search_data.crunchbase_search_results": crunchbase_data}}
                        )
                        print("Crunchbase data found: ", crunchbase_data)
                except Exception as e:
                    print(repr(e))

        return dict_api_results

    def extract_info(self, data_items_prompts, list_companies):
        def chatgpt_api_prompt(response_format_type="json_object", temperature=0.1, system_prompt="", user_prompt=""):
            messages = [{"role": "system", "content": system_prompt}, {
                "role": "user", "content": user_prompt}]
            return self.client.chat.completions.create(
                model="gpt-3.5-turbo-0125",
                messages=messages,
                max_tokens=500,
                temperature=temperature,
                response_format={"type": response_format_type}
            )

        def find_user_data_items(data_item, data):
            system_prompt = PromptText.SYSTEM_HELPFUL_BOT.value
            user_prompt = f"""
            I am giving you data about a company: {data}.
            I want you to find the following piece of information: {data_item}.
            If no information was found in the given information please answer with 'None' and nothing more.
            If you found the information ONLY return the information as is, nothing more.
            """
            response = chatgpt_api_prompt(
                "text", 0.7, system_prompt, user_prompt)
            return response.choices[0].message.content.strip()

        def get_div_required_data_items(data_items_prompts):
            div_required_data_items = {}
            for data_item, data_item_dict in data_items_prompts.items():
                system_prompt = PromptText.SYSTEM_NEEDED_PROCESS.value
                sources = {
                    "linkedin_search_results": "Contains information of a company in LinkedIn. So we can extract a description and very basic general information like the name and location.",
                    "crunchbase_search_results": "Contains information of a company in Crunchbase, it's mainly useful for searching financial information on a company like investment rounds",
                    "cp_house_search_results": "Contains information of a company in Companies House, it's only useful for searching: Company Name, Registered Office Address, Company Type, Directors and People with Significant Control, Annual accounts",
                }
                user_prompt = f"""
                Here is the search term you should act on: {data_item_dict["data_item_name"]},
                You are expected to find the right data sources from this list:
                {json.dumps(sources, indent=4)}
                Please answer in json in the following format:
                {{kept_data_sources: []}}
                where the contents of kept_data_sources list the keys of the data sources provided
                """
                response = chatgpt_api_prompt(
                    "json_object", 0.1, system_prompt, user_prompt)
                div_required_data_items[data_item_dict["data_item_name"]] = json.loads(
                    response.choices[0].message.content).get('kept_data_sources', list(sources.keys()))
            return div_required_data_items

        def search_llm_extraction(data_item, company_name):
            system_prompt = PromptText.SYSTEM_MARKET_RESEARCHER.value
            user_prompt = f"""
            Can you provide me the {data_item} of this company: {company_name}?
            The answer should be short and concise, it should only answer with the requested data:
            Don't form phrases, only give the number or a single word to answer the question
            If no data was found answer with None
            """
            response = chatgpt_api_prompt(
                "json_object", 0.1, system_prompt, user_prompt)
            return response.choices[0].message.content

        list_answers = []
        for company in list_companies:
            dict_company_answers = {"company": company["company_name"]}
            db_company_item = self.mongo_db_client.find_one(
                {"_id": company["linkedin_url"]})

            if not db_company_item:
                print(
                    f"Couldn't find company in db {company['linkedin_url']} MAJOR ERROR shouldn't happen")
                continue

            # Load data
            dict_company_data = {k: v for k,
                                 v in db_company_item["search_data"].items()}

            div_required_data_items = get_div_required_data_items(
                data_items_prompts)

            for data_item, data_item_dict in data_items_prompts.items():
                key = data_item_dict["data_item_name"]
                if "data_items" in db_company_item and key in db_company_item["data_items"]:
                    dict_company_answers[key] = db_company_item["data_items"][key][0]['content']
                else:
                    final_dict_company_data = [
                        dict_company_data[k] for k in div_required_data_items[key] if k in dict_company_data]
                    final_answer = []
                    for item in final_dict_company_data:
                        final_answer_temp = find_user_data_items(key, item)
                        if final_answer_temp.lower() != "none":
                            final_answer.append(
                                {"content": final_answer_temp, "source": item.get("source", "")})
                    if not final_answer:
                        try:
                            llm_answer = search_llm_extraction(
                                key, company["company_name"])
                            final_answer.append(
                                {"content": llm_answer, "source": "Google search"})
                        except KeyError:
                            pass
                    if final_answer:
                        dict_company_answers[key] = final_answer[0]['content']
                        mongo_db_client.update_one({"_id": company["linkedin_url"]}, {
                                                   "$set": {f"data_items.{key}": final_answer}})
                    else:
                        dict_company_answers[key] = None
                        mongo_db_client.update_one({"_id": company["linkedin_url"]}, {
                                                   "$set": {f"data_items.{key}": None}})

            list_answers.append(dict_company_answers)

        return list_answers
