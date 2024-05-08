import search_companies
from llm import LLM
from costants import Actions

def main(query, industry, region, size):
    # TODO: move to env variables
    llm = LLM(pplx_api_key='your_perplexity_api_key_here', apify_api_token='your_apify_api_token_here')

    companies_info = llm.perform_action(Action.SEARCH_COMPANIES, industry, region, size)

    for company in companies_info:
        print(company)

    data_items_info = llm.perform_action(Action.SEARCH_USER_DATA_ITEMS, query)

    print(json.dumps(data_items_prompts, indent=4))


main("Find all the scam AI companies out there :)", industry="technology", region="California", size="medium-sized")
