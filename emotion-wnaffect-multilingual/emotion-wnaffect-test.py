
# coding: utf-8

# In[1]:

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


# In[5]:

# wn16 = WordNetCorpusReader(os.path.abspath("{0}".format(self._wn16_path)), nltk.data.find(self._wn16_path))
wn16_path = "/data/emotion-wnaffect/wordnet1.6/dict"
wn16 = WordNetCorpusReader(wn16_path, nltk.data.find(wn16_path))
#  the second param should be an omw_reader !! (:


# In[6]:

get_ipython().magic('pinfo wn16.synsets')


# In[3]:

nltk.download("omw")


# ## nltk.corpus.wn and multilingual wn experiments

# In[1]:

from nltk.corpus import wordnet as wn
print(", ".join(wn.langs()))


# In[16]:

syns = wn.synsets("hlad",lang='cs')
print(len(syns))
print(len(set(syn.offset() for syn in syns)))


# In[2]:

Emo.emotions = {}
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
_load_emotions(None, "wn-affect-1.1/a-hierarchy.xml")


# In[3]:

mapping_wn16_30_path = "mapping-16-30"
wn16_30 = {}
pos_mapping_suffixes = {"a":"adj", "r":"adv", "n":"noun", "v":"verb"}
# for pos in ("a", "r", "n", "v"):
for pos,suffix in pos_mapping_suffixes.items():
    mapping = {}
    path = os.path.join(mapping_wn16_30_path,"wn16-30.{0}".format(suffix))
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
    

def _convert_wn_16_30(self, pos, wn16_offset):
    return wn16_30[pos][wn16_offset]


# In[4]:

unconvertedSynsetIds = []

def _load_synsets(self, synsets_path):
    """Returns a dictionary synset offset -> emotion (int -> str)."""
    # """Returns a dictionary POS tag -> synset offset -> emotion (str -> int -> str)."""
    def convertId(wn16id):
        pos_char,wn16_offset = wn16id.split("#")
        try:
            return "{0}-{1}".format(wn16_30[pos_char][int(wn16_offset)], pos_char)
        except KeyError:
            # unconvertedSynsetIds.append((wn16id, pos_char, wn16_offset))
            return None
    
    tree = ET.parse(synsets_path)
    root = tree.getroot()

    synsets = {}
    pending = []
    for pos in ["noun", "adj", "verb", "adv"]:
        for elem in root.findall(".//{0}-syn-list//{0}-syn".format(pos)):
            idd = elem.get("id")
            wn30_id = convertId(idd)
            if wn30_id is None: 
                continue
            if elem.get("categ"):
                synsets[wn30_id] = Emo.emotions[elem.get("categ")] if elem.get("categ") in Emo.emotions else None
            elif elem.get("noun-id"):
                try:
                    synsets[wn30_id] = synsets[convertId(elem.get("noun-id"))]
                except KeyError:
                    if wn30_id[:12] != "unconverted-":
                        pending.append((wn30_id, convertId(elem.get("noun-id"))))
    for (wn30_id, noun_id) in pending:
        try:
            synsets[wn30_id] = synsets[noun_id]
        except KeyError:
            print("trouble with id",wn30_id, noun_id)
            raise
    return synsets


# In[5]:

wnaff = _load_synsets(None, "wn-affect-1.1/a-synsets.xml")


# In[6]:

unconvertedSynsetIds


# The one id that doesn't convert to wn3.0 is **a#00196250** but its wn-affect category is **calmness**, which currently has no Ekman emotion associated.

# In[7]:

Emo.printTree()


# In[13]:

set(["foo","fum"])


# In[11]:

for level in (5,):
    for name, emo in Emo.emotions.items():
        if emo.level == level:
            print("%-28s %2d %s"%(emo.name, emo.level, emo.parent))


# In[118]:

categories = set()
for idd,emo in wnaff.items():
    #print(idd,":",emo)
    categories.add(str(emo))
    if str(emo) == 'surprise':
        print(emo.name, emo.level, emo.parent, [e.name for e in emo.children])
'surprise' in categories


# # Below uses pattern package - Python 2 only!!

# In[17]:

from pattern.en import parse

text = "I had a tomato at the shop."
sentencesP = parse(text,lemmata=True)
print sentencesP
get_ipython().magic('pinfo2 sentencesP.split')
sentences = sentencesP.split()
print sentences
print
for s in sentences:
    print
    for w in s:
        for p in w:
            print "%7s"%p,
        print
print

