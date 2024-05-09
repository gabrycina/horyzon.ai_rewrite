from enum import Enum, auto


class Actions(Enum):
    SEARCH_COMPANIES = auto(),
    SEARCH_USER_DATA_ITEMS = auto(),
    LAUNCH_SEARCH_APIS = auto(),
    EXTRACT_INFO = auto()


class PromptText(Enum):
    USER_DATA_ITEMS = (
        "Please give me the data items regarding a company's profile, answer with a list []."
        " Please do so for the following prompt '{user_query}' and answer in json format with the following format:"
        " {{data_items: ['first search term', 'second search term']}}"
    ),
    DATA_ITEM_DESCRIPTION = (
        "Explain what we are looking for when we say {data_item} regarding a company's profile;"
        " Provide a brief directive in a single sentence on what information should be collected."
    ),
    DATA_ITEM_FORMAT = (
        "When looking for {data_item}: {data_item_description} regarding a company's profile,"
        " would this piece of information normally be a:"
        " - Link (such as website)"
        " - Financial figure/Monetary Value (such as revenue)"
        " - Numerical Amount (such as FTE)"
        " - Binary answer (Yes or No answer)"
        " - Date Information (such as when company was founded)"
        " - Geographical Location (such as headquarter location)"
        " - Piece of text (such as additional information or someone's full name)"
        " In your answer just provide the data item found."
    ),
    DATA_ITEM_INFO_LIST = (
        "A user wants to know some information about a data item regarding a company."
        " This data item is: {data_item}."
        " Can you provide a list of two to three key informations required to understand this data item."
        " You answer must contain a json file with the following keys: {{data_item, key_information}}"
        " For example:"
        " Data item: Headquarters"
        " Key information: city, country, address"
        " Data item: Funding"
        " Key information: value, currency, date"
        " Data item: Investors"
        " Key information: number of investors, investor stage, investor type"
        " Data item: Description"
        " Key information: description, objective, competitive advantage"
        " Data item: Contact"
        " Key information: name, position, linkedin profile"
        " Data item: Social"
        " Key information: linkedin link, twitter link, facebook link, X link"
        " Data item: Main employees"
        " Key information: name, position"
    ),
    SYSTEM_ANALYST = "You are a professional analyst",
    SYSTEM_HELPFUL_BOT = "You are a helpful bot tasked with extracting information from a given text. If the requested information isn't available return 'None'",
    SYSTEM_NEEDED_PROCESS = "You are a necessary process in an internal search tool. You are expected to be able to determine the necessary data sources for a specific search term regarding a company search. You may also not find any data sources.",
    SYSTEM_MARKET_RESEARCHER = "You are a professional market researcher",