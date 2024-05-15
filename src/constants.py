from enum import Enum, auto

class Actions(Enum): 
    SEARCH_COMPANIES = auto(), 
    SEARCH_USER_DATA_ITEMS = auto(), 
    LAUNCH_SEARCH_APIS = auto(), 
    EXTRACT_INFO = auto()

class PromptText(Enum):
    SEARCH_COMPANIES = """
        Can you provide me with a list of 15 companies operating in the {industry} industry, located in this region {region} and
        that have an approximate size of {size}.
        No need to give a numbered list.
        The company name must be short and concise.
        Answer in json format with this format {{industry: list_of_companies}}. 
    """

    USER_DATA_ITEMS = """
        Please give me the data items regarding a company's profile, answer with a list [].
        Please do so for the following prompt '{user_query}' and answer in json format with the following format:
        {{data_items: ['first search term', 'second search term']}}
    """

    DATA_ITEM_DESCRIPTION = """
        Explain what we are looking for when we say {data_item} regarding a company's profile;
        Provide a brief directive in a single sentence on what information should be collected.
    """

    DATA_ITEM_FORMAT = """
        When looking for {data_item}: {data_item_description} regarding a company's profile,
        would this piece of information normally be a:
        - Link (such as website)
        - Financial figure/Monetary Value (such as revenue)
        - Numerical Amount (such as FTE)
        - Binary answer (Yes or No answer)
        - Date Information (such as when company was founded)
        - Geographical Location (such as headquarter location)
        - Piece of text (such as additional information or someone's full name)
        In your answer just provide the data item found.
    """

    DATA_ITEM_INFO_LIST = """
         A user wants to know some information about a data item regarding a company.
         This data item is: {data_item}.
         Can you provide a list of two to three key informations required to understand this data item.
         You answer must contain a json file with the following keys: {{data_item, key_information}}

         For example:
         Data item: Headquarters
         Key information: city, country, address
         Data item: Funding
         Key information: value, currency, date
         Data item: Investors
         Key information: number of investors, investor stage, investor type
         Data item: Description
         Key information: description, objective, competitive advantage
         Data item: Contact
         Key information: name, position, linkedin profile
         Data item: Social
         Key information: linkedin link, twitter link, facebook link, X link
         Data item: Main employees
         Key information: name, position
    """

    DATA_SOURCE_PROMPT = """Here is the search term you should act on: {data_item_name},
        You are expected to find the right data sources from this list:
        {sources}
        Please answer in json in the following format:
        {{kept_data_sources: []}}
        where the contents of kept_data_sources list the keys of the data sources provided"""

    FIND_USER_DATA_ITEMS_PROMPT = """I am giving you data about a company: {data}.
        I want you to find the following piece of information: {data_item}.
        If no information was found in the given information please answer with 'None' and nothing more.
        If you found the information ONLY return the information as is, nothing more."""

    SEARCH_LLM_EXTRACTION_PROMPT = """Can you provide me the {data_item} of this company: {company_name}?
        The answer should be short and concise, it should only answer with the requested data:
        Don't form phrases, only give the number or a single word to answer the question
        If no data was found answer with None"""

    SYSTEM_ANALYST = "You are a professional analyst"

    SYSTEM_HELPFUL_BOT = "You are a helpful bot tasked with extracting information from a given text. If the requested information isn't available return 'None'"

    SYSTEM_NEEDED_PROCESS = "You are a necessary process in an internal search tool. You are expected to be able to determine the necessary data sources for a specific search term regarding a company search. You may also not find any data sources."

    SYSTEM_MARKET_RESEARCHER = "You are a professional market researcher"

class Constants(Enum):
    SOURCES = {
        "linkedin_search_results": "Contains information of a company in LinkedIn. So we can extract a description and very basic general information like the name and location.",
        "crunchbase_search_results": "Contains information of a company in Crunchbase, it's mainly useful for searching financial information on a company like investment rounds",
    }
