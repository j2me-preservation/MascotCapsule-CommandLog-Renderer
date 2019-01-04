
# most awfullest s-expr parser in the history of mankind.
# do not use!!

# note: this requires the top-level expression to be a list
def load(f):
	# we read the entire thing into a string because we need to look ahead 1 byte
	# (like that's any excuse lol)
	s = f.read()
	p = 0

	# skip white space
	while s[p].isspace(): p += 1

	list, p = parse_list(s, p)

	# skip white space
	while p < len(s) and s[p].isspace(): p += 1

	assert p == len(s)

	return list

def parse_atom(s, p):
	if s[p] == '"':
		p += 1
		end = s.find('"', p)
		z = s[p:end]
		p = end + 1
	else:
		assert s[p].isalnum() or s[p] == '-'

		z = s[p]
		p += 1

		while s[p].isalnum() or s[p] == '-':
			z += s[p]
			p += 1

	#print('ATOM', z)
	return z, p

# note: this requires the first item of each expression be an atom
def parse_list(s, p):
	# expect (
	assert s[p] == '('
	p += 1

	# skip white space
	while s[p].isspace(): p += 1

	# expect atom
	atom, p = parse_atom(s, p)

	self = [atom]

	while True:
		# skip white space
		while s[p].isspace(): p += 1

		# accept ) or atom or nested list
		if s[p] == ')':
			p += 1
			break

		if s[p] == '(':
			list, p = parse_list(s, p)
			self += [list]
		else:
			# expect atom
			atom, p = parse_atom(s, p)
			self += [atom]

	#print('LIST', self)
	return self, p

# helper to convert a loaded list to a dictionary
def as_dict(list):
	dict = {}

	for entry in list:
		assert isinstance(entry[0], str)

		if len(entry) > 2:
			dict[entry[0]] = entry[1:]
		else:
			dict[entry[0]] = entry[1]

	return dict