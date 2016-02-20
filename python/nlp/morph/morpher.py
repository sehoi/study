# -*- coding: utf-8 -*-
import os

word_delim = ' '

simbol_list = ['.', '!', '?', ',', '"', "'", '`', '(', ')', '[', ']', '=', '-', '@']
josa_list = []
eomi_list = []

josa_file = open(os.path.dirname(__file__)+os.sep+'JosaEomi'+os.sep+'JOSA.out', 'r')
lines = josa_file.readlines()
for line in lines:
	josa_list.append(line.strip())
#print("JOSA list: ", josa_list)
josa_file.close()

eomi_file = open(os.path.dirname(__file__)+os.sep+'JosaEomi'+os.sep+'EOMI.out', 'r')
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
	

