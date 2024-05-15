from src.linkedin import search_linkedin

def manual_test():
    # Test data
    company = {
        "name": "Example Company",
        "linkedin_url": "https://www.linkedin.com/company/example-company"
    }

    # Call the function
    data = search_linkedin(company)

    # Print the results for manual inspection
    print(data)

if __name__ == "__main__":
    manual_test()

