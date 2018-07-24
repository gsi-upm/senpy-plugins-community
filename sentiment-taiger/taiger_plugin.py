# -*- coding: utf-8 -*-

import time
import requests
import json
import string
import os
from os import path
import time
from senpy.plugins import SentimentPlugin
from senpy.models import Results, Entry, Entity, Topic, Sentiment, Error
from senpy.utils import check_template

from mocked_request import mocked_requests_get

try:
    from unittest import mock
except ImportError:
    import mock

TAIGER_ENDPOINT = os.environ.get("TAIGER_ENDPOINT")


class TaigerPlugin(SentimentPlugin):
    '''
    Service that analyzes sentiments from social posts written in Spanish or English.

    Example request:

    http://senpy.cluster.gsi.dit.upm.es/api/?algo=sentiment-taiger&inputText=This%20is%20amazing
    '''
    name = 'sentiment-taiger'
    author = 'GSI UPM'
    version = "0.1"
    maxPolarityValue = -1
    minPolarityValue = -10

    extra_params = {
        "endpoint": {
            "aliases": ["endpoint"],
            "required": False
        }
    }
    def _polarity(self, value):

        if 'neu' in value:
            polarity = 'marl:Neutral'
        elif 'neg' in value:
            polarity = 'marl:Negative'
        elif 'pos' in value:
            polarity = 'marl:Positive'
        return polarity

    def analyse_entry(self, entry, params):

        txt = entry['nif:isString']
        if params.get("endpoint"):
            api = params.get("endpoint")
        else:
            api = TAIGER_ENDPOINT
        parameters = {
            'inputText': txt
        }
        try:
            r = requests.get(
                api, params=parameters, timeout=3)
        except requests.exceptions.Timeout:
            raise Error("API does not response")

        api_response = r.json()
        if not api_response.get('positivityCategory'):
            raise Error(r.json())
        self.log.debug(api_response)
        agg_polarity, agg_polarityValue = self._polarity(
            api_response.get('positivityCategory', None))
        normalized_text = api_response.get('normalizedText', None)
        agg_opinion = Sentiment(
            id="Opinion0",
            marl__hasPolarity=agg_polarity,
            marl__polarityValue=api_response['positivityScore']
            )
        agg_opinion["normalizedText"] = api_response['normalizedText']
        agg_opinion.prov(self)
        entry.sentiments.append(agg_opinion)

        yield entry

    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test(self, *args, **kwargs):
        params = {'algo': 'sentiment-taiger',
                  'intype': 'direct',
                  'expanded-jsonld': 0,
                  'informat': 'text',
                  'prefix': '',
                  'plugin_type': 'analysisPlugin',
                  'urischeme': 'RFC5147String',
                  'outformat': 'json-ld',
                  'i': 'I hate to say this',
                  'input': 'I hate to say this',
                  'conversion': 'full',
                  'language': 'en',
                  'apikey': '00000',
                  'algorithm': 'sentiment-taiger'}
        res_neg = next(self.analyse_entry(Entry(nif__isString="I hate to say this"), params))
        res_pos = next(self.analyse_entry(Entry(nif__isString="This is amazing"), params))
        res_neu = next(self.analyse_entry(Entry(nif__isString="The pillow is in the wardrobe"), params))

        check_template(res_neg,
                       {'sentiments': [
                           {'marl:hasPolarity': 'marl:Negative'}] 
                       })
        check_template(res_pos,
                       {'sentiments': [
                           {'marl:hasPolarity': 'marl:Positive'}] 
                       })
        check_template(res_neu,
                       {'sentiments': [
                           {'marl:hasPolarity': 'marl:Neutral'}] 
                       })


if __name__ == '__main__':
    from senpy import easy_test
    easy_test()
