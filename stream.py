"""
Based on python_arXiv_paging_example.py
Author: Julius B. Lucks
https://info.arxiv.org/help/api/examples/python_arXiv_paging_example.txt
"""

import requests
import time
import feedparser

# Base api query url
base_url = "http://export.arxiv.org/api/query?"


def stream_abstracts(search_query):
    # Search parameters
    search_query = f"all:{search_query}"
    start = 0
    total_results = 20
    results_per_iteration = 5
    wait_time = 3

    print("Searching arXiv for %s" % search_query)

    for i in range(start, total_results, results_per_iteration):

        print("Results %i - %i" % (i, i + results_per_iteration))

        query = "search_query=%s&start=%i&max_results=%i" % (
            search_query,
            i,
            results_per_iteration,
        )

        # perform a GET request using the base_url and query
        response = requests.get(base_url + query).text

        # parse the response using feedparser
        feed = feedparser.parse(response)

        # Run through each entry, and print out information
        for entry in feed.entries:
            print("arxiv-id: %s" % entry.id.split("/abs/")[-1])
            print("Title:  %s" % entry.title)
            # feedparser v4.1 only grabs the first author
            print("First Author:  %s" % entry.author)

        # Remember to play nice and sleep a bit before you call
        # the api again!
        print("Sleeping for %i seconds" % wait_time)
        time.sleep(wait_time)


stream_abstracts("biophysics")
