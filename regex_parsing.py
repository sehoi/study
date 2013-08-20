# -*- coding:euc-kr -*-

import re
import urllib.request

# html tag regex
start_tag_pattern = re.compile('<[^/][^>]*>')
end_tag_pattern = re.compile('</[^>]*>')
a_tag_pattern = re.compile('<a[^/][^>]*>')


# functions
def get_contents(html):
	contents = re.sub(start_tag_pattern, '', html)
	contents = re.sub(end_tag_pattern, '', contents)
	return contents
	
def get_start_tags(html):
	tags = re.findall(start_tag_pattern, html)
	return tags

def get_end_tags(html):
	tags = re.findall(end_tag_pattern, html)
	return tags

def check_a_tag(tags):
	tags = re.findall(a_tag_pattern, html)
	return tags


# http request
u = urllib.request.urlopen("http://www.nate.com")
lines = u.readlines()

# html parsing
for line in lines:
	line = line.decode('euc-kr').strip()
	
	if line=='':
		continue
		
	print("\n", line)
	
	start_tags = get_start_tags(line)
	print("\tstart tags: ", start_tags)

	contents = get_contents(line)
	print("\tcontents: ", contents)

	end_tags = get_end_tags(line)
	print("\tend tags: ", end_tags)
