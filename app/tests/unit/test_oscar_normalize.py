from app.crawlers.oscar import normalize_oscar_payload


def test_normalize_accepts_dict_with_data_key():
    payload = {
        "data": [
            {"title": "Birdman", "nominations": "9", "awards": "4", "best_picture": True},
            {"title": "Whiplash", "nominations": 5, "awards": 3, "best_picture": False},
        ]
    }

    rows = normalize_oscar_payload(payload, 2014)

    assert len(rows) == 2
    assert rows[0]["year"] == 2014
    assert rows[0]["title"] == "Birdman"
    assert rows[0]["nominations"] == 9
    assert rows[0]["awards"] == 4
    assert rows[0]["best_picture"] is True


def test_normalize_accepts_list_payload_directly():
    payload = [
        {"title": "The King's Speech", "nominations": 12, "awards": 4, "best_picture": True},
        {"title": "Inception", "nominations": "8", "awards": "4", "best_picture": False},
    ]

    rows = normalize_oscar_payload(payload, 2010)

    assert len(rows) == 2
    assert rows[0]["year"] == 2010
    assert rows[1]["title"] == "Inception"
    assert rows[1]["nominations"] == 8


def test_normalize_converts_bool_strings():
    payload = {
        "data": [
            {"title": "Movie A", "nominations": "1", "awards": "0", "best_picture": "true"},
            {"title": "Movie B", "nominations": None, "awards": None, "best_picture": "no"},
        ]
    }

    rows = normalize_oscar_payload(payload, 2015)

    assert rows[0]["best_picture"] is True
    assert rows[1]["best_picture"] is False
    assert rows[1]["nominations"] == 0
    assert rows[1]["awards"] == 0


def test_normalize_skips_invalid_items():
    payload = {"data": [{"title": ""}, "x", {"nominations": 1}]}
    rows = normalize_oscar_payload(payload, 2012)
    assert rows == []