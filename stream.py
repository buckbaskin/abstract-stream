"""
Based on python_arXiv_paging_example.py
Author: Julius B. Lucks
https://info.arxiv.org/help/api/examples/python_arXiv_paging_example.txt
"""

import requests
import time
import feedparser

# Base API query url
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
            arxiv_id=entry.id.split("/abs/")[-1]
            title = entry.title
            abstract = entry.summary
            yield {'id': arxiv_id, 'title': title, 'abstract': abstract}

        if len(feed.entries) < results_per_iteration:
            print('Early Termination')
            break

        # Remember to play nice and sleep a bit before you call
        # the API again!
        print("Sleeping for %i seconds" % wait_time)
        time.sleep(wait_time)

def ui_loop(search_query):
    INTERACTIONS = {'y': 1, 'n': -1, '1': 2, '!': 2}

    for idx, metadata in enumerate(stream_abstracts(search_query)):
        print(idx)
        print(' Title    : ' + metadata['title'])
        print('\n Abstract : ' + metadata['abstract'])

        print('y/n/! yes+1 / no-1 / excited+2, others skipped')
        result = input().lower()
        if result in INTERACTIONS:
            rating = INTERACTIONS[result]
            print(f'Rating: {rating}')
        else:
            rating = 0

        metadata['rating'] = rating
        yield metadata

for meta in list(ui_loop('state estimation')):
    print(metadata['rating'], metadata['title'])

# Future Expansion (in only a vague order):
#   - pipe through configuration from the outer caller so that the number of
#   results, batch size, etc can be configured
#   - TFIDF + regression of an expected rating
#   - Incremental learning, so that the estimator may be stream-updated as new
#   ratings are given
#   https://scikit-learn.org/0.15/modules/scaling_strategies.html
#   - A database for saving ratings so that ratings may accumulate over time
#   (this will be deferred to ensure that the database schema can be written
#   essentially once)
#   - async await generators, so that the fetching may be done in the
#   background https://peps.python.org/pep-0525/. Ideally, the batch update for
#   ML updates can be run async, the batch download can run seamlessly by
#   downloading sufficient to outpace rating and the user gets a smooth
#   experience
#   - provide links to download PDFs via arxiv.org
#   - suggest searches based on words that rate highly
