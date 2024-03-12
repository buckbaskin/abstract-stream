import functools
from os import mkdir
import os
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

            actions = [
                "d = dislike",
                "s = skip",
                "i = interested",
                "r = read",
                "l = liked",
            ]
            yield " | ".join(actions)

        return "\n".join(lines())


class ArxivCategoryProvider(object):
    MAX_RESULTS = 500
    WAIT_TIME = 3
    RESULT_PER_ITERATION = 50

    def __init__(self, category):
        self.start_index = 0
        self.search_query = f"cat:{category}"

    def records(self):
        for i in range(
            self.start_index,
            self.start_index // 2 + self.MAX_RESULTS,
            self.RESULT_PER_ITERATION,
        ):

            query = "search_query=%s&start=%i&max_results=%i" % (
                self.search_query,
                i,
                self.RESULT_PER_ITERATION,
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
                yield {
                    "id": arxiv_id,
                    "title": title,
                    "abstract": abstract,
                    "prng_score": random.random(),
                    "tfidf_score": 0.0,
                    "citation_score": 0.0,
                }

            if len(feed.entries) < self.RESULT_PER_ITERATION:
                print(
                    "Early Termination - ArxivCategoryProvider - %s"
                    % (self.search_query)
                )
                break

            # Remember to play nice and sleep a bit before you call
            # the API again!
            print(
                "Sleeping for %i seconds - ArxivCategoryProvider - %s"
                % (self.WAIT_TIME, self.search_query)
            )
            time.sleep(self.WAIT_TIME)


def round_robin(iterators):
    while True:
        nexts = []
        for iterator in iterators:
            try:
                nexts.append(next(iterator))
            except TypeError as te:
                print(te)
                raise

        if len(nexts) == 0:
            break

        yield from nexts


class UserInterface(object):
    def __init__(self, providers):
        self.providers = [p.records() for p in providers]

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

        # query memoizing
        self.start_index = 0

    @track_usage
    def load(self):
        try:
            with open("abstract_stream.json", "r") as f:
                py_version = json.load(f)

            self.active_item = None
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
                "unrated_items": [self.active_item]
                + self.unrated_items
                + self.skipped_items,
            }
        )
        with open("abstract_stream.json", "w") as f:
            f.write(string_version)

        end = datetime.datetime.now()
        print("Stored records in %.2f sec" % ((end - start).total_seconds()))

    @track_usage
    def discover(self, *, store=True):
        """
        return something that renders
        """
        self.sort_key = lambda record: max(
            record["prng_score"], record["tfidf_score"], record["citation_score"]
        )

        if self.active_item is not None:
            self.unrated_items.append(self.active_item)

        return self._tick(store=store)

    @track_usage
    def explore(self, *, store=True):
        self.sort_key = lambda record: record["prng_score"]

        if self.active_item is not None:
            self.unrated_items.append(self.active_item)

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
        # TODO: browse all of cs.RO, cs.SE
        # TODO: actually score by tfidf
        # TODO: convert this search query into its own action
        viewed_set = set(
            [record["id"] for record in self.rated_items]
            + [record["id"] for record in self.unrated_items]
            + [record["id"] for record in self.skipped_items]
            + [self.active_item["id"]]
        )

        for record in round_robin(self.providers):
            assert isinstance(record, dict)

            arxiv_id = record["id"]
            if arxiv_id not in viewed_set:
                self.unrated_items.append(record)
            else:
                print("De-duplicating record. Title:", record["title"])

            if len(self.unrated_items) > 50:
                print("Early refill pause")
                break

    @track_usage
    def skip(self):
        raise NotImplementedError("skip")

    @track_usage
    def download(self):
        DOWNLOAD_URL = "https://arxiv.org/pdf/%s.pdf"

        print("download")
        print(self.active_item)
        response = requests.get(DOWNLOAD_URL % self.active_item["id"])

        try:
            mkdir("pdf")
        except FileExistsError:
            pass

        write_out_id = self.active_item["id"]
        write_out_id = write_out_id.replace("/", "__")

        with open(os.path.join("pdf", write_out_id), "wb") as f:
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


ui = UserInterface([ArxivCategoryProvider("CS.RO")])
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
