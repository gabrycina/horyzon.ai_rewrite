import json

def find_user_data_items(client, data_item, data, system_prompt):
    user_prompt = f"""
    I am giving you data about a company: {data}.
    I want you to find the following piece of information: {data_item}.
    If no information was found in the given information please answer with 'None' and nothing more.
    If you found the information ONLY return the information as is, nothing more.
    """
    response = chatgpt_api_prompt(client, 0.7, system_prompt, user_prompt)

    if not response.choices[0].message.content:
        # TODO: error handling
        return 

    return response.choices[0].message.content.strip()

def get_div_required_data_items(client, data_items_prompts, system_prompt):
    div_required_data_items = {}
    sources = {
        "linkedin_search_results": "Contains information of a company in LinkedIn. So we can extract a description and very basic general information like the name and location.",
        "crunchbase_search_results": "Contains information of a company in Crunchbase, it's mainly useful for searching financial information on a company like investment rounds",
        "cp_house_search_results": "Contains information of a company in Companies House, it's only useful for searching: Company Name, Registered Office Address, Company Type, Directors and People with Significant Control, Annual accounts",
    }
    for _, data_item_dict in data_items_prompts.items():
        user_prompt = f"""
        Here is the search term you should act on: {data_item_dict["data_item_name"]},
        You are expected to find the right data sources from this list:
        {json.dumps(sources, indent=4)}
        Please answer in json in the following format:
        {{kept_data_sources: []}}
        where the contents of kept_data_sources list the keys of the data sources provided
        """
        response = chatgpt_api_prompt(client, "json_object", 0.1, system_prompt, user_prompt)
        div_required_data_items[data_item_dict["data_item_name"]] = json.loads(
            response.choices[0].message.content).get('kept_data_sources', list(sources.keys()))
    return div_required_data_items

def search_llm_extraction(client, data_item, company_name, system_prompt):
    user_prompt = f"""
    Can you provide me the {data_item} of this company: {company_name}?
    The answer should be short and concise, it should only answer with the requested data:
    Don't form phrases, only give the number or a single word to answer the question
    If no data was found answer with None
    """
    response = chatgpt_api_prompt(client, "json_object", 0.1, system_prompt, user_prompt)
    return response.choices[0].message.content

