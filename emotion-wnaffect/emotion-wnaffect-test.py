
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
from pattern.en import parse
from senpy.plugins import EmotionPlugin, SenpyPlugin, ShelfMixin
from senpy.models import Results, EmotionSet, Entry, Emotion


# In[5]:

# wn16 = WordNetCorpusReader(os.path.abspath("{0}".format(self._wn16_path)), nltk.data.find(self._wn16_path))
wn16_path = "/data/emotion-wnaffect/wordnet1.6/dict"
wn16 = WordNetCorpusReader(wn16_path, nltk.data.find(wn16_path))
#  the second param should be an omw_reader !! (:


# In[6]:

get_ipython().magic(u'pinfo wn16.synsets')


# In[22]:

nltk.download("omw")


# In[24]:

from nltk.corpus import wordnet as wn
", ".join(wn.langs())


# In[36]:

wn.synsets("love")[0].name(), wn16.synsets("love")[0].name()


# In[35]:

syn = wn.synsets("love")[0]
syn.name()


# In[17]:

text = "I had a tomato at the shop."
sentencesP = parse(text,lemmata=True)
print sentencesP
get_ipython().magic(u'pinfo2 sentencesP.split')
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

