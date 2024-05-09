import search_companies
from llm import LLM
from costants import Actions
import json


def main(query, industry, region, size):
    # TODO: move to env variables
    llm = LLM(pplx_api_key='your_perplexity_api_key_here',
              apify_api_token='your_apify_api_token_here')

    companies_info = llm.perform_action(
        Actions.SEARCH_COMPANIES, industry, region, size)
    for company in companies_info:
        print(company)

    data_items_info = llm.perform_action(Actions.SEARCH_USER_DATA_ITEMS, query)
    print(json.dumps(data_items_info, indent=4))

    results = llm.perform_action(
        Action.LAUNCH_SEARCH_APIS, list_cookies=list_cookies, dict_company=dict_company)
    print(json.dumps(results, indent=4))

    results = llm.perform_action(
        Actions.EXTRACT_INFO, data_items_info, companies_info)
    print(json.dumps(results, indent=4))


main("Find all the scam AI companies out there :)",
     industry="technology", region="California", size="medium-sized")
