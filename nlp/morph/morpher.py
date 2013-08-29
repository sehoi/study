# -*- coding: utf-8 -*-
import os

word_delim = ' '

simbol_list = ['.', '"', "'", '(', ')', '[', ']', '=', '-', '@', '!', '?']
josa_list = []
eomi_list = []

<<<<<<< HEAD:nlp/morph/morpher.py
josa_file = open('C:\\DEV\\python\\study\\nlp\\morph\\JosaEomi\\JOSA.out', 'r')
=======
josa_file = open('JosaEomi'+os.sep+'JOSA.out', 'r')
>>>>>>> e2a2a037da3d552f2f6364e95561634f8712215a:nlp/nlp.py
lines = josa_file.readlines()
for line in lines:
	josa_list.append(line.strip())
#print("JOSA list: ", josa_list)
josa_file.close()

<<<<<<< HEAD:nlp/morph/morpher.py
eomi_file = open('C:\\DEV\\python\\study\\nlp\\morph\\JosaEomi\\EOMI.out', 'r')
=======
eomi_file = open('JosaEomi'+os.sep+'EOMI.out', 'r')
>>>>>>> e2a2a037da3d552f2f6364e95561634f8712215a:nlp/nlp.py
lines = eomi_file.readlines()
for line in lines:
	eomi_list.append(line.strip())
#print("EOMI list: ", eomi_list)
eomi_file.close()

def remove_simbols(line): 
	for simbol in simbol_list:
		line = line.replace(simbol, ' ')
	line = line.strip()
	return line
		
def get_words_in_line(line):
	words = line.split(word_delim)
	return words
	
def remove_josaeomi(word):
	removed_word = word
	
	max_word = ""
	for josa in josa_list:
		if len(removed_word) == 0:
			return removed_word
		
		if removed_word.endswith(josa) == True:
			if len(max_word) < len(josa):
				max_word = josa
	
	for eomi in eomi_list:
		if len(removed_word) == 0:
			return removed_word
		
		if removed_word.endswith(eomi) == True:
			if len(max_word) < len(eomi):
				max_word = eomi
	
	return removed_word.rstrip(max_word)
<<<<<<< HEAD:nlp/morph/morpher.py
=======

input_file = open('input'+os.sep+'input.out', 'r')
lines = input_file.readlines()
for line in lines:
	for simbol in simbol_list:
		line = line.replace(simbol, ' ')
	line = line.strip()
	if len(line) == 0:
		continue	
	print("line: ", line)
	
	word_list = get_words_in_line(line)
	if len(word_list) != 0:
		print("words: ", word_list)
	
	removed_word_list = []
	for word in word_list:
		removed_word = remove_josaeomi(word)
		if len(removed_word) == 0:
			continue
		removed_word_list.append(removed_word)
	print("refined_words: ", removed_word_list)
	
	print('\n')
	
input_file.close();
>>>>>>> e2a2a037da3d552f2f6364e95561634f8712215a:nlp/nlp.py
	

