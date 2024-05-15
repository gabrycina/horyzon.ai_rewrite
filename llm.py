import json
import traceback
import os
import re
import requests
from scraper import Scraper
from dotenv import load_dotenv
from openai import OpenAI
from constants import Actions, PromptText
from tqdm import tqdm
from urllib import parse as urlparse
from utils import clean_company_names, clean_linkedin_url, find_user_data_items, get_div_required_data_items, search_llm_extraction

# Load environment variables
load_dotenv()


class LLM:

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.perplexity_client = OpenAI(api_key=os.getenv("PPLX_API_KEY"), base_url="https://api.perplexity.ai")
        self.piloterr_api_key = os.getenv("PILOTERR_API_KEY")
        self.crunchbase_api_key = os.getenv("CRUNCHBASE_API_KEY")
        self.scraper = Scraper()

    def perform_action(self, action, *args, **kwargs):
        match action:
            case Actions.SEARCH_COMPANIES:
                return self.search_companies(*args, **kwargs)
            case Actions.SEARCH_USER_DATA_ITEMS:
                return self.search_user_data_items(*args, **kwargs)
            case Actions.LAUNCH_SEARCH_APIS:
                return self.launch_search_apis(*args, **kwargs)
            case Actions.EXTRACT_INFO:
                return self.extract_info(*args, **kwargs)
            case _:
                raise ValueError(f"Unknown action: {action}")

    def prompt(self, client, model="gpt-3.5-turbo-0125", response_format="json_object", temperature=0.1, system_prompt="", user_prompt="", max_tokens=500):
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": response_format}
        )

    def search_companies(self, industry, region, size):
        """Search for companies using the given industry and region, then find LinkedIn URLs."""

        prompt = PromptText.SEARCH_COMPANIES.value.format(industry=industry, region=region, size=size)
        system_prompt = PromptText.SYSTEM_MARKET_RESEARCHER.value

        try:
            res = self.prompt(
                self.perplexity_client, 
                model="sonar-medium-online", 
                system_prompt=system_prompt, 
                user_prompt=prompt
            )

            if not res.choices[0].message.content:
                # TODO: handle error 
                return

            companies = json.loads(res.choices[0].message.content)
            _, company_names = next(iter(companies.items()))
            clean_company_names(company_names)

        except Exception as e:
            traceback.print_exc()
            print(repr(e))
            return []

        companies = []
        for company_name in tqdm(company_names[:10]):
            try:
                res = self.scraper.call(company_name, industry, region)

                if not res:
                    return

                url_links = [organic_res["url"] for organic_res in res["organicResults"] if "linkedin" in organic_res["url"]]
                linkedin_company_url = url_links[0]
                linkedin_company_url = clean_linkedin_url(linkedin_company_url)

                companies.append({
                    "name": company_name,
                    "linkedin_url": linkedin_company_url
                })
            except Exception as e:
                traceback.print_exc()
                print(f"Failed to process {company_name}: {repr(e)}")

        return companies

    def search_user_data_items(self, user_query):
        res = self.prompt(
            self.openai_client, 
            system_prompt=PromptText.SYSTEM_ANALYST.value, 
            user_prompt=PromptText.USER_DATA_ITEMS.value.format(user_query=user_query)
        )

        if not res or not res.choices[0].message.content:
            # TODO: error handling
            return

        data = json.loads(res.choices[0].message.content)
        data_items = {}

        for idx, data_item in enumerate(data['data_items']):
            result = {}

            res = self.prompt(
                self.openai_client, 
                system_prompt=PromptText.SYSTEM_ANALYST.value, 
                user_prompt=PromptText.DATA_ITEM_DESCRIPTION.value.format(data_item=data_item),
                temperature=0.7,
                response_format="text",
                max_tokens=150
            )

            if not res or not res.choices[0].message.content:
                return

            description = res.choices[0].message.content.strip()

            res = self.prompt(
                self.openai_client, 
                system_prompt=PromptText.SYSTEM_ANALYST.value, 
                user_prompt=PromptText.DATA_ITEM_FORMAT.value.format(data_item=data_item, data_item_description=description),
                response_format="text",
                max_tokens=150
            )

            if not res or not res.choices[0].message.content:
                return

            format = res.choices[0].message.content.strip().lower()

            res = self.prompt(
                self.openai_client,
                system_prompt=PromptText.SYSTEM_ANALYST.value,
                user_prompt=PromptText.DATA_ITEM_INFO_LIST.value.format(data_item=data_item),
                max_tokens=300,
            )

            if not res or not res.choices[0].message.content:
                # TODO: error handling 
                return

            info_list = json.loads(res.choices[0].message.content).get("key_information", [])

            # Build the data item dictionary
            result["name"] = data_item.strip()
            result["description"] = description
            result["format"] = format
            result["info_list"] = info_list

            data_items[f"data_item{idx+1}"] = result

        return data_items

    def launch_search_apis(self, companies_info):
        results = []

        for dict_company in companies_info:
            company_name = dict_company["company_name"]
            company_name_cleaned = re.sub(r'[^ \w+]', '', company_name)
            linkedin_company_url = dict_company["linkedin_url"]

            dict_api_results = {}
            dict_company_linkedin = None

            company_db_object = {}
            company_db_object["search_data"] = {}

            # LinkedIn search
            try:
                linkedin_search_url = f"https://api.linkedin.com/v2/companies/{linkedin_company_url.split('/')[-1]}"
                headers = {'Authorization': f'Bearer {os.getenv("PPLX_API_KEY")}'}
                response = requests.get(linkedin_search_url, headers=headers)
                dict_company_linkedin = response.json()

                dict_api_results["linkedin"] = dict_company_linkedin

                dict_company_linkedin["source"] = linkedin_company_url
                company_db_object["search_data"]["linkedin_search_results"] = dict_company_linkedin
                print("Piloterr results: ", dict_company_linkedin)

            except Exception as e:
                print(repr(e))
                dict_company_linkedin = None

            # Crunchbase search
            crunchbase_company_url = dict_company.get("crunchbase_company_url", "")

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
                    'query': urlparse.quote_plus(company_name_cleaned),
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
                        company_db_object["search_data"]["crunchbase_search_results"] = crunchbase_data
                        print("Crunchbase data found: ", crunchbase_data)
                except Exception as e:
                    print(repr(e))

            results.append(dict_api_results)

        return results

    def extract_info(self, data_items_prompts, list_companies):
        list_answers = []
        for company in list_companies:
            dict_company_answers = {"company": company["company_name"]}

            # Load data
            dict_company_data = {k: v for k, v in db_company_item["search_data"].items()}

            system_prompt_needed_process = PromptText.SYSTEM_NEEDED_PROCESS.value
            system_prompt_helpful_bot = PromptText.SYSTEM_HELPFUL_BOT.value
            system_prompt_market_researcher = PromptText.SYSTEM_MARKET_RESEARCHER.value
            
            div_required_data_items = get_div_required_data_items(self.openai_client, data_items_prompts, system_prompt_needed_process)

            for data_item, data_item_dict in data_items_prompts.items():
                key = data_item_dict["data_item_name"]
                if "data_items" in db_company_item and key in db_company_item["data_items"]:
                    dict_company_answers[key] = db_company_item["data_items"][key][0]['content']
                else:
                    final_dict_company_data = [dict_company_data[k] for k in div_required_data_items[key] if k in dict_company_data]
                    final_answer = []
                    for item in final_dict_company_data:
                        final_answer_temp = find_user_data_items(self.openai_client, key, item, system_prompt_helpful_bot)
                        if final_answer_temp.lower() != "none":
                            final_answer.append({"content": final_answer_temp, "source": item.get("source", "")})
                    if not final_answer:
                        try:
                            llm_answer = search_llm_extraction(self.openai_client, key, company["company_name"], system_prompt_market_researcher)
                            final_answer.append({"content": llm_answer, "source": "Google search"})
                        except KeyError:
                            pass
                    if final_answer:
                        dict_company_answers[key] = final_answer[0]['content']
                    else:
                        dict_company_answers[key] = None

            list_answers.append(dict_company_answers)

        return list_answers
