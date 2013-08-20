# -*- coding:euc-kr -*-

# 초성 리스트
initial_sounds = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

# 종성 리스트
final_consonants = [' ', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 
'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ',
'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

# 유니코드 한글 시작 문자의 ord값
unicode_start = 44032
# 유니코드 한글 종료 문자의 ord값 + 1
unicode_end = 55204
# 유니코드 한글 자음당 간격
initial_interval = 588
# 유니코드 한글 자음당 종성 간격
final_interval = 28


# 한글 문자의 초성 변환 함수
def getInitial(ch) :
	unicode = ord(ch) - unicode_start
	i = int(unicode / initial_interval)
	#print("\t\t\char: ", ch, ", unicode: ", ord(ch), ", initial sound: ", initial_sounds[i])
	return initial_sounds[i]

# 한글 문자의 종성 변환 함수
def getFinal(ch) :
	unicode = ord(ch) - unicode_start
	i = unicode % final_interval
	#print("\t\t\char: ", ch, ", unicode: ", ord(ch), ", final consonants: ", final_consonants[i])
	return final_consonants[i]


# 검색 함수
def isMatch(names, querys) :
	name_str = ""
	for name in names:
		name_str = name_str + name
	#print(name_str)

	query_str = ""
	for initial in querys:
		query_str = query_str + initial
	#print(query_str)

	if query_str in name_str: return True
	else: return False


# 이름 리스트
names = ["김세회", "박진우", "유지훈", "이슬기", "한준희"]
# 이름 리스트의 초성,종성을 저장할 변수
initials_list = []
finals_list = []


# 이름 리스트의 초성과 종성 저장
for name in names:
	#print("\t", name, name.encode("unicode-escape"))
	initials = ""
	finals = ""
	for c in name:
		initials = initials + getInitial(c)
		finals = finals + getFinal(c)
	
	initials_list.append(initials)
	finals_list.append(finals)

i = 0
while i < len(names):
	print(names[i], initials_list[i], finals_list[i])
	i += 1


# 검색하기
while True:
	query_type = input("\n검색 타입 입력(초성 검색=1, 종성 검색=2,그 외 종료): ")
	# 초성 검색
	if query_type == "1":
		while True: 			
			inputs = input("\n검색할 초성을 입력하세요.(q to exit): ")
			
			if inputs == "q": break
		
			# 초성 검색 결과
			print("\n------ 초성 검색 결과 --------")
			search_result = []
			i = 0
			for initials in initials_list:
				if isMatch(initials, inputs):
					search_result.append(names[i])
				i += 1
			
			print(search_result);
	# 종성 검색
	elif query_type == "2":
		while True: 
			inputs = input("\n검색할 종성을 입력하세요.(q to exit): ")
			
			if inputs == "q": break

			# 종성 검색 결과
			print("\n------ 종성 검색 결과 --------")
			search_result = []
			i = 0
			for finals in finals_list:
				if isMatch(finals, inputs):
					search_result.append(names[i])
				i += 1
			
			print(search_result);
	else: break