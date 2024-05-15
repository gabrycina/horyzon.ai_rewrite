import json
import traceback
import os
from scraper import Scraper
from dotenv import load_dotenv
from openai import OpenAI
from constants import Actions, PromptText, SOURCES
from tqdm import tqdm
from linkedin import clean_linkedin_url, clean_company_names, search_linkedin
from crunchbase import search_crunchbase

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
                    # TODO: error handling
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
                # TODO: error handling 
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
                # TODO: error handling 
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

        for company in companies_info:
            results[company["name"]] = {}

            company_linkedin = search_linkedin(company)
            results[company["name"]]["linkedin"] =  company_linkedin

            company_crunchbase = search_crunchbase(company)
            results[company["name"]]["crunchbase"] =  company_crunchbase

        return results

    def extract_info(self, data_items, companies, search_results):
        results = []

        for company in companies:
            company_results = {"company": company["name"]}
            required_data_items = {}

            for _, data_item in data_items.items():
                res = self.prompt(
                    self.openai_client,
                    system_prompt=PromptText.SYSTEM_NEEDED_PROCESS.value, 
                    user_prompt=PromptText.DATA_SOURCE_PROMPT.value.format(
                        data_item_name=data_item["name"],
                        sources=json.dumps(SOURCES, indent=4)
                    )
                )

                if not res or not res.choices[0].message.content: 
                # TODO: error handling 
                    return 

                required_data_items[data_item["name"]] = json.loads(res.choices[0].message.content).get('kept_data_sources')

            filtered_data_items = []
            for key, data_sources in required_data_items.items():
                filtered_data_items.extend([search_results[company["name"]][k] for k in data_sources if k in search_results[company["name"]]])

            answers = []
            for data_item in filtered_data_items:
                res = self.prompt(
                    self.openai_client,
                    temperature=0.7, 
                    system_prompt=PromptText.SYSTEM_HELPFUL_BOT.value, 
                    user_prompt=PromptText.FIND_USER_DATA_ITEMS_PROMPT.value.format(
                        data=data_item, 
                        data_item=company["name"]
                    )
                )

                if not res or not res.choices[0].message.content:
                    continue

                data = res.choices[0].message.content.strip()
                if data.lower() != "none":
                    answers.append({"content": data, "source": data_item.get("source", "")})

            if not answers:
                for key in required_data_items.keys():
                    res = self.prompt(
                        self.openai_client,
                        system_prompt=PromptText.SYSTEM_MARKET_RESEARCHER.value,
                        user_prompt=PromptText.SEARCH_LLM_EXTRACTION_PROMPT.value.format(data_item=key, company_name=company["name"])
                    )

                    if not res or not res.choices[0].message.content:
                        return

                    answers.append({"content": res.choices[0].message.content, "source": "Google search"})

            for key in required_data_items.keys():
                company_results[key] = answers[0]['content'] if answers else None

            results.append(company_results)

        return results



