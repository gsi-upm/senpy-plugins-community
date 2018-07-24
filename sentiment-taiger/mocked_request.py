import os 


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[1]['inputText'] == "I hate to say this":
        return MockResponse({
                              "inputText": "I hate to say this",
                              "normalizedText": "I hate to say this",
                              "positivityScore": -1.8951251587831475,
                              "positivityCategory": "neg"
                            }, 200)
    elif args[1]['inputText'] == "This is amazing":
        return MockResponse({
                              "inputText": "This is amazing ",
                              "normalizedText": "This is amazing",
                              "positivityScore": -1.4646806570973374,
                              "positivityCategory": "pos"
                            }, 200)
    elif args[1]['inputText'] == "The pillow is in the wardrobe":
        return MockResponse({
                              "inputText": "The pillow is in the wardrobe",
                              "normalizedText": "The pillow is in the wardrobe",
                              "positivityScore": -2.723999097522657,
                              "positivityCategory": "neu"
                            }, 200)

    return MockResponse(None, 404)
