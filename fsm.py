#!/usr/bin/python
# encoding=UTF-8

from collections import deque, Iterable, defaultdict
from itertools import chain
import copy
import libxml2, sys, os
import urlparse
sys.path.append(".")
sys.setrecursionlimit(10000)

class switch(object):
	def __init__(self, value):
		self.value = value
		self.fall = False

	def __iter__(self):
		yield self.match
		raise StopIteration

	def match(self, *args):
		if self.fall or not args:
			return True
		elif self.value in args:
			self.fall = True
			return True
		else:
			return False

class Transition(object):
	def __init__(self, label, target, actions=[]):
		self.label = label
		self.target = target
		self.actions = list(actions)

	def appendAction(self, actions):
		self.actions.extend([action for action in actions if action not in self.actions])

	def prependAction(self, actions):
		self.actions[:0] = [action for action in actions if action not in self.actions]

class State(object):
	def __init__(self):
		self.transitions = set()
		self.id = None

	def addTransition(self, label, target, actions=[]):
		trans = set([t for t in self.transForLabel(label) if t.target == target])
		if len(trans) > 0:
			for t in trans: t.appendAction(actions)
		else:
			self.transitions.add(Transition(label, target, actions))

	def statesForLabel(self, label):
		return set([t.target for t in self.transForLabel(label)])

	def transForLabel(self, label):
		return set([t for t in self.transitions if t.label == label])

	def labels(self):
		return set([t.label for t in self.transitions])

class XMLFsm(object):
	def __init__(self):
		self.entry = None
		self.accepts = set()

	def empty(self):
		self.entry = State()
		self.accepts = set([self.entry])
		return self

	def concat(self, b):
		for state in self.accepts:
			state.addTransition(None, b.entry)
		self.accepts = b.accepts
		return self

	def union(self, b):
		entry = State()
		entry.addTransition(None, self.entry)
		entry.addTransition(None, b.entry)
		self.accepts = self.accepts.union(b.accepts)
		self.entry = entry
		return self

	def reachables(self, label = False):
		states = []
		queue = deque([self.entry])
		while len(queue) > 0:
			state = queue.popleft()
			states.append(state)
			state.id = len(states)
			for trans in state.transitions:
				if trans.target not in states and trans.target not in queue:
					queue.append(trans.target)
		return states

	def apply(self, ea=[], la=[]):
		for trans in self.entry.transitions:
			trans.prependAction(ea)
		if la == []: return self
		states = self.reachables()
		for state in states:
			for trans in state.transitions:
				if trans.target in self.accepts:
					trans.appendAction(la)
		return self

	def element(self, name, content, ea=[], la=[]):
		self.entry = State()
		self.entry.addTransition(name, content.entry)
		leave = State()
		for state in content.accepts:
			state.addTransition("/"+name, leave)
		self.accepts = set([leave])
#		self.apply(ea, la)
		return self

	def choice(self, fsms, ea=[], la=[]):
		self.entry = State()
		self.accepts = set()
		for fsm in fsms:
			self.entry.addTransition(None, fsm.entry)
			self.accepts = self.accepts.union(fsm.accepts)
#		self.apply(ea, la)
		return self

	def sequence(self, fsms, ea=[], la=[]):
		fsms.reverse()
		self.entry = fsms[0].entry
		self.accepts = fsms[0].accepts
		for fsm in fsms[1:]:
			for state in fsm.accepts:
				state.addTransition(None, self.entry)
			self.entry = fsm.entry
#		self.apply(ea, la)
		return self

#	@staticmethod
	def particle(term, minOccurs, maxOccurs):
		if maxOccurs == "unbounded":
#           print "Building unbounded part"
			a = copy.deepcopy(term)
			for accept in a.accepts:
				accept.addTransition(None, a.entry)
			a.accepts = set([a.entry])
		else:
#           print "Building optional part %d times" % (maxOccurs - minOccurs)
			a = type(term)().empty()
			leave = a.entry
			for i in range(0, maxOccurs - minOccurs):
				c = copy.deepcopy(term)
				c.concat(a)
				c.entry.addTransition(None, leave)
				a = c
		if minOccurs > 0:
#           print "Building the mandatory part %d times" % minOccurs
			b = type(term)().empty()
			for i in range(0, minOccurs):
				c = copy.deepcopy(term)
				b.concat(c)
			if maxOccurs == "unbounded" or maxOccurs - minOccurs > 0:
				b.concat(a)
			return b
		return a

	@staticmethod
	def closure(states):
		if not isinstance(states, Iterable): states = [states]
		states = list(states)
		actions = [[] for i in range(0, len(states))]
		queue = deque(states)
		while len(queue) > 0:
			state = queue.popleft()
			s = set([trans.target for trans in state.transitions if trans.label is None])
			for st in s:
				for trans in state.transitions:
					if trans.label is None and trans.target == st:
						if st not in states:
							states.append(st)
							actions.append(list(actions[states.index(state)]))
						actions[states.index(st)].extend([a for a in trans.actions if a not in actions[states.index(st)]])
			queue.extend(s)
