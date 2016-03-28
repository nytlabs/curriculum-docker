#!/usr/bin/env python

# AKA tuned-resonator curriculum-insular resolver/worker

import beanstalkc
import pattern.web
from pattern.en import parsetree
from pymongo import MongoClient
import datetime
import os

beanstalk = beanstalkc.Connection(host='localhost', port=14711)
client = MongoClient(tz_aware=True)
#beanstalk = beanstalkc.Connection(host=os.getenv("AKABEANSTALK_PORT_14711_TCP_ADDR"), port=14711, parse_yaml=False)
#client = MongoClient(os.getenv("AKAMONGO_PORT_27017_TCP_ADDR"), tz_aware=True)
db = client.curriculum
print 'AKA WORKER IS STARTING'
while True:
    # take URL and groupID
    # resolve URL into chunks and shove them in 'keywords' with same groupID
    # delete job
    print 'starting worker outer loop'
    job = beanstalk.reserve()  # this is blocking, waits till there's something on the stalk
    payload = job.body.split('|')
    groupID = payload[0]
    url = pattern.web.URL(payload[-1])
    print 'new url, we think', url
    timestamp = datetime.datetime.utcnow()
    try:
        document = url.download(cached=True)
    except Exception as e:
        print 'the url.download failed on %s' % url
        print 'error is ', e
        job.delete()
        continue
    if (url.mimetype in pattern.web.MIMETYPE_WEBPAGE) or (url.mimetype in pattern.web.MIMETYPE_PLAINTEXT):
        try:
            doc_plain = pattern.web.plaintext(document)
        except Exception as e:
            print 'the plaintext parse failed on URL %s' % url
            print 'error is ', e
            job.delete()
            continue
        '''
        parsetree(string,
               tokenize = True,         # Split punctuation marks from words?
                   tags = True,         # Parse part-of-speech tags? (NN, JJ, ...)
                 chunks = True,         # Parse chunks? (NP, VP, PNP, ...)
              relations = False,        # Parse chunk relations? (-SBJ, -OBJ, ...)
                lemmata = False,        # Parse lemmata? (ate => eat)
               encoding = 'utf-8'       # Input string encoding.
                 tagset = None)         # Penn Treebank II (default) or UNIVERSAL.
        '''
        parsed = parsetree(doc_plain, chunks=True)
        for sentence in parsed:
            # only noun phrases for now but let's pick some good other ones next week
            # seeing ADJP, ADVP, PP and VP mostly tho NP are predominant
            # gen = (the_chunk for the_chunk in sentence.chunks if the_chunk.type=='NP')
            # for chunk in gen:
            for chunk in sentence.chunks:
                try:
                    d = db.keywords.update(
                        {'keyword': chunk.string, 'type': chunk.type, 'groupID': groupID},
                        {'$push': {'timestamp': timestamp, 'url': url.string}, '$set': {'latest': timestamp}},
                        upsert=True
                        )
                except Exception as e:
                    print 'mongo upsert error!', e
                    continue
    else:
        'we failed the mimetype test, we think mimetype is ', url.mimetype
    job.delete()
    print 'job deleted, we think this was all successful - loop over'
