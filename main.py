from llm import LLM
from constants import Actions
import json


def main(query, industry, region, size):
    llm = LLM()

    companies_info = llm.perform_action(Actions.SEARCH_COMPANIES, industry, region, size)
    print(json.dumps(companies_info, indent=4))

    data_items = llm.perform_action(Actions.SEARCH_USER_DATA_ITEMS, query)
    print(json.dumps(data_items, indent=4))

    results = llm.perform_action(Actions.LAUNCH_SEARCH_APIS, companies_info)
    print(json.dumps(results, indent=4))

    # results = llm.perform_action(
    #     Actions.EXTRACT_INFO, data_items_info, companies_info)
    # print(json.dumps(results, indent=4))


main("Companies realising revolutionary AI products born in the last 7 years",
     industry="technology", region="California", size="medium-sized")
