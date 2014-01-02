# coding=UTF-8
from collections import deque, Iterable, defaultdict
import copy

"""
d = defaultdict(list)
d["word1"].append(1)
d["word2"].append(2)
d["word2"].append(3)
d
defaultdict(<type 'list'>, {'word1': [1], 'word2': [2, 3]})
"""

class State:
	def __init__(self):
		self.transitions = dict()
		self.actions = dict()
		self.id = None

	def setTransition(self, label, target, actions = set()):
		if not self.transitions.has_key(label):
			self.transitions[label] = set()
			self.actions[label] = list()
		self.transitions[label].add(target)
		actions = actions if isinstance(actions, Iterable) else [actions]
		for action in actions:
			if action not in self.actions[label]: self.actions[label].append(action)

class Fsm:
	def __init__(self):
		self.entry = None
		self.labels = list()
		self.accepts = set()

	def concat(self, fsm):
		for state in self.accepts: state.setTransition(None, fsm.entry)
		self.accepts = fsm.accepts
		return self

	def union(self, fsm):
		entry = State()
		entry.setTransition(None, fsm.entry)
		entry.setTransition(None, self.entry)
		self.accepts = self.accepts.union(fsm.accepts)
		self.entry = entry
		return self

	@staticmethod
	def empty():
		fsm = Fsm()
		fsm.entry = State()
		fsm.accepts.add(fsm.entry)
		return fsm

	def isFinal(self, state):
		return state in self.accepts

	def makeFinal(self, state):
		self.accepts.add(state)

	@staticmethod
	def closure(states):
		if not isinstance(states, Iterable): states = [states]
		c = set(states)
		queue = deque(states)
		while len(queue) > 0:
			state = queue.popleft()
			if state.transitions.has_key(None):
				targets = state.transitions[None]
				for target in targets:
					if target not in c:
						queue.append(target)
						c.add(target)
#		print "closure has %d states" % len(c)
		return c

	def dump2(self):
		visited = set([self.entry])
		inqueue = deque([self.entry])
		outqueue = deque()
		labels = dict()
		substs = set()
		id = 1
		labelId = 0
		while len(inqueue) > 0:
			state = inqueue.popleft()
			if state not in self.accepts:
				state.id = id
				id += 1
				outqueue.append(state)
				
			transitions = state.transitions
			for label, targets in transitions.iteritems():
				if not (label.startswith("/") or label.startswith('!')) and label not in labels:
					labels[label] = labelId
					labelId += 1
				elif label.startswith('!'):
					substs.add(label)
				for target in targets:
					if target not in visited:
						inqueue.append(target)
						visited.add(target)
		for state in self.accepts:
			state.id = id
			id += 1
			outqueue.append(state)
		for label in substs:
			labels[label] = labelId
			labelId += 1

		first_final = min(map(lambda x: x.id, self.accepts))
		token_list = []
		token_offset = [0]
		token_length = [0]
		target_list = [0, 0]
		target_offset = [0]

		print "first_final = %d" % first_final
		while len(outqueue) > 0:
			state = outqueue.popleft()
			onClose = 0
			nTokens = 0
			t_list = []
			token_offset.append(len(token_list))
			transitions = state.transitions
			for label, targets in transitions.iteritems():
				target = reduce(lambda x, y: x if y is None else y, targets)
				if label.startswith('/'):
					onClose = target.id
				else:
					token_list.append(labels[label])
					nTokens += 1
					t_list.append(target.id)
			target_offset.append(len(target_list))
			target_list.append(onClose)
			target_list.extend(t_list)
			target_list.append(0)		# default transition
			token_length.append(len(t_list))
			
		print "token_list := %s\n" % str(token_list)
		print "token_offset := %s\n" % str(token_offset)
		print "token_length := %s\n" % str(token_length)
		print "target_list := %s\n" % str(target_list)
		print "target_offset := %s\n" % str(target_offset)
		for index, token in dict(zip(labels.values(), labels.keys())).iteritems():
			print "{0, %s}" % token

	def dump(self):
		visited = set([self.entry])
		queue = deque([self.entry])
		self.entry.id = 1
		id = 2
		while len(queue) > 0:
			state = queue.popleft()
			line = ""
			line += "%s\t%s%d%s| " % ("entry:" if state == self.entry else "", "[" if self.isFinal(state) else " ", state.id, "]" if self.isFinal(state) else " ")
			first = True
			transitions = state.transitions
			for label, targets in transitions.iteritems():
				line += "%s%s -> " % ("" if first else ", ", label)
				first = False
				idx = False
				for target in targets:
					if target not in visited:
						target.id = id
						id += 1
						queue.append(target)
						visited.add(target)
					line += "%s%d" % (", " if idx else "", target.id)
					idx = True
				state.actions[label]
				idx = False
				for action in state.actions[label]:
					line += "%s%s" % (", " if idx else " / ", action)
					idx = True
			print line

	def determinize(self):
		dfa = Fsm()
		dfa.entry = State()
		sets = {0: {'dfaState': dfa.entry, 'set': self.closure(self.entry)}}
		for state in sets[0]['set']:
			if self.isFinal(state):
				dfa.makeFinal(dfa.entry)
				break
		queue = deque([0])
		while len(queue) > 0:
			i = queue.popleft()
