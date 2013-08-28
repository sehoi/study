# -*- coding: utf-8 -*-

word_delim = ' '

simbol_list = ['.', '"', "'", '(', ')', '[', ']', '=', '-', '@', '!', '?']
josa_list = []
eomi_list = []

josa_file = open('C:\\DEV\\python\\nlp\\JosaEomi\\JOSA.out', 'r')
lines = josa_file.readlines()
for line in lines:
	josa_list.append(line.strip())
#print("JOSA list: ", josa_list)
josa_file.close()

eomi_file = open('C:\\DEV\\python\\nlp\\JosaEomi\\EOMI.out', 'r')
lines = eomi_file.readlines()
for line in lines:
	eomi_list.append(line.strip())
#print("EOMI list: ", eomi_list)
eomi_file.close()

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

input_file = open('C:\\DEV\\python\\nlp\\input\\input.out', 'r')
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
	

