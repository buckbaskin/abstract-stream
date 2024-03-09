import functools
import datetime
import time
import random
import requests
import feedparser
from collections import defaultdict
import json
import code

BASE_URL = "http://export.arxiv.org/api/query?"


def interact():
    code.InteractiveConsole(locals=globals()).interact()


class InteractionsCounter(object):
    def __init__(self):
        self.previous_func = "_init"

        self.usage = defaultdict(int)
        self.sequences = defaultdict(int)

        self._deserialize()

    def count(self, func_name):
        self.usage[func_name] += 1
        self.sequences[f"{func_name}:{self.previous_func}"] += 1

        self.previous_func = func_name

        self._serialize()

    def _serialize(self):
        string_version = json.dumps({"usage": self.usage, "sequences": self.sequences})
        with open("interactions.json", "w") as f:
            f.write(string_version)

    def _deserialize(self):
        try:
            with open("interactions.json", "r") as f:
                py_version = json.load(f)

            self.usage = defaultdict(int, py_version["usage"])
            self.sequences = defaultdict(int, py_version["sequences"])
        except FileNotFoundError:
            pass


_interactions = InteractionsCounter()


def track_usage(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        global interactions
        _interactions.count(func.__name__)

        return func(*args, **kwargs)

    return wrap


class PrintTrigger(object):
    def __init__(self, name, action):
        self.name = name
        self.action = action

    def __call__(self):
        return self.action()

    def __repr__(self):
        print(f"*{self.name}")
        return str(self.action())


class RenderRecord(object):
    def __init__(self, record):
        self.record = record

    def __repr__(self):
        def lines():
            yield ""
            yield self.record["title"]
            yield f"Scores: PRNG {self.record['prng_score']:.2f} TFIDF {self.record['tfidf_score']:.2f} Citation {self.record['citation_score']:.2f}"
            yield ""
            yield from self.record["abstract"].split("\n")
            yield ""


            actions = ['d = dislike'
            ,'s = skip'
            ,'i = interested'
            ,'r = read'
            ,'l = liked']
            yield ' | '.join(actions)

        return "\n".join(lines())


class UserInterface(object):
    def __init__(self):
        self.rated_items = []
        self.unrated_items = []
        self.skipped_items = []

        self.active_item = None

        self.mark_as_interested = PrintTrigger(
            "mark_as_interested", self._mark_as_interested
        )
        self.mark_as_read = PrintTrigger("mark_as_read", self._mark_as_read)
        self.mark_as_liked = PrintTrigger("mark_as_liked", self._mark_as_liked)
        self.mark_as_disliked = PrintTrigger("mark_as_disliked", self._mark_as_disliked)

        self.sort_key = lambda record: record["prng_score"]

    @track_usage
    def load(self):
        try:
            with open("abstract_stream.json", "r") as f:
                py_version = json.load(f)

            self.rated_items = py_version["rated_items"]
            self.unrated_items = py_version["unrated_items"]
            print(
                f"Loaded {len(self.rated_items)} ratings and {len(self.unrated_items)} unrated records"
            )
        except FileNotFoundError:
            pass

    @track_usage
    def store(self):
        start = datetime.datetime.now()
        string_version = json.dumps(
            {
                "rated_items": self.rated_items,
                "unrated_items": self.unrated_items + self.skipped_items,
            }
        )
        with open("abstract_stream.json", "w") as f:
            f.write(string_version)

        end = datetime.datetime.now()
        print('Stored records in %s' % ((end - start).total_seconds()))

    @track_usage
    def discover(self, *, store=True):
        """
        return something that renders
        """
        self.sort_key = lambda record: max(
            record["prng_score"], record["tfidf_score"], record["citation_score"]
        )

        return self._tick(store=store)

    @track_usage
    def explore(self, *, store=True):
        self.sort_key = lambda record: record["prng_score"]

        return self._tick(store=store)

    def _tick(self, store=True):
        if len(self.unrated_items) <= 2:
            self._refill()
            if store:
                self.store()

        self.unrated_items.sort(
            key=self.sort_key,
            reverse=True,
        )

        self.active_item, self.unrated_items = (
            self.unrated_items[0],
            self.unrated_items[1:],
        )

        return RenderRecord(self.active_item)

    def _refill(self):
        search_query = "robot"
        search_query = f"all:{search_query}"
        start = 0
        total_results = 20
        results_per_iteration = 20
        wait_time = 3

        viewed_set = set(
            [record["title"] for record in self.rated_items]
            + [record["title"] for record in self.unrated_items]
            + [record["title"] for record in self.skipped_items]
        )

        print("Searching arXiv for %s" % search_query)

        for i in range(start, total_results, results_per_iteration):

            print("Results %i - %i" % (i, i + results_per_iteration))

            query = "search_query=%s&start=%i&max_results=%i" % (
                search_query,
                i,
                results_per_iteration,
            )

            # perform a GET request using the BASE_URL and query
            response = requests.get(BASE_URL + query).text

            # parse the response using feedparser
            feed = feedparser.parse(response)

            # Run through each entry, and print out information
            for entry in feed.entries:
                arxiv_id = entry.id.split("/abs/")[-1]
                title = entry.title
                abstract = entry.summary
                if title not in viewed_set:
                    self.unrated_items.append(
                        {
                            "id": arxiv_id,
                            "title": title,
                            "abstract": abstract,
                            "prng_score": random.random(),
                            "tfidf_score": 0.0,
                            "citation_score": 0.0,
                        }
                    )
                else:
                    print("De-duplicating record. Title:", title)

            if len(feed.entries) < results_per_iteration:
                print("Early Termination")
                break

            # Remember to play nice and sleep a bit before you call
            # the API again!
            print("Sleeping for %i seconds" % wait_time)
            time.sleep(wait_time)

    @track_usage
    def skip(self):
        raise NotImplementedError("skip")

    @track_usage
    def download(self):
        DOWNLOAD_URL = "https://arxiv.org/pdf/%s.pdf"

        print("download")
        print(self.active_item)
        response = requests.get(DOWNLOAD_URL % self.active_item["id"])
        with open("%s.pdf" % self.active_item["id"], "wb") as f:
            f.write(response.content)

    def _mark_as_interested(self):
        self.active_item["rating"] = 1
        self.rated_items.append(self.active_item)
        self.store()

        return self._tick(store=False)

    def _mark_as_read(self):
        self.active_item["rating"] = 2
        self.rated_items.append(self.active_item)
        self.store()

        return self._tick(store=False)

    def _mark_as_liked(self):
        self.active_item["rating"] = 3
        self.rated_items.append(self.active_item)
        self.store()

        return self._tick(store=False)

    def _mark_as_disliked(self):
        self.active_item["rating"] = 3
        self.rated_items.append(self.active_item)
        self.store()

        return self._tick(store=False)


ui = UserInterface()
load = ui.load
store = ui.store
discover = ui.discover
explore = ui.explore

i = interested = ui.mark_as_interested
r = read = ui.mark_as_read
l = liked = ui.mark_as_liked
s = skip = ui.skip
d = dislike = ui.mark_as_disliked
download = ui.download

operations = [
    ("load", "load saved state"),
    ("store", "store algorithm state"),
    ("discover", "Surface likely interests based on previous data"),
    ("explore", "Surface random papers"),
    ("i = interested", "Mark as interested and go to the next paper"),
    ("r = read", "Mark that you read the paper and go to the next paper"),
    ("l = liked", "Mark that you read and liked the paper. Go to the next paper"),
    ("s = skip", "Skip the current paper without rating"),
    ("d = dislike", "Dislike the current paper. Recommend less like this"),
    ("download", "Download the current paper"),
]


for op, description in operations:
    print(op.ljust(20), description)


print(
    "Example Usage\n",
    """
        >>> load()
        >>> discover()
        ...
        Abstract Info
        ...
        >>> download()
        ...
        read the paper
        ...
        >>> l
        ...
        A new abstract
        ...
        """,
)


def test(*, store=False):
    load()

    print(explore(store=store))

    # magic values where printing them to the repl calls their action
    print(dislike)
    print(skip)
    print(interested)
    print(read)
    print(liked)

    print(discover(store=store))

    print(dislike)
    print(skip)
    print(interested)
    print(read)
    print(liked)

    download()

    if store:
        store()


if __name__ == "__main__":
    interact()
