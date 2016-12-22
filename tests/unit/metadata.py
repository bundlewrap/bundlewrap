from bundlewrap.metadata import atomic, dictionary_key_map


def test_dictmap():
    assert set(dictionary_key_map({
        'key1': 1,
        'key2': {
            'key3': [3, 3, 3],
            'key4': atomic([4, 4, 4]),
            'key5': {
                'key6': "6",
            },
            'key7': set((7, 7, 7)),
        },
    })) == set([
        ("key1",),
        ("key2",),
        ("key2", "key3"),
        ("key2", "key4"),
        ("key2", "key5"),
        ("key2", "key5", "key6"),
        ("key2", "key7"),
    ])
