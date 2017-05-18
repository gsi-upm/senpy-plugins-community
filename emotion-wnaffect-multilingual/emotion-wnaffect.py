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
from emotion import Emotion as Emo

from senpy.plugins import EmotionPlugin, SenpyPlugin, ShelfMixin
from senpy.models import Results, EmotionSet, Entry, Emotion


class EmotionTextPlugin(EmotionPlugin, ShelfMixin):
    
  
    def _load_synsets(self, synsets_path):
        """Returns a dictionary synset offset -> emotion (int -> str)."""
        tree = ET.parse(synsets_path)
        root = tree.getroot()
        pos_map = { "noun": "NN", "adj": "JJ", "verb": "VB", "adv": "RB" }

        synsets = {}
        for pos in ["noun", "adj", "verb", "adv"]:
            tag = pos_map[pos]
            for elem in root.findall(".//{0}-syn-list//{0}-syn".format(pos, pos)):
                offset = int(elem.get("id")[2:])                
                if not offset: continue
                if elem.get("categ"):
                    synsets[offset] = Emo.emotions[elem.get("categ")] if elem.get("categ") in Emo.emotions else None
                elif elem.get("noun-id"):
                    synsets[offset] = synsets[int(elem.get("noun-id")[2:])]
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

    def activate(self, *args, **kwargs):
        
        nltk.download('stopwords')
        self._stopwords = stopwords.words('english')
        self._categoryLevels = [5,6,7]
        self._categories = {'anger': [set(), set(['hate']), set(['anger'])],
                            'fear': [set(['negative-fear','ambiguous-fear']), set(), set()],
                            'disgust': [set(), set(['self-disgust']), set(['antipathy', 'contempt', 'disgust', 'alienation'])],
                            'joy': [set(['gratitude','levity','affection','enthusiasm','love','joy','liking']), set(), set()],
                            'sadness': [set(['ingrattitude','daze','humility','compassion','despair','anxiety','sadness']), set(), set()],
                            'surprise' : [set(['surprise']), set(), set()]}

        self._load_emotions(self.hierarchy_path)
                
        if 'total_synsets' not in self.sh:
            total_synsets = self._load_synsets(self.synsets_path)
            self.sh['total_synsets'] = total_synsets
        
        self._total_synsets = self.sh['total_synsets']
        
        if 'wn16' not in self.sh:
            self._wn16_path = self.wn16_path
            wn16 = WordNetCorpusReader(os.path.abspath("{0}".format(self._wn16_path)), nltk.data.find(self._wn16_path))
            self.sh['wn16'] = wn16
        
        self._wn16 = self.sh['wn16']
        del self.sh['wn16']

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

    def _extract_features(self, text):

        feature_set={k:0 for k in self._categories}
        ngrams_words = [w.lower() for w in text.split() if w.lower() not in self._stopwords]

        matches=0
        for i in range(len(ngrams_words)):
            synsets = self._wn16.synsets(ngrams_words[i]) 
            if synsets:
                    offset = synsets[0].offset()
                    if offset in self._total_synsets:
                        if self._total_synsets[offset] is None:
                            continue
                        else:
                            synsetEmo = self._total_synsets[offset]
                            emotion = [synsetEmo.get_level(j).name for j in _categoryLevels]
                            matches+=1
                            for i,emoEmotions in self._categories.items():
                                if any( emotion[j] in emoEmotions[j] for j in range(len(_categoryLevels)) ):
                                    feature_set[i]+=1
        if matches == 0:
            matches=1                

        for i in feature_set:
            feature_set[i] = (feature_set[i]/matches)*100

        return feature_set

    def analyse_entry(self, entry, params):

        text_input = entry.get("text", None)

        text=self._my_preprocessor(text_input)

        feature_text=self._extract_features(text)

        response = Results()

        emotionSet = EmotionSet(id="Emotions0")
        emotions = emotionSet.onyx__hasEmotion

        for i in feature_text:
            emotions.append(Emotion(onyx__hasEmotionCategory=i,
                                    onyx__hasEmotionIntensity=feature_text[i]))

        entry.emotions = [emotionSet]

        yield entry