import os
import json
import re
from openai import OpenAI
from apify_client import ApifyClient
from tqdm import tqdm
from enum import Enum, auto
from constants import Actions

class LLM:

    # TODO: move to env file
    def __init__(self, pplx_api_key, apify_api_token):
        self.openai_client = OpenAI(api_key=pplx_api_key, base_url="https://api.perplexity.ai")
        self.apify_client = ApifyClient(apify_api_token)

    def perform_action(self, action, *args, **kwargs):
        """Perform an action based on the given action enum."""
        if action == Action.SEARCH_COMPANIES:
            return self.search_companies(*args, **kwargs)
        elif action == Action.SEARCH_USER_DATA_ITEMS:
            return self.search_user_data_items(*args, **kwargs)
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
            companies_names = [re.sub(r"\((.*?)\)", "", company_name).strip() for company_name in companies_names]
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
                    "queries": [google_query],  # Adjusted to a list for the updated search method signature
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
                query_run = self.apify_client.actor("nFJndFXA5zjCTuudP").call(run_input=run_input)

                # Extract data from the search query
                search_data = list(self.apify_client.dataset(query_run["defaultDatasetId"]).iterate_items())[0]

                # Extract the first LinkedIn URL
                url_links = [organic_res["url"] for organic_res in search_data["organicResults"] if "linkedin" in organic_res["url"]]
                linkedin_company_url = url_links[0]

                # Clean the LinkedIn URL
                if linkedin_company_url.endswith("/jobs"):
                    linkedin_company_url = linkedin_company_url.strip("/jobs")
                linkedin_company_url = "/".join(linkedin_company_url.split("/")[:5])
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
        user_data_items_prompt = PromptText.USER_DATA_ITEMS.value.format(user_query=user_query)
        
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

        dict_data_items = json.loads(user_data_response.choices[0].message.content)

        # Initialize the final dictionary to hold data item prompts
        data_items_prompts = {}

        # Step 2: Process Each Data Item
        for idx, data_item in enumerate(dict_data_items['data_items']):
            dict_data_item = {}

            # Description Prompt
            data_item_description_prompt = PromptText.DATA_ITEM_DESCRIPTION.value.format(data_item=data_item)
            
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

            data_item_description = data_item_description_response.choices[0].message.content.strip()

            # Format Prompt
            data_item_format_prompt = PromptText.DATA_ITEM_FORMAT.value.format(data_item=data_item, data_item_description=data_item_description)

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

            data_item_format = data_item_format_response.choices[0].message.content.strip().lower()

            # Information List Prompt
            data_item_info_list_prompt = PromptText.DATA_ITEM_INFO_LIST.value.format(data_item=data_item)

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

            data_item_info_list = json.loads(data_item_info_list_response.choices[0].message.content)

            # Build the data item dictionary
            dict_data_item["data_item_name"] = data_item.strip()
            dict_data_item["data_item_description"] = data_item_description
            dict_data_item["data_item_format"] = data_item_format
            dict_data_item["data_item_info_list"] = data_item_info_list.get("key_information", [])

            # Update the main dictionary with the processed data item
            data_items_prompts[f"data_item{idx+1}"] = dict_data_item

        return data_items_prompts



