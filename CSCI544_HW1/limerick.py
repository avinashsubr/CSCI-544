#!/usr/bin/env python
import argparse
import string
import sys
import codecs
if sys.version_info[0] == 2:
  from itertools import izip
else:
  izip = zip
from collections import defaultdict as dd
import re
import os.path
import gzip
import tempfile
import shutil
import atexit

# Use word_tokenize to split raw text into words
from string import punctuation

import nltk
from nltk.tokenize import word_tokenize



scriptdir = os.path.dirname(os.path.abspath(__file__))


reader = codecs.getreader('utf8')
writer = codecs.getwriter('utf8')


def prepfile(fh, code):
  if type(fh) is str:
    fh = open(fh, code)
  ret = gzip.open(fh.name, code if code.endswith("t") else code+"t") if fh.name.endswith(".gz") else fh
  if sys.version_info[0] == 2:
    if code.startswith('r'):
      ret = reader(fh)
    elif code.startswith('w'):
      ret = writer(fh)
    else:
      sys.stderr.write("I didn't understand code "+code+"\n")
      sys.exit(1)
  return ret

def addonoffarg(parser, arg, dest=None, default=True, help="TODO"):
  ''' add the switches --arg and --no-arg that set parser.arg to true/false, respectively'''
  group = parser.add_mutually_exclusive_group()
  dest = arg if dest is None else dest
  group.add_argument('--%s' % arg, dest=dest, action='store_true', default=default, help=help)
  group.add_argument('--no-%s' % arg, dest=dest, action='store_false', default=default, help="See --%s" % arg)



