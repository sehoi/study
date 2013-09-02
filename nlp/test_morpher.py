# -*- coding: utf-8 -*-
import os
from morph import morpher

def test_morpher(filename):
	input_file = open(filename, 'r')
	lines = input_file.readlines()
	for line in lines:
		line = morpher.remove_simbols(line)
		if len(line) == 0:
			continue	
		print("line: ", line)
		
		word_list = morpher.get_words_in_line(line)
		if len(word_list) != 0:
			print("words: ", word_list)
		
		removed_word_list = []
		for word in word_list:
			removed_word = morpher.remove_josaeomi(word)
			if len(removed_word) == 0:
				continue
			removed_word_list.append(removed_word)
		print("refined_words: ", removed_word_list)
		
		print('\n')
	input_file.close();

if __name__ == '__main__':
	test_morpher(os.path.dirname(__file__)+os.sep+'input'+os.sep+'input.out')
