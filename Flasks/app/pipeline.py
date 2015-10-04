#!/usr/bin/python
# -*- coding: utf-8 -*-
import MySQLdb as mdb
# import sys
import pandas as pd
from textstat.textstat import textstat
import copy
import numpy as np
import nltk
import string
from collections import Counter
from nltk.corpus import stopwords
import math 
import re
import nltk.stem.porter as porter

def build_vectors(counter1, counter2):
    all_items = set(counter1.keys()).union(set(counter2.keys()))
    vector1 = [counter1[k] for k in all_items]
    vector2 = [counter2[k] for k in all_items]
    return vector1, vector2

def normalized_product(v1, v2):
    dot_product = sum(n1 * n2 for n1, n2 in zip(v1, v2) )
    magnitude1 = math.sqrt(sum(n ** 2 for n in v1))
    magnitude2 = math.sqrt(sum(n ** 2 for n in v2))
    return dot_product / (magnitude1 * magnitude2)

def get_filtered_counter(text):
    '''http://www.cs.duke.edu/courses/spring14/compsci290/assignments/lab02.html'''
    lowers = text.lower()
    #remove the punctuation using the character deletion step of translate
    #no_punctuation = lowers.translate(dict.fromkeys(string.punctuation)) # -- TODOlowers.translate(string.punctuation)
    regex = re.compile('[%s]' % re.escape(string.punctuation))
    no_punctuation = regex.sub('', lowers)
    tokens = nltk.word_tokenize(no_punctuation)
    filtered = [w for w in tokens if not w in stopwords.words('english')]
    return Counter(tokens)

def get_filtered_stemmed_counter(text):
    '''http://www.cs.duke.edu/courses/spring14/compsci290/assignments/lab02.html'''
    filtered = get_filtered_counter(text)
    stemmer = porter.PorterStemmer()
    stemmed = []
    for item in filtered:
        stemmed.append(stemmer.stem(item))
    return Counter(stemmed)

def filtered_cosine_similarity(text1,text2):
    c1 = get_filtered_stemmed_counter(text1)
    c2 = get_filtered_stemmed_counter(text2)
    
    v1,v2 = build_vectors(c1, c2)
    return normalized_product(v1, v2)

def find_related_asins_depth1(asin, dfm):
    row = dfm[dfm.asin == asin]
    
    if row.empty: return set([])
    for asins_str in row.relevant_asins: pass # TODO: find better way to access an object
    asins = asins_str.split()
    
    asins_set = set([])
    
    for asin1 in asins: 
        row1 = dfm[dfm.asin == asin1]
        if not row1.empty: asins_set.add(asin1)
    
    return asins_set

def find_related_asins(asin, dfm, depth):
    ''' asins are related by amazon'z connections;
        depth is how many layers in the network we go '''
    try:
        if depth == 0: return set([asin])
        
        asins = find_related_asins_depth1(asin, dfm)
        if depth == 1: return asins
        asins_out = copy.deepcopy(asins)
        for asin1 in asins:
            asins_out.update(find_related_asins(asin1,dfm,depth-1))

        return asins_out
    except Exception as e:
        print "failed in find_related_asins  ", e
        return {}

def titles_match(title1,title2):
    treshold = 0.8
    return filtered_cosine_similarity(title1,title2) > treshold

def get_coarsegrained_difficulty_new(score):
    if score == 1:
        result = 'easy to moderate'
    elif score == 2:
        result = 'advanced'
    else:
        result = 'Could not find out'
    return result

# sort dataframes titles by similarity with the source
def include_title_similarity(df,title0):
    df['similarity'] = 0
    for title in df.title.values:
        indx = df[df.title == title].index
        df.loc[indx,'similarity'] = filtered_cosine_similarity(title,title0)
    return df.sort('similarity', inplace = True, ascending = 0)

def empty_dict():
    d = {'adv_w': [0],
  'ar_score': [0],
  'asin': [''],
  'avg_rating': [0.],
  'difficulty': [''],
  'fk_score': [0.],
  'imgUrl': ['../static/background_output.jpg'],
  'index': [0],
  'inferred_class': [2],
  'intro_w': [0.],
  'nrevs': [0],
  'nrevs_positive': [0],
  'relevant_asins': [''],
  'score': [0],
  'similarity': [0],
  'title': [''],
  'winning_w': [0]}
    return d

def get_searches_dict(in_ld, success):
    ''' these searches will be called by knobs in the output'''
    
    if not success: return {}

    titles=[]
    for dd in in_ld:
      titles.append(dd['title'])

    #amazon
    amazon_dict = {}
    OL_dict = {}
    hackershelf_dict = {}
    lookforbook_dict = {}
    google_dict = {}

    amazon_base = 'http://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%3Dstripbooks&field-keywords='
    OL_base = 'https://openlibrary.org/search?q='
    hackershelf_base = 'http://hackershelf.com/search/?q='
    lookforbook_base = 'http://www.lookforbook.com/cgi-bin/search.cgi?lang=en&st='
    google_base = 'https://www.google.com/search?tbm=bks&hl=en&q='

    for title in titles:
        tit = title.lower().replace(" ", "+")
        amazon_dict[title] = amazon_base + tit
        OL_dict[title] = OL_base + tit
        hackershelf_dict[title] = hackershelf_base + tit
        lookforbook_dict[title] = lookforbook_base + tit
        google_dict[title] = google_base + tit

    searches = {}

    searches['amazon'] = amazon_dict
    searches['OL'] = OL_dict
    searches['hackershelf'] = hackershelf_dict
    searches['lookforbook'] = lookforbook_dict
    searches['google'] = google_dict

    return searches

def pipeline(in_title,in_depth):

    con1 = mdb.connect('localhost', 'insightUser', 'insight15', 'amazon_filtered_compact');
    #dfres = pd.read_sql('select * from trained;', con=con1) 
    dfres = pd.read_sql('select * from final;', con=con1) 
    con1.close()

    #---- asins of books matching the query --------
    asin0_set = set([])
    for index, row in dfres.iterrows():
        title = row.title
        if (titles_match(title,in_title)):
            asin0_set.add(row.asin)
            
    if not asin0_set:        
        return False, empty_dict()


    # all related asins
    asinall_set = copy.deepcopy(asin0_set)
    for asin0 in asin0_set:
        asinall_set.update(find_related_asins(asin0, dfres, in_depth))

    def set_mapper (in_set) :
        def g(x):
            return x in in_set
        return g
    out_df = dfres[dfres['asin'].map(set_mapper(asinall_set))]

    # add the difficulty line
    out_df['difficulty'] = 'could not rate'
    for index, row in out_df.iterrows():
        score = row['inferred_class']
        diff = get_coarsegrained_difficulty_new(score)
        out_df.loc[index,'difficulty'] = diff

    # add similarity
    include_title_similarity(out_df,in_title)

    # final dict
    out_d = out_df.T.to_dict().values()
    out_d.sort(key = lambda x: x['similarity'],reverse = True)

    for d in out_d:
      d['nrevs'] = int(d['nrevs'])

    return True, out_d