#			print "Processing DFA state/NFA state set %d" % i
			transitions = dict()
			actions = dict()
			for nfaState in sets[i]['set']:
#				print "  Processing state %d" % nfaState.id
				for label, targets in nfaState.transitions.iteritems():
					if label is None: continue
					if not transitions.has_key(label):
						transitions[label] = set()
						actions[label] = set()
					transitions[label] = transitions[label].union(targets)
					if nfaState.actions.has_key(label):
						actions[label] = actions[label].union(nfaState.actions[label])

			for nfaState in sets[i]['set']:
				if not nfaState.transitions.has_key(None): continue
				for label, targets in transitions.iteritems():
					actions[label] = actions[label].union(nfaState.actions[None])

			for label, targets in transitions.iteritems():
				targets = self.closure(targets)
				for target in targets:
					if not target.transitions.has_key(None): continue
#					print "  adding actions for the empty word from state %d" % target.id
					actions[label] = actions[label].union(target.actions[None])

				is_final = False
				for s in targets:
					if self.isFinal(s):
						is_final = True
						break
				new_state = None
				for t in sets.itervalues():
					if t['set'] == targets:
						new_state = t['dfaState']
						break
				if new_state is None:
					new_state = State()
					new_state.id = len(sets)
					sets[new_state.id] = {'dfaState': new_state, 'set': targets}
					if is_final: dfa.makeFinal(new_state)
					queue.append(new_state.id)
				line = ""
				for action in actions[label]: line += ", %d" % action
#				print "  adding transition for label %s to state %d with actions (%s)" % (label, new_state.id, line)
				sets[i]['dfaState'].setTransition(label, new_state, actions[label])
		return dfa

class XMLFsm(Fsm):
	def __init__(self):
		Fsm.__init__(self)
		pass

	@staticmethod
	def sequence(fsms, ea = list(), la = list()):
		fsm = XMLFsm()
		fsm.entry = State()
		fsm.makeFinal(fsm.entry)
		fsms.reverse()
		for idx, machine in enumerate(fsms):
			for accept in machine.accepts:
				accept.setTransition(None, fsm.entry, la if idx == 0 else set())
			fsm.entry = machine.entry
		entry = State()
		entry.setTransition(None, fsm.entry, ea)
		fsm.entry = entry
		return fsm

	@staticmethod
	def choice(fsms, ea = list(), la = list()):
		fsm = XMLFsm()
		fsm.entry = State()
		leave = State()
		for machine in fsms:
			fsm.entry.setTransition(None, machine.entry, ea)
			for accept in machine.accepts: accept.setTransition(None, leave, la)
		fsm.makeFinal(leave)
		return fsm

	@staticmethod
	def element(name, content, ea = list(), la = list()):
		fsm = XMLFsm()
		fsm.entry = State()
		fsm.entry.setTransition(name, content.entry, ea)
		leave = State()
		for state in content.accepts: state.setTransition("/" + name, leave, la)
		fsm.makeFinal(leave)
		return fsm

	@staticmethod
	def particle(term, minOccurs, maxOccurs):
		if maxOccurs == "unbounded":
#			print "Building unbounded part"
			a = copy.deepcopy(term)
			for accept in a.accepts:
				accept.setTransition(None, a.entry)
			a.accepts = set([a.entry])
		else:
#			print "Building optional part %d times" % (maxOccurs - minOccurs)
			a = XMLFsm.empty()
			leave = a.entry
			for i in range(0, maxOccurs - minOccurs):
				c = copy.deepcopy(term)
				c.concat(a)
				c.entry.setTransition(None, leave)
				a = c
		if minOccurs > 0:
#			print "Building the mandatory part %d times" % minOccurs
			b = XMLFsm.empty()
			for i in range(0, minOccurs):
#				print "cloning part %d" % i
				c = copy.deepcopy(term)
#				c.dump()
#				print "concating to existing part"
				b.concat(c)
#				b.dump()
			if maxOccurs == "unbounded" or maxOccurs - minOccurs > 0:
				b.concat(a)
			return b
		return a
"""
fsm = XMLFsm.choice([
	XMLFsm.element("Foo", XMLFsm.empty(), [1, 2], [7]),
	XMLFsm.element("Bar", XMLFsm.empty(), [2, 3], [6]),
	XMLFsm.element("Baz", XMLFsm.empty(), [3, 4], [5])
	], [8], [9])
#fsm = XMLFsm.element("Baz", XMLFsm.empty(), [1], [2])
fsm.dump()
fsm = XMLFsm.particle(fsm, 0, "unbounded")
fsm.dump()
dfa = fsm.determinize()
dfa.dump()
"""
