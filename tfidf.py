"""
Example Rated Item

{
    "id": "cs/0412050v1",
    "title": "Gyroscopically Stabilized Robot: Balance and Tracking",
    "abstract": "The single wheel, gyroscopically stabilized robot - Gyrover, is a dynamically\nstable but statically unstable, underactuated system. In this paper, based on\nthe dynamic model of the robot, we investigate two classes of nonholonomic\nconstraints associated with the system. Then, based on the backstepping\ntechnology, we propose a control law for balance control of Gyrover. Next,\nthrough transferring the systems states from Cartesian coordinate to polar\ncoordinate, control laws for point-to-point control and line tracking in\nCartesian space are provided.",
    "prng_score": 0.9857003508946388,
    "tfidf_score": 0.0,
    "citation_score": 0.0,
    "rating": 1,
}
"""

# TFIDF Example: https://scikit-learn.org/stable/auto_examples/text/plot_document_classification_20newsgroups.html

import numpy as np

from time import time
from collections import namedtuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge

Dataset = namedtuple(
    "Dataset", ["data", "target", "filenames", "DESCR", "target_names"]
)


def _items_to_dataset(items, *, resample=False):
    positive_data = []  # list of strings
    positive_target = []  # list of float scores to predict
    negative_data = []
    negative_target = []

    target_names = []  # list of target classes

    for i in items:
        # ((-1) + 1) / 4 -> 0.00 # dislike
        # (( 0) + 1) / 4 -> 0.25
        # ((+1) + 1) / 4 -> 0.50 # interested
        # ((+2) + 1) / 4 -> 0.75 # read
        # ((+3) + 1) / 4 -> 1.00 # liked
        text = i["title"] + "   " + i["abstract"]

        if "rating" in i:
            rating = i["rating"]
            if rating <= 0:
                negative_data.append(text)
                negative_target.append((rating + 1.0) / 4.0)
            else:
                positive_data.append(text)
                positive_target.append((rating + 1.0) / 4.0)
        else:
            if resample:
                raise ValueError("Can't resample without ratings")
            negative_data.append(text)
            negative_target.append("no score")

    if resample:
        reselect_idx = np.random.randint(
            0, len(positive_data), size=(len(negative_data),)
        )

        pre_size = len(positive_data)

        positive_data = np.array(positive_data)[reselect_idx]
        positive_target = np.array(positive_target)[reselect_idx]

        post_size = len(positive_data)
        print(
            "Resampled from %d to %d"
            % (
                pre_size,
                post_size,
            )
        )

    data = np.concatenate((negative_data, positive_data))
    target = np.concatenate((negative_target, positive_target))

    return Dataset(
        data=np.array(data),
        target=np.array(target),
        filenames=[],
        DESCR="auto",
        target_names=target_names,
    )


def _load_dataset(rated_items, unrated_items, *, verbose=False, max_df=0.5, min_df=5):
    data_train = _items_to_dataset(rated_items, resample=True)
    data_test = _items_to_dataset(unrated_items)
    """
    data_train should match:

    bunch : :class:`~sklearn.utils.Bunch`
        Dictionary-like object, with the following attributes.

        data : list of shape (n_samples,)
            The data list to learn.
        target: ndarray of shape (n_samples,)
            The target labels.
        filenames: list of shape (n_samples,)
            The path to the location of the data.
        DESCR: str
            The full description of the dataset.
        target_names: list of shape (n_classes,)
            The names of target classes.
            """

    target_names = data_train.target_names
    y_train = data_train.target

    t0 = time()
    vectorizer = TfidfVectorizer(
        sublinear_tf=True, max_df=max_df, min_df=min_df, stop_words="english"
    )
    X_train = vectorizer.fit_transform(data_train.data)
    duration_train = time() - t0

    t0 = time()
    X_test = vectorizer.transform(data_test.data)
    duration_test = time() - t0

    feature_names = vectorizer.get_feature_names_out()

    if verbose:
        print(f"{len(data_train.data)} documents - (training set)")
        print(f"{len(data_test.data)} documents - (test set)")
        print(f"{len(target_names)} categories")
        print(f"vectorize training done in {duration_train:.3f}s ")
        print(f"n_samples: {X_train.shape[0]}, n_features: {X_train.shape[1]}")
        print(f"vectorize testing done in {duration_test:.3f}s ")
        print(f"n_samples: {X_test.shape[0]}, n_features: {X_test.shape[1]}")

    return X_train, y_train, X_test, feature_names, target_names


def tfidf_score(rated_items, unrated_items, *, verbose=False, test=False):
    """
    Given a list of rated items (title, abstract, rating), predict the rating
    on a 0 to 1 scale, assign to tfidf_score and return the unrated items with
    updated tfidf_score
    """
    if not test:
        X_train, y_train, X_test, feature_names, target_names = _load_dataset(
            rated_items=rated_items,
            unrated_items=unrated_items,
            verbose=verbose,
        )
    else:
        X_train, y_train, X_test, feature_names, target_names = _load_dataset(
            rated_items=rated_items,
            unrated_items=unrated_items,
            verbose=verbose,
            max_df=0.99,
            min_df=0.01,
        )

    clf = Ridge(tol=1e-2, solver="sparse_cg")
    print("y_train", y_train, y_train.shape)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    print("y_pred", y_pred.shape)
    print("unrated_items", len(unrated_items))

    for item, score in zip(unrated_items, y_pred):
        item["tfidf_score"] = score
        yield item


def _test_ratings():
    return [
        {
            "id": "1",
            "title": "A",
            "abstract": "The single wheel, gyroscopically stabilized robot - Gyrover, is a dynamically\nstable but statically unstable, underactuated system. In this paper, based on\nthe dynamic model of the robot, we investigate two classes of nonholonomic\nconstraints associated with the system. Then, based on the backstepping\ntechnology, we propose a control law for balance control of Gyrover. Next,\nthrough transferring the systems states from Cartesian coordinate to polar\ncoordinate, control laws for point-to-point control and line tracking in\nCartesian space are provided.",
            "prng_score": 0.9857003508946388,
            "tfidf_score": 0.0,
            "citation_score": 0.0,
            "rating": 1,
        },
        {
            "id": "2",
            "title": "B",
            "abstract": "The single wheel, gyroscopically stabilized robot - Gyrover, is a dynamically\nstable but statically unstable, underactuated system. In this paper, based on\nthe dynamic model of the robot, we investigate two classes of nonholonomic\nconstraints associated with the system. Then, based on the backstepping\ntechnology, we propose a control law for balance control of Gyrover. Next,\nthrough transferring the systems states from Cartesian coordinate to polar\ncoordinate, control laws for point-to-point control and line tracking in\nCartesian space are provided.",
            "prng_score": 0.9857003508946388,
            "tfidf_score": 0.0,
            "citation_score": 0.0,
            "rating": 2,
        },
        {
            "id": "3",
            "title": "B",
            "abstract": "lobsters pinwheels kafka kubernetes",
            "prng_score": 0.9857003508946388,
            "tfidf_score": 0.0,
            "citation_score": 0.0,
            "rating": -1,
        },
    ]


def _test_unratings():
    return [
        {"id": "Y", "title": "", "abstract": "lobsters"},
        {"id": "Z", "title": "", "abstract": "gyroscopically"},
    ]


def _test():
    rerated = list(
        tfidf_score(_test_ratings(), _test_unratings(), verbose=True, test=True)
    )

    print([(r["id"], r["tfidf_score"]) for r in rerated])

    assert rerated[0]["tfidf_score"] < rerated[1]["tfidf_score"]


if __name__ == "__main__":
    _test()
    print("Done")
