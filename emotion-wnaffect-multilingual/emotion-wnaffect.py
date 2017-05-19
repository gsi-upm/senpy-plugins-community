# -*- coding: utf-8 -*-

from __future__ import division
import re
import nltk
import logging
import os
import string
import xml.etree.ElementTree as ET
from nltk.corpus import stopwords
from nltk.corpus import WordNetCorpusReader
from nltk.corpus import wordnet as wn
from emotion import Emotion as Emo

from senpy.plugins import EmotionPlugin, SenpyPlugin, ShelfMixin
from senpy.models import Results, EmotionSet, Entry, Emotion

logger = logging.getLogger(__name__)

class EmotionTextPlugin(EmotionPlugin, ShelfMixin):

    def _convert_wn_16_30(self, wn16id):
        pos_char,wn16_offset = wn16id.split("#")
        try:
            return "{0}-{1}".format(self._wn16_30[pos_char][int(wn16_offset)], pos_char)
        except KeyError:
            # There is a wn16 id that cannot be converted. Currently only a#00196250
            return None

    def _load_synsets(self, synsets_path):
        """Returns a dictionary synset offset -> emotion (int -> str)."""
        tree = ET.parse(synsets_path)
        root = tree.getroot()

        synsets = {}
        pending = []
        for pos in ["noun", "adj", "verb", "adv"]:
            for elem in root.findall(".//{0}-syn-list//{0}-syn".format(pos)):
                idd = elem.get("id")
                wn30_id = self._convert_wn_16_30(idd)
                if wn30_id is None: 
                    continue
                if elem.get("categ"):
                    synsets[wn30_id] = Emo.emotions[elem.get("categ")] if elem.get("categ") in Emo.emotions else None
                elif elem.get("noun-id"):
                    try:
                        synsets[wn30_id] = synsets[self._convert_wn_16_30(elem.get("noun-id"))]
                    except KeyError:
                        newid = self._convert_wn_16_30(elem.get("noun-id"))
                        if newid is not None:
                            pending.append((wn30_id, newid))
        for (wn30_id, noun_id) in pending:
            try:
                synsets[wn30_id] = synsets[noun_id]
            except KeyError:
                logger.warning("trouble with id",wn30_id, noun_id)
                raise
        return synsets

    def _load_emotions(self, hierarchy_path):
        """Loads the hierarchy of emotions from the WordNet-Affect xml."""

        tree = ET.parse(hierarchy_path)
        root = tree.getroot()
        for elem in root.findall("categ"):
            name = elem.get("name")
            if name == "root":
                Emo.emotions["root"] = Emo("root")
            else:
                Emo.emotions[name] = Emo(name, elem.get("isa"))

    def _load_wn_16_30_mapping(self, mapping_wn16_30_path):
        wn16_30 = {}
        pos_mapping_suffixes = {"a":"adj", "r":"adv", "n":"noun", "v":"verb"}
        for pos,suffix in pos_mapping_suffixes.items():
            mapping = {}
            path = mapping_wn16_30_path + suffix
            with open(path) as f:
                for l in f:
                    l = l.split()
                    # get mapping with greatest probability
                    target, prob = 0, 0
                    for t,p in zip(l[1::2],l[2::2]):
                        p = float(p.strip())
                        if p>prob:
                            target,prob = t,p
                    mapping[int(l[0])] = int(target)
            wn16_30[pos] = mapping
        return wn16_30

    def _get_stopwords(self, lang):
        # omw and polywn language codes that match nltk stopword file names
        langmap = {
            "dan":"danish","eng":"english","fin":"finnish","fra":"french",
            "ita":"italian","nob":"norwegian","spa":"spanish",
            "swe":"swedish",
            "da":"danish","nl":"dutch","fi":"finnish","fr":"french","de":"german","hu":"hungarian",
            "it":"italian","pt":"portuguese","es":"spanish"
        }
        sw = self._stopwords.get(lang, None)
        if sw is None:
            if lang not in langmap:
                sw = set()
                self._stopwords[lang] = sw
            else:
                sw = stopwords.words(langmap[lang])
                self._stopwords[lang] = sw
        return sw


    def activate(self, *args, **kwargs):
        print(dir(self))
        nltk.download('stopwords')
        
        if 'stopwords' not in self.sh:
            self.sh['stopwords'] = {}
        self._stopwords = self.sh['stopwords']

        self._categoryLevels = [5,6,7]
        self._categories = {'anger': [set(), set(['hate']), set(['anger'])],
                            'fear': [set(['negative-fear','ambiguous-fear']), set(), set()],
                            'disgust': [set(), set(['self-disgust']), set(['antipathy', 'contempt', 'disgust', 'alienation'])],
                            'joy': [set(['gratitude','levity','affection','enthusiasm','love','joy','liking']), set(), set()],
                            'sadness': [set(['ingrattitude','daze','humility','compassion','despair','anxiety','sadness']), set(), set()],
                            'surprise' : [set(['surprise']), set(), set()]}

        if 'wnaffect-emotions' in self.sh:
            Emo.emotions = self.sh['wnaffect-emotions']
        else:
            self._load_emotions(self.hierarchy_path)
            self.sh['wnaffect-emotions'] = Emo.emotions

        if 'wn16_30' not in self.sh:
            self.sh['wn16_30'] = self._load_wn_16_30_mapping(self.mapping_wn16_30_path)
        self._wn16_30 = self.sh['wn16_30']
                
        if 'total_synsets' not in self.sh:
            self.sh['total_synsets'] = self._load_synsets(self.synsets_path)
        self._total_synsets = self.sh['total_synsets']
        self._total_synsets_offsets = set(self._total_synsets.keys())
        
    def deactivate(self, *args, **kwargs):
        self.save()

    def _my_preprocessor(self, text):

        regHttp = re.compile('(http://)[a-zA-Z0-9]*.[a-zA-Z0-9/]*(.[a-zA-Z0-9]*)?')
        regHttps = re.compile('(https://)[a-zA-Z0-9]*.[a-zA-Z0-9/]*(.[a-zA-Z0-9]*)?')
        regAt = re.compile('@([a-zA-Z0-9]*[*_/&%#@$]*)*[a-zA-Z0-9]*')
        text = re.sub(regHttp, '', text)
        text = re.sub(regAt, '', text)
        text = re.sub('RT : ', '', text)
        text = re.sub(regHttps, '', text)
        text = re.sub('[0-9]', '', text)
        text = self._delete_punctuation(text)
        return text

    def _delete_punctuation(self, text):

        exclude = set(string.punctuation)
        s = ''.join(ch for ch in text if ch not in exclude)
        return s

    def _find_ngrams(self, input_list, n):
        return zip(*[input_list[i:] for i in range(n)])

    def _extract_features(self, text, language):

        def wn3id(syn):
            return "%d-%s"%(syn.offset(), syn.pos())

        feature_set={k:0 for k in self._categories}
        ngrams_words = [w.lower() for w in text.split() if w.lower() not in self._get_stopwords(language)]

        matches=0
        for i in range(len(ngrams_words)):
            synsets = set(wn3id(syn) for syn in wn.synsets(ngrams_words[i], lang=language))
            logger.info("synsets for %s in %s : %s"%(ngrams_words[i], language, len(synsets)))
            for syn_id in synsets & self._total_synsets_offsets:
                logger.info("%s %8s %20s"%(syn_id, type(syn_id)))
                logger.info("synset offset %s in wnaffect! %20s"%(syn_id, ngrams_words[i])) 
                if self._total_synsets[syn_id] is None:
                    continue
                else:
                    synsetEmo = self._total_synsets[syn_id]
                    emotion = [synsetEmo.get_level(j).name for j in self._categoryLevels]
                    matches+=1
                    for emoemo,emoEmotions in self._categories.items():
                        if any( emo in emoEmotions[j] for j,emo in enumerate(emotion) ):
                            logger.info("synset offset %s has emotion %s!"%(syn_id, emoemo)) 
                            feature_set[emoemo]+=1
                        else:
                            logger.info("synset offset %s with wnaffect %s has no emotion in %s!"%(syn_id, synsetEmo, emotion))
        if matches == 0:
            matches=1                

        for i in feature_set:
            feature_set[i] = (feature_set[i]/matches)*100

        return feature_set

    def analyse_entry(self, entry, params):

        text_input = entry.get("text", None)
        language = params.get("language", "eng")

        text=self._my_preprocessor(text_input)

        feature_text=self._extract_features(text, language)

        response = Results()

        emotionSet = EmotionSet(id="Emotions0")
        emotions = emotionSet.onyx__hasEmotion

        for i in feature_text:
            emotions.append(Emotion(onyx__hasEmotionCategory=i,
                                    onyx__hasEmotionIntensity=feature_text[i]))

        entry.emotions = [emotionSet]

        yield entry