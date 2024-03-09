import functools
from collections import defaultdict
import json
import code


def interact():
    code.InteractiveConsole(locals=globals()).interact()


print("Hello World")


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


class RenderExplorer(object):
    def __init__(self, name):
        self.name = name

    def __call__(self):
        print("RenderExplorer.__call__")
        return f"RenderExplorer({self.name})"

    def __repr__(self):
        print("RenderExplorer.__repr__")
        return f"RenderExplorer({self.name})"

    def __str__(self):
        print("RenderExplorer.__str__")
        return f"RenderExplorer({self.name})"


class RenderRecord(object):
    def __init__(self, record):
        self.record = record

    def __repr__(self):
        print("RenderExplorer.__repr__")
        return f"RenderExplorer({self.record})"

    def __str__(self):
        print("RenderExplorer.__str__")

        def lines():
            yield self.record.title
            yield f"Scores: PRNG {self.record['prng_score']} TFIDF {self.record['tfidf_score']} Citation {self.record['citation_score']}"
            yield ""
            yield from self.record.abstract.split("\n")

        return "\n".join(lines)


class UserInterface(object):
    def __init__(self):
        self.rated_items = []
        self.unrated_items = []
        self.skipped_items = []

        self.active_item = None

        self.mark_as_interested = RenderExplorer("mark_as_interested")
        self.mark_as_read = RenderExplorer("mark_as_read")
        self.mark_as_liked = RenderExplorer("mark_as_liked")
        self.mark_as_disliked = RenderExplorer("mark_as_disliked")

    @track_usage
    def load(self):
        try:
            with open("abstract_stream.json", "r") as f:
                py_version = json.load(f)

            self.rated_items = py_version.rated_items
            self.unrated_items = py_version.unrated_items
        except FileNotFoundError:
            pass

    @track_usage
    def store(self):
        # Don't forget to store skipped items as unrated
        raise NotImplementedError("store")

    @track_usage
    def discover(self):
        """
        return something that renders
        """
        raise NotImplementedError("discover")

    @track_usage
    def explore(self):
        if len(self.unrated_items) <= 2:
            self._refill()

        self.unrated_items.sort(
            key=lambda record: max(
                record["prng_score"], record["tfidf_score"], record["citation_score"]
            )
        )

        self.active_item, self.unrated_items = (
            self.unrated_items[0],
            self.unrated_items[1:],
        )

        return RenderRecord(self.active_item)

    def _refill(self):
        raise NotImplementedError("download a batch of arXiv records")

    @track_usage
    def skip(self):
        raise NotImplementedError("skip")

    @track_usage
    def download(self):
        raise NotImplementedError("download")


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


def test(*, store=False):
    load()

    print(explore())

    # magic values where printing them to the repl calls their action
    print(dislike)
    print(skip)
    print(interested)
    print(read)
    print(liked)

    print(discover())

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
