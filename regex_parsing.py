# -*- coding:utf-8 -*-

import re
import urllib.request

## html tag regex
start_tag_pattern = re.compile('<[^/][^>]*>')
end_tag_pattern = re.compile('</[^>]*>')
a_tag_pattern = re.compile('<a[^/][^>]*>')

## email regex
email_pattern = re.compile('\w+@\w+\.\w{3}')

## link regex
# not perfect!!
#link_pattern = re.compile('[http|https]+://\w+\.[^\s|^)|^>|^&nbsp;]+')
link_pattern = re.compile('[http|https]+://\w+\..+(?<![\s|)|>|^&.+;|^\:])')

## id regex
id_pattern = re.compile('@\w+')


## functions
def get_content(html):
	content = re.sub(start_tag_pattern, '', html)
	content = re.sub(end_tag_pattern, '', content)
	return content
	
def get_start_tags(html):
	tags = re.findall(start_tag_pattern, html)
	return tags

def get_end_tags(html):
	tags = re.findall(end_tag_pattern, html)
	return tags

def get_emails(text):
	emails = re.findall(email_pattern, text)
	return emails

def get_links(text):
	links = re.findall(link_pattern, text)
	return links

def get_ids(text):
	ids = re.findall(id_pattern, text)
	return ids


## http request
#u = urllib.request.urlopen("http://www.nate.com")
u = urllib.request.urlopen("https://twitter.com/sehoe")
#print(u.info())
lines = u.readlines()


## html parsing
link_list = []
id_list = []
for line in lines:
	line = line.decode('utf-8').strip()
	
	if line=='':
		continue
	#print("\n", line)
	
	start_tags = get_start_tags(line)
	end_tags = get_end_tags(line)
	#print("\tstart tags: ", start_tags)
	#print("\tend tags: ", end_tags)
	
	content = get_content(line)
	#print("\tcontent: ", content)
	
	## find link
	links = (get_links(content))
	for link in links:
		link_list.append(link)

	## find id
	ids = get_ids(content)
	for id in ids:
		id_list.append(id)


## print result
print("link list: ", link_list)
print("ID list: ", id_list)