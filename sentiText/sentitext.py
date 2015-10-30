import os
import logging
import string
import nltk
import pickle

from sentiwn import SentiWordNet
from nltk.corpus import wordnet as wn
from textblob import TextBlob
from scipy.interpolate import interp1d
from os import path

from senpy.plugins import SentimentPlugin, SenpyPlugin
from senpy.models import Response, Opinion, Entry


logger = logging.getLogger(__name__)

class SentiTextPlugin(SentimentPlugin):

    def __init__(self, info, *args, **kwargs):
        super(SentiTextPlugin, self).__init__(info, *args, **kwargs)
        self.id = info['module']
        base = path.abspath(path.dirname(__file__))
        self.swn_path = path.join(base, info['sentiword_path'])
        self.pos_path = path.join(base, info['pos_path'])
        self._swn = None
        self._pos_tagger = None

    def _load_swn(self):
        swn = SentiWordNet(self.swn_path)
        return swn

    def _load_pos_tagger(self):
        with open(self.pos_path, 'r') as f:
            tagger = pickle.load(f)
        return tagger

    def activate(self, *args, **kwargs):
        self._swn = self._load_swn()
        self._pos_tagger = self._load_pos_tagger()
        logger.info("SentiText plugin is ready to go!")

    def deactivate(self, *args, **kwargs):
        logger.info("SentiText plugin is being deactivated...")



    def _remove_punctuation(self, tokens):
        return [t for t in tokens if t not in string.punctuation]

    def _tokenize(self, text):
        data = {}
        sentences = nltk.sent_tokenize(text)
        for i, sentence in enumerate(sentences):
            sentence_ = {}
            words = nltk.word_tokenize(sentence)
            sentence_['sentence'] = sentence
            tokens_ = [w.lower() for w in words]
            sentence_['tokens'] = self._remove_punctuation(tokens_)
            data[i] = sentence_
        return data

    def _pos(self, tokens):
        for i in tokens:
            tokens[i]['tokens'] = self._pos_tagger.tag(tokens[i]['tokens'])
        return tokens

    # def _stopwords(sentences, lang='english'):
    #     for i in sentences:
    #         sentences[i]['tokens'] = [t for t in sentences[i]['tokens'] if t not in nltk.corpus.stopwords.words(lang)]
    #     return sentences

    def _compare_synsets(self, synsets, tokens, i):
        for synset in synsets:
            for word in tokens[i]['lemmas']:
                for lemma in tokens[i]['lemmas'][word]:
                    synset_ = lemma.synset() 
                    if synset == synset_:
                        return synset
        return None


    def analyse(self, **params):
        logger.debug("Analysing with params {}".format(params))

        text = params.get("input", None)
        tokens = self._tokenize(text)
        tokens = self._pos(tokens)
        
        
        for i in tokens:
            tokens[i]['lemmas'] = {}
            for w in tokens[i]['tokens']:
                lemmas = wn.lemmas(w[0], lang='spa')
                if len(lemmas) == 0:
                    continue
                tokens[i]['lemmas'][w[0]] = lemmas
        logger.debug("Tokens: {}".format(tokens))
        
        trans = TextBlob(unicode(text)).translate(from_lang='es',to='en')
        useful_synsets = {}
        for s_i, t_s in enumerate(trans.sentences):
            useful_synsets[s_i] = {}
            for w_i, t_w in enumerate(trans.sentences[s_i].words):
                synsets = wn.synsets(trans.sentences[s_i].words[w_i])
                if len(synsets) == 0:
                    continue
                eq_synset = self._compare_synsets(synsets, tokens, s_i)
                useful_synsets[s_i][t_w] = eq_synset
        logger.debug("Synsets used for analysis: {}".format(useful_synsets))

        scores = {}
        for i in tokens:
            scores[i] = {}
            for word in useful_synsets[i]:
                if useful_synsets[i][word] is None:
                    continue
                temp_scores = self._swn.get_score(useful_synsets[i][word].name().split('.')[0].replace(' ',' '))
                for score in temp_scores:
                    if score['synset'] == useful_synsets[i][word]:
                        t_score = score['pos'] - score['neg']
                        f_score = 'neu'
                        if t_score > 0:
                            f_score = 'pos'
                        elif t_score < 0:
                            f_score = 'neg'
                        score['score'] = f_score
                        scores[i][word] = score
                        break
        logger.debug("All scores (some not used): {}".format(scores))


        lang = params.get("language", "auto")
        p = params.get("prefix", None)
        response = Response(prefix=p)

        for i in scores:
            n_pos = 0.0
            n_neg = 0.0
            for w in scores[i]:
                if scores[i][w]['score'] == 'pos':
                    n_pos += 1.0
                elif scores[i][w]['score'] == 'neg':
                    n_neg += 1.0

            inter = interp1d([-1.0, 1.0], [0.0, 1.0])
            try:
                g_score = (n_pos - n_neg) / (n_pos + n_neg)
                g_score = float(inter(g_score))
            except:
                if n_pos == 0 and n_neg == 0:
                    g_score = 0.5

            polarity = 'marl:Neutral'
            if g_score > 0.5:
                polarity = 'marl:Positive'
            elif g_score < 0.5:
                polarity = 'marl:Negative'

            entry = Entry(id="Entry"+str(i),
                      text=tokens[i]['sentence'],
                      prefix=p)
            polarity
            opinion = Opinion(id="Opinion0"+'_'+str(i),
                          prefix=p,
                          hasPolarity=polarity,
                          polarityValue=float("{0:.2f}".format(g_score)))


            opinion["prov:wasGeneratedBy"] = self.id
            entry.opinions.append(opinion)
            entry.language = lang
            response.entries.append(entry)
        return response
