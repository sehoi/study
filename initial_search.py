# -*- coding:euc-kr -*-

# �ʼ� ����Ʈ
initial_sounds = ['��', '��', '��', '��', '��', '��', '��', '��', '��',
'��', '��', '��', '��', '��', '��', '��', '��', '��', '��']

# ���� ����Ʈ
final_consonants = [' ', '��', '��', '��', '��', '��', '��', '��', '��', 
'��', '��', '��', '��', '��', '��', '��', '��', '��', '��',
'��', '��', '��', '��', '��', '��', '��', '��', '��', '��']

# �����ڵ� �ѱ� ���� ������ ord��
unicode_start = 44032
# �����ڵ� �ѱ� ���� ������ ord�� + 1
unicode_end = 55204
# �����ڵ� �ѱ� ������ ����
initial_interval = 588
# �����ڵ� �ѱ� ������ ���� ����
final_interval = 28


# �ѱ� ������ �ʼ� ��ȯ �Լ�
def getInitial(ch) :
	unicode = ord(ch) - unicode_start
	i = int(unicode / initial_interval)
	#print("\t\t\char: ", ch, ", unicode: ", ord(ch), ", initial sound: ", initial_sounds[i])
	return initial_sounds[i]

# �ѱ� ������ ���� ��ȯ �Լ�
def getFinal(ch) :
	unicode = ord(ch) - unicode_start
	i = unicode % final_interval
	#print("\t\t\char: ", ch, ", unicode: ", ord(ch), ", final consonants: ", final_consonants[i])
	return final_consonants[i]


# �˻� �Լ�
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


# �̸� ����Ʈ
names = ["�輼ȸ", "������", "������", "�̽���", "������"]
# �̸� ����Ʈ�� �ʼ�,������ ������ ����
initials_list = []
finals_list = []


# �̸� ����Ʈ�� �ʼ��� ���� ����
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


# �˻��ϱ�
while True:
	query_type = input("\n�˻� Ÿ�� �Է�(�ʼ� �˻�=1, ���� �˻�=2,�� �� ����): ")
	# �ʼ� �˻�
	if query_type == "1":
		while True: 			
			inputs = input("\n�˻��� �ʼ��� �Է��ϼ���.(q to exit): ")
			
			if inputs == "q": break
		
			# �ʼ� �˻� ���
			print("\n------ �ʼ� �˻� ��� --------")
			search_result = []
			i = 0
			for initials in initials_list:
				if isMatch(initials, inputs):
					search_result.append(names[i])
				i += 1
			
			print(search_result);
	# ���� �˻�
	elif query_type == "2":
		while True: 
			inputs = input("\n�˻��� ������ �Է��ϼ���.(q to exit): ")
			
			if inputs == "q": break

			# ���� �˻� ���
			print("\n------ ���� �˻� ��� --------")
			search_result = []
			i = 0
			for finals in finals_list:
				if isMatch(finals, inputs):
					search_result.append(names[i])
				i += 1
			
			print(search_result);
	else: break