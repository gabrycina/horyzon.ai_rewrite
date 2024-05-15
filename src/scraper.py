import os
from apify_client import ApifyClient

class Scraper:
    company_name = ""
    industry = ""
    region = ""

    def __init__(self):
        self.apify_client = ApifyClient(os.getenv("APIFY_API_TOKEN"))

    def call(self, company_name, industry, region):
        options = {
                "queries": f"{company_name} {industry} in {region} site:www.linkedin.com/company/",
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


        res = self.apify_client.actor("nFJndFXA5zjCTuudP").call(run_input=options)

        if not res or res == []:
            # TODO: error handling
            print("Empty scraping results.")
            return

        return list(self.apify_client.dataset(res["defaultDatasetId"]).iterate_items())[0]