#		print "  closure has length %d: %s / %s" % (len(states), [s.id for s in states], actions)
		return states, actions

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
			line += "%s\t%s%d%s| " % ("entry:" if state == self.entry else "", "[" if state in self.accepts else " ", state.id, "]" if state in self.accepts else " ")
			first = True
			transitions = dict((trans.label, state.statesForLabel(trans.label)) for trans in state.transitions)
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
				actions = []
				for trans in state.transForLabel(label):
					actions.extend([t for t in trans.actions if t not in actions])
				idx = False
				for action in actions:
					line += "%s%s" % (", " if idx else " / ", action)
					idx = True
			print line

	def determinize(self):
		NFAstates = self.reachables()
		states, actions = XMLFsm.closure(self.entry)
		sets = [states]
		queue = deque([(0, actions)])
		DFAstates = [State()]
		DFA = XMLFsm()
		DFA.entry = DFAstates[0]
		if len([x for x in states if x in self.accepts]) > 0:
			DFA.accepts.add(DFAstates[0])
		while len(queue) > 0:
			i, actions = queue.popleft()
			transitions = dict()
			tactions = dict()
			# for every NFA state from active set
			for state in sets[i]:
				# collect non-epsilon transitions
				for trans in state.transitions:
					if trans.label is not None:
						# as key -> list of target states
						if not transitions.has_key(trans.label):
							transitions[trans.label] = set()
							tactions[trans.label] = list( actions[ sets[i].index(state) ] )
						if trans.target not in transitions[trans.label]:
							transitions[trans.label].add(trans.target)
						tactions[trans.label].extend(trans.actions)

			for label, targets in transitions.iteritems():
				targets, actions = XMLFsm.closure(targets)
				if targets not in sets:
					j = len(sets)
					queue.append((j, actions))
					sets.append(targets)
					DFAstates.append(State())
					if len([x for x in targets if x in self.accepts]) > 0:
						DFA.accepts.add(DFAstates[j])
				else:
					j = sets.index(targets)
				DFAstates[i].addTransition(label, DFAstates[j], tactions[label])
		return DFA

	def minimize(self):
		marked = []
		unmarked = []
		states = self.reachables()
		F = [states.index(x) for x in self.accepts]
		for p in range(0, len(states) - 1):
			for q in range(p + 1, len(states)):
				if (p in F) != (q in F):
					marked.append([p, q])
				else:
					unmarked.append([p, q])
		oldlength = -1

		list2dict = lambda src: dict((t.label, [s.target for s in src if s.label == t.label]) for t in src)

		while len(unmarked) != oldlength:
			oldlength = len(unmarked)
			for pq in unmarked:
				p = states[pq[0]]
				q = states[pq[1]]
				if len(p.transitions) < len(q.transitions): p, q = q, p
				mark = False
				ptrans = list2dict(p.transitions)
				qtrans = list2dict(q.transitions)

				for label, targets in ptrans.iteritems():
					ptarget = states.index(reduce(lambda x, y: y if x is None else x, targets))
					if qtrans.has_key(label):
						qtarget = states.index(reduce(lambda x, y: y if x is None else x, qtrans[label]))
						pacts = list(chain.from_iterable(t.actions for t in p.transitions if t.label == label and t.target == states[ptarget]))
						qacts = list(chain.from_iterable(t.actions for t in q.transitions if t.label == label and t.target == states[qtarget]))
#						print "for label %s and states (%d, %d): %s %s= %s" % (label, ptarget, qtarget, pacts, "!" if pacts != qacts else "=", qacts)
						if ([ptarget, qtarget] in marked) or ([qtarget, ptarget] in marked) or (pacts != qacts):
							mark = True
							break
					else:
						mark = True
						break
				if mark:
					marked.append(pq)
					unmarked.remove(pq)
#		print "Remaining unmarked: %s" % unmarked
		merge = []

		for pq in unmarked:
			inserted = False
			for l in merge:
				if (pq[0] in l) or (pq[1] in l):
					if pq[0] not in l: l.append(pq[0])
					if pq[1] not in l: l.append(pq[1])
					inserted = True
					break
			if not inserted:
				merge.append(pq)

#		print "Merge: %s" % merge
		state2set = dict()
		set_num = 0
		for pq in unmarked:
			pe = state2set.has_key(pq[0])
			qe = state2set.has_key(pq[1])
			if pe and not qe:
				state2set[pq[1]] = state2set[pq[0]]
			elif not pe and qe:
				state2set[pq[0]] = state2set[pq[1]]
			elif not pe and not qe:
				state2set[pq[0]] = set_num
				state2set[pq[1]] = set_num
				set_num += 1

		for i in range(0, len(states)):
			if not state2set.has_key(i):
				state2set[i] = set_num
				set_num += 1

		sets = []
		set2states = dict()
		for i in range(0, set_num):
			set2states[i] = [k for k, v in state2set.items() if v == i]
			sets.append(State())

		for set, state_list in set2states.iteritems():
			for state in state_list:
				for label, targets in list2dict(states[state].transitions).iteritems():
					if len([t for t in sets[set].transitions if t.label == label]) == 0:
						target = states.index(reduce(lambda x, y: y if x is None else x, targets))
						pacts = list(chain.from_iterable(t.actions for t in states[state].transitions if t.label == label and t.target == states[target]))
#						print "Adding transition to DFA for label %s -> %d / %s" % (label, states[target].id, pacts)
						sets[set].addTransition(label, sets[state2set[target]], pacts)
				break
		optDFA = XMLFsm()
		optDFA.entry = sets[state2set[states.index(self.entry)]]
		for state in [sets[state2set[states.index(i)]] for i in self.accepts]:
			optDFA.accepts.add(state)
		print "DFA reduced from %d to %d states (%.1f)" % (len(states), len(sets), 100.0 * len(sets) / len(states))
		return optDFA

if __name__ == "__main__":
	fsm = XMLFsm().element("A",
            XMLFsm().choice([
                XMLFsm().element("C", XMLFsm().empty()).apply([2], [4]),
                XMLFsm().element("D", XMLFsm().empty()).apply([3], [5])
            ]).apply([1], [6]).particle(1, "unbounded"),
          ).apply([0], [7]).particle(1, "unbounded")
	fsm.dump()
	dfa = fsm.determinize()
	dfa.dump()
	dfa = dfa.minimize()
	dfa.dump()