class LimerickDetector:

    def __init__(self):
        """
        Initializes the object to have a pronunciation dictionary available
        """
        self._pronunciations = nltk.corpus.cmudict.dict()

    def stress_digits(self, pron):
        return [char for phone in pron for char in phone if char.isdigit()]

    def min_syllable(self, syllables):
        return min(syllables, key=lambda syllable: len(syllable))

    def num_syllables(self, word):
        """
        Returns the number of syllables in a word.  If there's more than one
        pronunciation, take the shorter one.  If there is no entry in the
        dictionary, return 1.
        """
        # TODO: provide an implementation!
        syllables = []
        if word in self._pronunciations:
            prons = self._pronunciations[word]
            for pron in prons:
                syllables.append(self.stress_digits(pron))
            return len(self.min_syllable(syllables))
        else:
            return 1

    #strip until first vowel is reached in the pronunciation
    def first_vowel(self, pron):
        idx = 0
        for i in range(0, len(pron)):
            if pron[i][-1] in ('0', '1', '2'):
                idx = i
                break
        return ' '.join(pron[idx:])

    def rhymes(self, a, b):
        """
        Returns True if two words (represented as lower-case strings) rhymes,
        False otherwise.
        """

        #word isnt in the dictionary and hence dont rhyme
        if a not in self._pronunciations or b not in self._pronunciations:
            return False

        strip_pron_a = []
        strip_pron_b = []
        a = self._pronunciations[a]
        b = self._pronunciations[b]
        for pron in a:
            strip_pron_a.append(self.first_vowel(pron))
        for pron in b:
            strip_pron_b.append(self.first_vowel(pron))

        for ent_a in strip_pron_a:
            ent_a = ent_a.split()
            for ent_b in strip_pron_b:
                ent_b = ent_b.split()
                if len(ent_a) == len(ent_b):
                    if ent_a == ent_b:
                        return True
                elif len(ent_a) < len(ent_b):
                    idx = len(ent_a)
                    if ent_b[-idx:] == ent_a:
                        return True
                else:
                    idx = len(ent_b)
                    if ent_a[-idx:] == ent_b:
                        return True
        return False


    def is_limerick(self, text):
        """
        Takes text where lines are separated by newline characters.  Returns
        True if the text is a limerick, False otherwise.

        A limerick is defined as a poem with the form AABBA, where the A lines
        rhymes with each other, the B lines rhymes with each other, and the A lines do not
        rhymes with the B lines.

        Additionally, the following syllable constraints should be observed:
          * No two A lines should differ in their number of syllables by more than two.
          * The B lines should differ in their number of syllables by no more than two.
          * Each of the B lines should have fewer syllables than each of the A lines.
          * No line should have fewer than 4 syllables

        (English professors may disagree with this definition, but that's what
        we're using here.)
        """
        lime_list = text.lower().strip().split('\n')
        #print lime_list
        init_list = []
        prep_list = []

        for line in lime_list:
            #init_list.append(nltk.tokenize.word_tokenize(line))
            init_list.append(self.apostrophe_tokenize(line))
        print init_list

        alphabet = string.ascii_lowercase + string.ascii_uppercase
        for line in init_list:
           # fin_list.append([''.join(c for c in word if c not in string.punctuation) for word in line])
            line_dup=[]
            for word in line:
                alpha = 0
                string1 = []
                for c in word:
                    if c in alphabet:
                        alpha = 1
                    string1.append(c)
                if alpha != 0:
                    line_dup.append(''.join(string1))
            prep_list.append(line_dup)
        print prep_list

        #Count the number of lines in given Limerick
        if len(prep_list) != 5:
            return False

        syl_cnt = []
        for line in prep_list:
            cnt = 0
            for word in line:
                cnt += self.num_syllables(word)
            syl_cnt.append(cnt)
        print syl_cnt

        #No line should have fewer than 4 syllables
        for cnt in syl_cnt:
            if cnt < 4:
                print "Line has fewer than 4 syllables"
                return False

        # Each of the B lines should have fewer syllables than each of the A lines.
        if (syl_cnt[2] > syl_cnt[0] or syl_cnt[2] > syl_cnt[1] or syl_cnt[2] > syl_cnt[4] or syl_cnt[3] > syl_cnt[0] \
                    or syl_cnt[3] > syl_cnt[1] or syl_cnt[3] > syl_cnt[4]):
            print "B lines have more syllables than each of the A lines"
            return False

        #A lines rhymes with B lines: return False
        if self.rhymes(prep_list[0][-1], prep_list[2][-1]) or self.rhymes(prep_list[0][-1], prep_list[3][-1])\
            or self.rhymes(prep_list[1][-1], prep_list[2][-1]) or self.rhymes(prep_list[1][-1], prep_list[3][-1])\
            or self.rhymes(prep_list[4][-1], prep_list[2][-1]) or self.rhymes(prep_list[4][-1], prep_list[3][-1]):
                print "A lines rhymes with B lines"
                return False

        # A lines rhymes with each other
        # B lines rhymes with each other
        if self.rhymes(prep_list[0][-1], prep_list[1][-1]) and self.rhymes(prep_list[0][-1], prep_list[4][-1]) and \
                self.rhymes(prep_list[1][-1], prep_list[4][-1]):
            if self.rhymes(prep_list[2][-1], prep_list[3][-1]):
                if(abs(syl_cnt[0]-syl_cnt[1]) <= 2 and abs(syl_cnt[0]-syl_cnt[4]) <= 2 and abs(syl_cnt[1]-syl_cnt[4]) <= 2 and abs(syl_cnt[2]-syl_cnt[3]) <= 2):
                        return True
        return False

    def apostrophe_tokenize(self, line):
        #init_list = text.split('\n')
        #for init_line in init_list:
        prep_line = line.split()
        print prep_line
        fin_line = []
        for word in prep_line:
             fin_line.append(word.strip(string.punctuation))
        return fin_line

    def guess_syllables(self, word):
        count = 0
        vowels = 'aeiouy'
        word = word.lower().strip(string.punctuation)
        if word[0] in vowels:
            count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word[-1] == 'e':
            count -= 1
        if word[-2:] == 'le':
            count += 1
        if word[-2:] == 'ee':
            count += 1
        return count

# The code below should not need to be modified
def main():
    parser = argparse.ArgumentParser(description="limerick detector. Given a file containing a poem, indicate whether that poem is a limerick or not",
                                       formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    addonoffarg(parser, 'debug', help="debug mode", default=False)
    parser.add_argument("--infile", "-i", nargs='?', type=argparse.FileType('r'), default=sys.stdin, help="input file")
    parser.add_argument("--outfile", "-o", nargs='?', type=argparse.FileType('w'), default=sys.stdout, help="output file")

    try:
     args = parser.parse_args()
    except IOError as msg:
     parser.error(str(msg))

    infile = prepfile(args.infile, 'r')
    outfile = prepfile(args.outfile, 'w')

    ld = LimerickDetector()
    lines = ''.join(infile.readlines())
    outfile.write("{}\n-----------\n{}\n".format(lines.strip(), ld.is_limerick(lines)))

if __name__ == '__main__':
    main()