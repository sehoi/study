# -*- coding: utf-8 -*-
import os
from morph import morpher

lines = []
line_words_list = []
word_list = []

word_tf = {}
keyword_tf = {}

line_score = []

tf_limit = 3
score_limit = 23

max_lines = 3

def test(filename):
	input_file = open(filename, 'r')
	lines = input_file.readlines()
	input_file.close()
	
	# parsing
	for line in lines:
		if len(line) == 0:
			continue
		print("line: ", line)
		
		line = morpher.remove_simbols(line)
		line = morpher.get_words_in_line(line)
		line_words = []
		for word in line:
			word = morpher.remove_josaeomi(word)
			line_words.append(word)
			word_list.append(word)
		
		line_words_list.append(line_words)
	
	# tf count
	for word in word_list:
		if len(word) == 0:
			continue
		
		tf = word_list.count(word)
		word_tf[word] = tf
	print(word_tf)
	
	# get keywords
	keys = sorted(word_tf.keys())
	for key in keys:
		tf = word_tf[key]
		
		if tf >= tf_limit:
			keyword_tf[key] = tf
			print(key, tf)
	
	# line scoring
	keywords = keyword_tf.keys()
	for line_words in line_words_list:
		score = 0
		for keyword in keywords:
			tf = keyword_tf[keyword]
			if keyword in line_words:
				score += tf
			print(keyword, tf)
		line_score.append(score)
	
	print(line_score)
	
	# get high score line
	for line in lines:
		index = lines.index(line)
		if line_score[index] >= score_limit:
			print(line)
	
if __name__ == '__main__':
	test(os.path.dirname(__file__)+os.sep+'input'+os.sep+'input2.out')
